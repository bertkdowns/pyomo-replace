from contextlib import contextmanager
from dataclasses import dataclass

from idaes.core.util.model_statistics import degrees_of_freedom
from pyomo.contrib.incidence_analysis import IncidenceGraphInterface
from pyomo.core.base.var import IndexedVar
from pyomo.environ import Block, Var, value
from pyomo.network import Port

__all__ = ["Replacement", "SpecificationState"]


def _is_child_of(block, component):
    parent = component.parent_block()
    while parent is not None:
        if parent is block:
            return True
        parent = parent.parent_block()
    return False


def _is_fixed(var: Var | IndexedVar):
    """Return whether every index of a variable is fixed."""
    if isinstance(var, IndexedVar):
        if all(v.fixed for v in var.values()):
            return True
        if any(v.fixed for v in var.values()):
            raise ValueError(
                f"Variable {var} is partially fixed. All indices must be fixed or unfixed."
            )
        return False
    return var.fixed


def _var_data_objects(var: Var | IndexedVar):
    return list(var.values()) if isinstance(var, IndexedVar) else [var]


def _fix(var: Var | IndexedVar):
    for item in _var_data_objects(var):
        item.fix()


def _unfix(var: Var | IndexedVar):
    for item in _var_data_objects(var):
        item.unfix()


def _snapshot(var: Var | IndexedVar):
    return [(item, item.fixed, value(item, exception=False)) for item in _var_data_objects(var)]


def _restore(snapshot):
    for item, was_fixed, item_value in snapshot:
        if item_value is not None:
            item.set_value(item_value)
        if was_fixed:
            item.fix()
        else:
            item.unfix()


@dataclass(frozen=True, eq=False)
class Replacement:
    canonical_variable: Var | IndexedVar
    replacement_variable: Var | IndexedVar
    category: str


class SpecificationState:
    """Authoritative Canonical Variable and Replacement state for one flowsheet."""

    @classmethod
    def for_flowsheet(cls, flowsheet: Block):
        """Return the flowsheet's SpecificationState, creating it when needed."""
        specifications = getattr(flowsheet, "specifications", None)
        if specifications is None:
            specifications = cls(flowsheet)
            flowsheet.specifications = specifications
        return specifications

    def __init__(self, flowsheet: Block):
        self._flowsheet = flowsheet
        self._canonical_variables: list[tuple[Var | IndexedVar, str]] = []
        self._replacements: list[Replacement] = []

    def register(self, canonical_variables: list[tuple[Var | IndexedVar, str]]):
        """Register Canonical Variables and immediately make new ones active."""
        for canonical_variable, category in canonical_variables:
            existing_category = self._registered_category(canonical_variable)
            if existing_category is None:
                _fix(canonical_variable)
                self._canonical_variables.append((canonical_variable, category))
            elif existing_category != category:
                raise ValueError(
                    f"Variable {canonical_variable} is already registered as {existing_category}, not {category}."
                )

    def register_inlet_ports(self, block: Block):
        """Register variables on unconnected ports marked as inlets."""
        for port in block.component_objects(ctype=Port, active=True, descend_into=True):
            if not hasattr(port, "is_inlet"):
                raise ValueError(
                    f"Port {port.name} must declare whether it is an inlet."
                )
            if len(port.sources()) == 0 and port.is_inlet:
                self.register([(getattr(port, name), "inlet") for name in port.vars])

    def validate(self, block: Block, allow_degrees_of_freedom=False):
        """Validate the degrees of freedom for the supplied block only."""
        dof = degrees_of_freedom(block)
        if dof > 0 and not allow_degrees_of_freedom:
            raise ValueError(
                f"Block {block.name} has {dof} degrees of freedom. "
                "Perhaps a Canonical Variable is missing."
            )
        if dof < 0:
            raise ValueError(
                f"Block {block.name} has {dof} degrees of freedom. "
                "Perhaps a non-canonical variable is fixed."
            )

    def canonical_variables_in(self, block: Block):
        return [
            canonical_variable
            for canonical_variable, _category in self._canonical_variables
            if _is_child_of(block, canonical_variable)
        ]

    def fixed_canonical_variables_in(self, block: Block):
        return [
            canonical_variable
            for canonical_variable in self.canonical_variables_in(block)
            if _is_fixed(canonical_variable)
        ]

    def category_of(self, canonical_variable: Var | IndexedVar):
        category = self._registered_category(canonical_variable)
        if category is None:
            raise ValueError(f"Variable {canonical_variable} is not a Canonical Variable.")
        return category

    def replacement_candidates_in(self, block: Block):
        return (
            variable
            for variable in block.component_objects(Var, descend_into=True)
            if not self._is_canonical(variable) and not _is_fixed(variable)
        )

    def replace(self, canonical_variable: Var | IndexedVar, replacement_variable: Var | IndexedVar):
        """Immediately activate a Replacement in the flowsheet solve state."""
        if not self._belongs_to_flowsheet(canonical_variable) or not self._belongs_to_flowsheet(
            replacement_variable
        ):
            raise ValueError(
                f"Variables {canonical_variable} and {replacement_variable} do not belong to {self._flowsheet.name}."
            )

        existing = self._replacement_for(canonical_variable)
        if existing is not None:
            if existing.replacement_variable is not replacement_variable:
                raise ValueError(
                    f"Canonical Variable {canonical_variable} already has an active Replacement."
                )
            _unfix(canonical_variable)
            _fix(replacement_variable)
            return existing

        category = self._registered_category(canonical_variable)
        if category is None:
            raise ValueError(f"Variable {canonical_variable} is not a Canonical Variable.")
        if not _is_fixed(canonical_variable):
            raise ValueError(f"Canonical Variable {canonical_variable} must be fixed to be replaced.")
        if self._is_canonical(replacement_variable):
            raise ValueError(
                f"Variable {replacement_variable} is a Canonical Variable and cannot be a Replacement."
            )
        if _is_fixed(replacement_variable):
            raise ValueError(
                f"Variable {replacement_variable} must be unfixed to become a Replacement."
            )

        _unfix(canonical_variable)
        _fix(replacement_variable)
        igraph = IncidenceGraphInterface(self._flowsheet)
        _variables, constraints = igraph.dulmage_mendelsohn()
        if constraints.unmatched:
            _fix(canonical_variable)
            _unfix(replacement_variable)
            raise ValueError(
                f"Replacing {canonical_variable} with {replacement_variable} causes a structural singularity in {self._flowsheet.name}. "
                f"Unmatched constraints: {[constraint.name for constraint in constraints.unmatched]}"
            )

        replacement = Replacement(canonical_variable, replacement_variable, category)
        self._replacements.append(replacement)
        return replacement

    def undo(self, canonical_variable: Var | IndexedVar):
        replacement = self._replacement_for(canonical_variable)
        if replacement is None:
            raise ValueError(f"Canonical Variable {canonical_variable} has no active Replacement.")
        self._replacements.remove(replacement)
        _fix(replacement.canonical_variable)
        _unfix(replacement.replacement_variable)
        return replacement

    def deactivate_category(self, category: str):
        deactivated = [
            replacement for replacement in self._replacements if replacement.category == category
        ]
        for replacement in deactivated:
            self.undo(replacement.canonical_variable)
        return deactivated

    def replacements_in(self, block: Block):
        return [
            replacement
            for replacement in self._replacements
            if _is_child_of(block, replacement.canonical_variable)
        ]

    def internal_replacements_in(self, block: Block):
        return [
            replacement
            for replacement in self.replacements_in(block)
            if _is_child_of(block, replacement.replacement_variable)
        ]

    def external_replacements_in(self, block: Block):
        return [
            replacement
            for replacement in self.replacements_in(block)
            if not _is_child_of(block, replacement.replacement_variable)
        ]

    def external_replacements_provided_by(self, block: Block):
        return [
            replacement
            for replacement in self._replacements
            if not _is_child_of(block, replacement.canonical_variable)
            and _is_child_of(block, replacement.replacement_variable)
        ]

    def guesses_in(self, block: Block):
        return [
            replacement.canonical_variable
            for replacement in self.replacements_in(block)
            if not _is_fixed(replacement.canonical_variable)
        ]

    @contextmanager
    def replacements_suspended_in(self, block: Block):
        with self._replacements_suspended(self.replacements_in(block)):
            yield self

    @contextmanager
    def external_replacements_suspended_in(self, block: Block):
        replacements = self.external_replacements_in(
            block
        ) + self.external_replacements_provided_by(block)
        with self._replacements_suspended(replacements):
            yield self

    @contextmanager
    def _replacements_suspended(self, replacements: list[Replacement]):
        snapshots = {
            replacement: _snapshot(replacement.replacement_variable)
            for replacement in replacements
        }
        try:
            for replacement in replacements:
                _fix(replacement.canonical_variable)
                _unfix(replacement.replacement_variable)
            yield
        finally:
            for replacement in replacements:
                _unfix(replacement.canonical_variable)
                _restore(snapshots[replacement])

    def _registered_category(self, variable: Var | IndexedVar):
        for canonical_variable, category in self._canonical_variables:
            if canonical_variable is variable:
                return category
        return None

    def _is_canonical(self, variable: Var | IndexedVar):
        return self._registered_category(variable) is not None

    def _replacement_for(self, canonical_variable: Var | IndexedVar):
        for replacement in self._replacements:
            if replacement.canonical_variable is canonical_variable:
                return replacement
        return None

    def _belongs_to_flowsheet(self, variable: Var | IndexedVar):
        return _is_child_of(self._flowsheet, variable)
