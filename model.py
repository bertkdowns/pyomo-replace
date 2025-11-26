from pyomo.environ import ConcreteModel, Block, Var, Expression, Constraint
from idaes.core.util.model_statistics import degrees_of_freedom
from pyomo.contrib.incidence_analysis import IncidenceGraphInterface
from pyomo.network import Port, Arc
from pyomo.core.base.var import IndexedVar, ScalarVar
from pyomo.gdp import Disjunct
"""
Requirements:
- Ability to identify state vars in a block
- Ability to replace state vars within/across blocks with new state vars (replacement should be stored on the closest parent block)
- Degrees of freedom should always be zero
- Ability to list:
    - state vars in a block (recursively)
    - replacements made in a block (recursively)
    - currently fixed state vars/replacements in a block (recursively)
    - current guess variables (state vars that are replaced) (recursively)
"""

def is_child_of(block, component):
    parent = component.parent_block()
    while parent is not None:
        if parent is block:
            return True
        parent = parent.parent_block()
    return False

def register_block(block, state_vars: list, allow_degrees_of_freedom=False):
    """
    This is used to identify which variables in the block should be the state variables.
    These variables, if fixed, should fully specify the block, i.e Degrees of freedom should be zero.

    Args:
        block: The block to register the state variables for.
        state_vars: List of variables to register as state variables. These will all be fixed when registering the block.
        allow_degrees_of_freedom: If True, the block is allowed to have degrees of freedom of greater than zero. This is for example when the block is constrained by external constraints, e.g inlet conditions.
    Raises:
        ValueError: If any of the state variables are not part of the block, or if the block does not have zero degrees of freedom after fixing the state variables.
    """
    for v in state_vars:
        if is_child_of(v,block):
            raise ValueError(
                f"Variable {v} is not part of the block {block.name} being registered"
            )
        v.fix()  # All state variables must be fixed to register the block.

    if degrees_of_freedom(block) > 0 and not allow_degrees_of_freedom:
        raise ValueError(
            f"Block {block.name} has {degrees_of_freedom(block)} degrees of freedom. "
            "Each block should have zero degrees of freedom when all state variables are fixed."
            "Perhaps you forgot to include a state variable?"
        )
    if degrees_of_freedom(block) < 0:
        raise ValueError(
            f"Block {block.name} has {degrees_of_freedom(block)} degrees of freedom. "
            "Each block should have zero degrees of freedom when all state variables are fixed."
            "Perhaps you included a variable that is not a state variable, or you are fixing extra variables other than the state variables?"
        )

    block._state_vars = state_vars
    block._replacements = []  # List of (old_var, new_var) tuples for replacements

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
    

def list_state_vars(block):
    """
    List all state variables in the block and its sub-blocks recursively.
    """
    state_vars = []
    if hasattr(block, "_state_vars"):
        state_vars.extend(block._state_vars)
    for b in block.component_objects(Block, descend_into=True):
        if hasattr(b, "_state_vars"):
            state_vars.extend(b._state_vars)
    return state_vars


def list_guesses(block):
    """
    List all guess variables (state variables that have been replaced) in the block and its sub-blocks recursively.
    """
    return [var for var in list_state_vars(block) if not is_fixed(var)]


def list_fixed_state_vars(block):
    """
    List all fixed state variables in the block and its sub-blocks recursively.
    """
    return [var for var in list_state_vars(block) if is_fixed(var)]


def list_replacements(block):
    """
    List all replacements made in the block and its sub-blocks recursively.
    """
    replacements = []
    if hasattr(block, "_replacements"):
        replacements.extend(block._replacements)
    for b in block.component_objects(Block, descend_into=True):
        if hasattr(b, "_replacements"):
            replacements.extend(b._replacements)
    return replacements



def _try_get_state_vars(block):
    """
    Helper function to get state vars from a block, or return an empty list if none are registered.
    """
    if hasattr(block, "_state_vars"):
        return block._state_vars
    else:
        return []

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
    List all available variables (variables that are not state vars and are not fixed) in the block and its sub-blocks recursively.
    """
    return (
        var
        for var in block.component_objects(Var, descend_into=True)
        if not _has_var(var, _try_get_state_vars(var.parent_block)) and not is_fixed(var)
    )

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


def replace_state_var(state_var, new_var):
    state_var_parent = state_var.parent_block()
    new_var_parent = new_var.parent_block()
    parent_block = state_var_parent.flowsheet()
    if parent_block is None:
        raise ValueError(
            f"Variables {state_var} and {new_var} do not share a common parent block."
        )

    # The state var must be currently fixed, and must be registered as a state var.
    if not hasattr(state_var_parent, "_state_vars") or not is_in(
        state_var, state_var_parent._state_vars
    ):
        raise ValueError(
            f"Variable {state_var} is not a registered state variable in the closest common parent block {parent_block.name}."
        )
    if not is_fixed(state_var):
        raise ValueError(f"Variable {state_var} must be fixed to be replaced.")
    # The new var must not be a state var, and must not be fixed.
    if hasattr(new_var_parent, "_state_vars") and is_in(
        new_var, new_var_parent._state_vars
    ):
        raise ValueError(
            f"Variable {new_var} is a registered state variable in the closest common parent block {parent_block.name}."
        )
    if is_fixed(new_var):
        raise ValueError(
            f"Variable {new_var} must not be fixed to be used as a replacement."
        )

    # Note: We can't check degrees of freedom because it could be fixed by external constraints.
    # Validate that degrees of freedom is zero before the replacement
    # if degrees_of_freedom(parent_block) != 0:
    #     raise ValueError(
    #         f"Block {parent_block.name} must have zero degrees of freedom before replacement. Something is wrong with the model formulation. It currently has {degrees_of_freedom(parent_block)} degrees of freedom."
    #     )
    # Perform the replacement
    state_var.unfix()
    new_var.fix()

    # if degrees_of_freedom(parent_block) != 0:
    #     # Revert the replacement
    #     state_var.fix()
    #     new_var.unfix()
    #     raise ValueError(
    #         f"Block {parent_block.name} must have zero degrees of freedom after replacement. Did you try to replace an indexed variable with one which has a different size?"
    #     )

    # Validate that this does not cause an over-constrained or under-constrained set.
    # https://pyomo.readthedocs.io/en/6.8.0/contributed_packages/incidence/tutorial.dm.html
    igraph = IncidenceGraphInterface(parent_block)
    var_dm_partition, constraint_dm_partion = igraph.dulmage_mendelsohn()

    #  ignore unmatched variables, as some of them may be fixed by outside constraints.
    # however, if internal constraints are unmatched, that is definitely over-defined.
    # this does not guarantee that the system is well-defined, as we would have to check both at the model level.
    if len(constraint_dm_partion.unmatched) > 0:
        # Revert the replacement
        state_var.fix()
        new_var.unfix()
        raise ValueError(
            f"Replacing variable {state_var} with {new_var} causes a structural singularity in {parent_block.name}. These variables cannot be replaced with the given system configuration."
            "Unmatched constraints: "
            f"{list(i.name for i in constraint_dm_partion.unmatched)}"
        )

    # Record the replacement (old_var, new_var) so that it can be tracked.

    if not hasattr(parent_block, "_replacements"):
        parent_block._replacements = []

    parent_block._replacements.append((state_var, new_var))

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
    

def pprint_replacements(block):
    """
    Pretty print all variables and replacements in the block
    """

    replacements = list_replacements(block)
    if len(replacements) == 0:
        print(f"No replacements in block {block.name}")
    else:
        print(f"Replacements in block {block.name}:")
        print("(Variable -> Replaced State Var)")
        for old_var, new_var in list_replacements(block):
            print(f"  {new_var} -> {old_var}")
        print()
    
    state_vars = list_fixed_state_vars(block)
    if len(state_vars) == 0:
        print(f"No other state variables in block {block.name}")
    else:
        print(f"Unreplaced state variables in block {block.name}:")
        for var in list_fixed_state_vars(block):
            print(f"  {var}")




obj_iter_kwds = dict(
    ctype=Port,
    active=True,
)

def register_inlet_ports(block):
    """
    This is a helper function to add all inlet variables to the state definition of a block.
    This is useful for unit models where the inlet variables are always state variables.
    """

    for port in block.component_objects(**obj_iter_kwds):
        if not hasattr(port, "is_inlet"):
            raise ValueError(
                f"Port {port.name} does not have the 'is_inlet' attribute. Please set this attribute to True for inlet ports and False for outlet ports. This is done automatically for Pyomo-Replace Unit Operations."
            )
        
        if len(port.sources()) == 0 and port.is_inlet:  # This is an inlet port
            # if not already, register the block
            parent_block = port.parent_block()
            # Initialise block if there are no state vars yet
            if not hasattr(parent_block, "_state_vars"):
                parent_block._state_vars = []
                parent_block._replacements = []
            # Add all variables in the port to the state vars if not already present
            for var_name in port.vars:
                var = getattr(port, var_name)
                if not _has_var(var, parent_block._state_vars):
                    var.fix()
                    parent_block._state_vars.append(var)

    