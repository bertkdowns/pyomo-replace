from contextlib import contextmanager
from dataclasses import dataclass

from pyomo.environ import ConcreteModel, Block, Var, Expression, Constraint, value
from idaes.core.util.model_statistics import degrees_of_freedom
from pyomo.contrib.incidence_analysis import IncidenceGraphInterface
from pyomo.network import Port, Arc
from pyomo.core.base.var import IndexedVar, ScalarVar
from pyomo.gdp import Disjunct
"""
Requirements:
- Ability to identify canonical vars in a block
- Ability to replace canonical vars within/across blocks with new canonical vars (replacement should be stored on the closest parent block)
- Degrees of freedom should always be zero
- Ability to list:
    - canonical vars in a block (recursively)
    - replacements made in a block (recursively)
    - currently fixed canonical vars/replacements in a block (recursively)
    - current guess variables (canonical vars that are replaced) (recursively)
"""

def is_child_of(block, component):
    parent = component.parent_block()
    while parent is not None:
        if parent is block:
            return True
        parent = parent.parent_block()
    return False


def _var_data_objects(var: Var | IndexedVar):
    if isinstance(var, IndexedVar):
        return list(var.values())
    return [var]


def _fix_var(var: Var | IndexedVar):
    for v in _var_data_objects(var):
        v.fix()


def _unfix_var(var: Var | IndexedVar):
    for v in _var_data_objects(var):
        v.unfix()


def _snapshot_var(var: Var | IndexedVar):
    return [(v, v.fixed, value(v, exception=False)) for v in _var_data_objects(var)]


def _restore_var(snapshot):
    for var, was_fixed, var_value in snapshot:
        if var_value is not None:
            var.set_value(var_value)
        if was_fixed:
            var.fix()
        else:
            var.unfix()


@dataclass(eq=False)
class ReplacementRecord:
    canonical_var: Var | IndexedVar
    replacement_var: Var | IndexedVar
    canonical_block: Block
    replacement_block: Block

    def as_tuple(self):
        return (self.canonical_var, self.replacement_var)

    def is_in(self, block: Block):
        return is_child_of(block, self.canonical_var)

    def is_local_to(self, block: Block):
        return is_child_of(block, self.canonical_var) and is_child_of(
            block, self.replacement_var
        )


class ReplacementState:
    """
    Authoritative replacement state for a flowsheet.
    """

    def __init__(self, flowsheet: Block):
        self.flowsheet = flowsheet
        self.records: list[ReplacementRecord] = []

    def append(self, canonical_var: Var | IndexedVar, replacement_var: Var | IndexedVar):
        record = ReplacementRecord(
            canonical_var=canonical_var,
            replacement_var=replacement_var,
            canonical_block=canonical_var.parent_block(),
            replacement_block=replacement_var.parent_block(),
        )
        self.records.append(record)
        return record

    def replace(self, canonical_var: Var | IndexedVar, replacement_var: Var | IndexedVar):
        canonical_block = canonical_var.parent_block()
        replacement_block = replacement_var.parent_block()
        if canonical_block.flowsheet() is not self.flowsheet or replacement_block.flowsheet() is not self.flowsheet:
            raise ValueError(
                f"Variables {canonical_var} and {replacement_var} do not share flowsheet {self.flowsheet.name}."
            )

        if not hasattr(canonical_block, "_state_vars") or not is_in(
            canonical_var, get_canonical_vars(canonical_block)
        ):
            raise ValueError(
                f"Variable {canonical_var} is not a registered canonical variable in the block {canonical_block.name}."
            )
        if not is_fixed(canonical_var):
            raise ValueError(f"Variable {canonical_var} must be fixed to be replaced.")
        if is_in(replacement_var, get_canonical_vars(replacement_block)):
            raise ValueError(
                f"Variable {replacement_var} is a registered canonical variable in the block {replacement_block.name}."
            )
        if is_fixed(replacement_var):
            raise ValueError(
                f"Variable {replacement_var} must not be fixed to be used as a replacement."
            )

        _unfix_var(canonical_var)
        _fix_var(replacement_var)

        igraph = IncidenceGraphInterface(self.flowsheet)
        _var_partition, constraint_partition = igraph.dulmage_mendelsohn()
        if constraint_partition.unmatched:
            _fix_var(canonical_var)
            _unfix_var(replacement_var)
            raise ValueError(
                f"Replacing variable {canonical_var} with {replacement_var} causes a structural singularity in {self.flowsheet.name}. These variables cannot be replaced with the given system configuration."
                "Unmatched constraints: "
                f"{[constraint.name for constraint in constraint_partition.unmatched]}"
            )

        return self.append(canonical_var, replacement_var)

    def replacements_in(self, block: Block):
        return [record.as_tuple() for record in self.records if record.is_in(block)]

    def guesses_in(self, block: Block):
        return [
            record.canonical_var
            for record in self.records
            if record.is_in(block) and not is_fixed(record.canonical_var)
        ]

    def find(self, canonical_var: Var | IndexedVar):
        for record in self.records:
            if record.canonical_var is canonical_var:
                return record
        return None

    def remove(self, canonical_var: Var | IndexedVar):
        for i, record in enumerate(self.records):
            if record.canonical_var is canonical_var:
                del self.records[i]
                return record
        return None

    def undo(self, canonical_var: Var | IndexedVar):
        record = self.remove(canonical_var)
        if record is None:
            raise ValueError(
                f"No replacement has been made for variable {canonical_var} in {self.flowsheet.name}."
            )
        _fix_var(record.canonical_var)
        _unfix_var(record.replacement_var)
        return record.as_tuple()

    def deactivate_category(self, category_name: str, block: Block):
        deactivated = []
        for canonical_var, replacement_var in self.replacements_in(block):
            if get_category(canonical_var) == category_name:
                self.undo(canonical_var)
                deactivated.append((canonical_var, replacement_var))
        return deactivated

    def reactivate(self, canonical_var: Var | IndexedVar, replacement_var: Var | IndexedVar):
        return self.replace(canonical_var, replacement_var)

    @contextmanager
    def initialisation_context(self, block: Block):
        records = [record for record in self.records if record.is_in(block)]
        snapshots = {
            record: _snapshot_var(record.replacement_var) for record in records
        }
        try:
            for record in records:
                _fix_var(record.canonical_var)
                _unfix_var(record.replacement_var)
            yield self
        finally:
            for record in records:
                _unfix_var(record.canonical_var)
                _restore_var(snapshots[record])

    def activate_local_replacements_for_initialisation(self, block: Block):
        activated = []
        for record in self.records:
            if record.is_local_to(block):
                _unfix_var(record.canonical_var)
                _fix_var(record.replacement_var)
                activated.append(record.as_tuple())
        return activated


def replacement_state(block: Block) -> ReplacementState:
    flowsheet = block.flowsheet() or block
    if not hasattr(flowsheet, "_replacement_state"):
        flowsheet._replacement_state = ReplacementState(flowsheet)
    return flowsheet._replacement_state

def register_block(block, canonical_vars: list[tuple[Var,str]], allow_degrees_of_freedom=False):
    """
    This is used to identify which variables in the block should be the canonical variables.
    These variables, if fixed, should fully specify the block, i.e Degrees of freedom should be zero.

    Args:
        block: The block to register the canonical variables for.
        canonical_vars: List of variables to register as canonical variables. These will all be fixed when registering the block.
        allow_degrees_of_freedom: If True, the block is allowed to have degrees of freedom of greater than zero. This is for example when the block is constrained by external constraints, e.g inlet conditions.
    Raises:
        ValueError: If any of the canonical variables are not part of the block, or if the block does not have zero degrees of freedom after fixing the canonical variables.
    """
    for v,category in canonical_vars:
        if not is_child_of(block, v):
            raise ValueError(
                f"Variable {v} is not part of the block {block.name} being registered"
            )
        v.fix()  # All canonical variables must be fixed to register the block.

    if degrees_of_freedom(block) > 0 and not allow_degrees_of_freedom:
        raise ValueError(
            f"Block {block.name} has {degrees_of_freedom(block)} degrees of freedom. "
            "Each block should have zero degrees of freedom when all canonical variables are fixed."
            "Perhaps you forgot to include a canonical variable?"
        )
    if degrees_of_freedom(block) < 0:
        raise ValueError(
            f"Block {block.name} has {degrees_of_freedom(block)} degrees of freedom. "
            "Each block should have zero degrees of freedom when all canonical variables are fixed."
            "Perhaps you included a variable that is not a canonical variable, or you are fixing extra variables other than the canonical variables?"
        )

    block._state_vars = canonical_vars

def is_fixed(var : Var | IndexedVar):
    """
    Checks if a variable or indexed variable is fully fixed, or fully unfixed.
    """
    if isinstance(var, IndexedVar):
        if all(v.fixed for v in var.values()):
            return True
        else:
            if any(v.fixed for v in var.values()):
                raise ValueError(f"Variable {var} is partially fixed. All indices must be either fixed or unfixed.")
            return False
    else:
        return var.fixed
    

def get_canonical_vars(block):
    """
    List all canonical variables in the block
    """
    state_vars = getattr(block, "_state_vars", None)
    if isinstance(state_vars, list):
        return [v for v, category in state_vars]
    return []

def all_canonical_vars(block):
    """
    List all canonical variables in the block and its sub-blocks recursively.
    """
    canonical_vars = []
    canonical_vars.extend(get_canonical_vars(block))
    for b in block.component_objects(Block, descend_into=True):
        canonical_vars.extend(get_canonical_vars(b))
    return canonical_vars

def all_canonical_var_categories(block: Block):
    """
    List all canonical variable categories in the block and its sub-blocks recursively.
    """
    categories: list[Var, str] = []
    if hasattr(block, "_state_vars"):
        categories.extend(block._state_vars)
    for b in block.component_objects(Block, descend_into=True):
        if hasattr(b, "_state_vars"):
            categories.extend(b._state_vars)
    return categories

def list_fixed_canonical_vars(block):
    """
    List all fixed canonical variables in the block and its sub-blocks recursively.
    """
    return [var for var in all_canonical_vars(block) if is_fixed(var)]


def _safe_equal(var1,var2):
    """
    Safe equality check to handle different types of var/indexed var comparisons.
    """
    try:
        return var1 == var2
    except TypeError:
        return False


def _has_var(var,var_list):
    """
    Check if a variable is in a list of variables, using safe equality check.
    """
    return any(_safe_equal(var, v) for v in var_list)


def list_available_vars(block):
    """
    List all available variables (variables that are not canonical vars and are not fixed) in the block and its sub-blocks recursively.
    """
    return (
        var
        for var in block.component_objects(Var, descend_into=True)
        if not _has_var(var, get_canonical_vars(var.parent_block())) and not is_fixed(var)
    )

def get_category(canonical_var: Var):
    block = canonical_var.parent_block()
    while (True):
        if block is None:
            break;
        if not hasattr(block, "_state_vars"):
            block = block.parent_block()
            continue
        # try find the category.
        for v, category in block._state_vars:
            if v is canonical_var:
                return category
        # Otherwise, loop and try the parent block.
        block = block.parent_block()
    raise ValueError(f"Variable {canonical_var} is not a registered canonical variable.")

def closest_common_parent(comp1, comp2):
    # Collect all ancestors of comp1
    ancestors1 = set()
    p = comp1.parent_block()
    while p is not None:
        ancestors1.add(p)
        p = p.parent_block()

    # Walk comp2 upwards until a match
    p = comp2.parent_block()
    while p is not None:
        if p in ancestors1:
            return p
        p = p.parent_block()
    return None


def is_in(obj, container):
    """This is to check if the reference is the name, not using python equality."""
    return any(obj is x for x in container)


def fix_port(port: Port):
    """
    To allow the degrees of freedom check to work,
    we need to fix any other constraints coming into the model.
    """
    vars_to_unfix = []
    for var in port.vars():
        if not var.fixed:
            var.fix()
            vars_to_unfix.append(var)
    return vars_to_unfix

def unfix_port_vars(vars_to_unfix):
    for var in vars_to_unfix:
        var.unfix()
    

obj_iter_kwds = dict(
    ctype=Port,
    active=True,
)

def register_inlet_ports(block):
    """
    This is a helper function to add all inlet variables to the canonical variable definition of a block.
    This is useful for unit models where the inlet variables are always canonical variables.
    """

    for port in block.component_objects(**obj_iter_kwds):
        if not hasattr(port, "is_inlet"):
            raise ValueError(
                f"Port {port.name} does not have the 'is_inlet' attribute. Please set this attribute to True for inlet ports and False for outlet ports. This is done automatically for Pyomo-Replace Unit Operations."
            )
        
        if len(port.sources()) == 0 and port.is_inlet:  # This is an inlet port
            # if not already, register the block
            parent_block = port.parent_block()
            # Initialise block if there are no canonical vars yet
            if not hasattr(parent_block, "_state_vars"):
                parent_block._state_vars = []
            # Add all variables in the port to the canonical vars if not already present
            for var_name in port.vars:
                var = getattr(port, var_name)
                if not _has_var(var, get_canonical_vars(parent_block)):
                    var.fix()
                    parent_block._state_vars.append((var,"inlet"))
