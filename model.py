from pyomo.environ import ConcreteModel, Block, Var, Expression, Constraint
from idaes.core.util.model_statistics import degrees_of_freedom
from pyomo.contrib.incidence_analysis import IncidenceGraphInterface

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


def register_block(block, state_vars: list):
    """
    This is used to identify which variables in the block should be the state variables.
    These variables, if fixed, should fully specify the block, i.e Degrees of freedom should be zero.
    """
    for v in state_vars:
        if v.parent_block() is not block:
            raise ValueError(
                f"Variable {v} is not part of the block {block.name} being registered"
            )
        v.fix()  # All state variables must be fixed to register the block.

    if degrees_of_freedom(block) > 0:
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
    return [var for var in list_state_vars(block) if not var.fixed]


def list_fixed_state_vars(block):
    """
    List all fixed state variables in the block and its sub-blocks recursively.
    """
    return [var for var in list_state_vars(block) if var.fixed]


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


def list_avaliable_vars(block):
    """
    List all avaliable variables (variables that are not state vars and are not fixed) in the block and its sub-blocks recursively.
    """
    return (
        var
        for var in block.component_objects(Var, descend_into=True)
        if var not in var.parent_block()._state_vars and not var.fixed
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
    parent_block = closest_common_parent(state_var, new_var)
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
    if not state_var.fixed:
        raise ValueError(f"Variable {state_var} must be fixed to be replaced.")
    # The new var must not be a state var, and must not be fixed.
    if hasattr(new_var_parent, "_state_vars") and is_in(
        new_var, new_var_parent._state_vars
    ):
        raise ValueError(
            f"Variable {new_var} is a registered state variable in the closest common parent block {parent_block.name}."
        )
    if new_var.fixed:
        raise ValueError(
            f"Variable {new_var} must not be fixed to be used as a replacement."
        )

    # Validate that degrees of freedom is zero before the replacement
    if degrees_of_freedom(parent_block) != 0:
        raise ValueError(
            f"Block {parent_block.name} must have zero degrees of freedom before replacement. Something is wrong with the model formulation. It currently has {degrees_of_freedom(parent_block)} degrees of freedom."
        )
    # Perform the replacement
    state_var.unfix()
    new_var.fix()

    if degrees_of_freedom(parent_block) != 0:
        # Revert the replacement
        state_var.fix()
        new_var.unfix()
        raise ValueError(
            f"Block {parent_block.name} must have zero degrees of freedom after replacement. Did you try to replace an indexed variable with one which has a different size?"
        )

    # Validate that this does not cause an over-constrained or under-constrained set.
    # https://pyomo.readthedocs.io/en/6.8.0/contributed_packages/incidence/tutorial.dm.html
    igraph = IncidenceGraphInterface(parent_block)
    var_dm_partition, constraint_dm_partion = igraph.dulmage_mendelsohn()

    if len(var_dm_partition.unmatched) > 0 or len(constraint_dm_partion.unmatched) > 0:
        # Revert the replacement
        state_var.fix()
        new_var.unfix()
        raise ValueError(
            f"Replacing variable {state_var} with {new_var} causes a structural singularity in {parent_block.name}. These variables cannot be replaced with the given system configuration."
        )

    # Record the replacement (old_var, new_var) so that it can be tracked.

    if not hasattr(parent_block, "_replacements"):
        parent_block._replacements = []

    parent_block._replacements.append((state_var, new_var))


def pprint_replacements(block):
    """
    Pretty print all variables and replacements in the block
    """
    
    replacements = list_replacements(block)
    if len(replacements) == 0:
        print(f"No replacements in block {block.name}")
        return
    else:
        print(f"Replacements in block {block.name}:")
        for old_var, new_var in list_replacements(block):
            print(f"  {old_var} -> {new_var}")
        print()
    
    state_vars = list_fixed_state_vars(block)
    if len(state_vars) == 0:
        print(f"No other state variables in block {block.name}")
    else:
        print(f"Unreplaced state variables in block {block.name}:")
        for var in list_fixed_state_vars(block):
            print(f"  {var}")
