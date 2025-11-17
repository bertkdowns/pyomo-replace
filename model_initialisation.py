from idaes.models.unit_models.valve import ValveData
from model import is_child_of
from idaes.core.util.exceptions import PropertyNotSupportedError, InitializationError
import idaes.logger as idaeslog
from idaes.core.solvers import get_solver
from pyomo.environ import (
    value,
    check_optimal_termination,
    Component,
    Reference,
    Var,
    Block,
)
from pyomo.network import Port
from idaes.core.util.model_serializer import StoreSpec

from idaes.core.util.model_serializer import (
    to_json, from_json)


def record_model_definition(blk: Block) -> dict:
    """
    Record what variables are fixed in this block, and their values.
    This is needed so we can reset them later after initialisation is performed.


    Restore this with restore_model_definition().


    Example:
        state = record_model_definition(m.fs.unit)
        unfix_everything(m.fs.unit)
        # fix whatever default values you want for initialisation
        # solve the model to get some good initial values
        restore_model_definition(m.fs.unit, state)

    """
    state = to_json(blk,
                         wts=StoreSpec.value_isfixed(True), # only store any fixed values
                         return_dict=True)
    return state


def unfix_everything(blk):
    """
    Unfix all variables in the block. 

    Make sure to store the state first if you need to refix them later, e.g using record_model_definition()
    """

    # unfix all fixed variables (we have the state so we can refix later)
    for v in blk.component_data_objects(Var, descend_into=True):
        v.unfix()


def restore_model_definition(blk: Block, state: dict):
    """
    Re-fix all variables in the block using the stored state.
    This will leave the model mathematically unchanged from when record_model_definition() was called.
    However, any unfixed variables will have new initial values as a result
    of any calculations done previously.
    """
    unfix_everything(blk) # so no conflicts with existing fixed vars
    from_json(blk, sd=state, wts=StoreSpec.value_isfixed(True)) # only load the fixed values


def fix_state_vars(blk):
    """
    Fix the state variables for this block.

    This requires that the block has state variables registered (via calling register_state_vars on the block.).
    Usually this is done in the build() method of the block.
    """
    for var in blk._state_vars:
        var.fix()

def fix_replaced_state_vars(blk):
    """
    If any state variables have been replaced by other variables in this block,
    fix those variables instead of the state vars.

    The reason for doing this is to get the model closer to what the final solve state will be.
    We can only do this for variables that are children of this block.

    Any other variables that were fixed on this block but are not tied to a state variable in this block
    will not be fixed during initialization, as they require degrees of freedom from
    other unit operations so fixing them here would overconstrain the model.
    
    This requires that the block has state variables registered (via calling register_state_vars on the block.).
    Usually this is done in the build() method of the block.
    """
    for state_var, new_var in blk._replacements:
        if is_child_of(new_var, blk):
            new_var.fix() 
            state_var.unfix()

def fix_inlets(blk):
    """
    Fix all inlet port state variables.
    This assumes that the inlet port has been marked as an inlet (e.g. self.inlet.is_inlet = True)
    """
    for port in blk.component_data_objects(
        Port, descend_into=True
    ):
        if hasattr(port, "is_inlet") and port.is_inlet:
            port.fix_state()

def staged_initialise(blk: Block, opt, outlvl=idaeslog.NOTSET):
    """
    Performs a two-step initialization of the block.

    1. Fix the state variables and solve. Hopefully you've provided some good initial guesses.
    2. if a state var has been replaced by something in this block,
       unfix it, fix that, and solve again. That should get you closer to the true solution.
    
    This expects that the inlet and outlet state blocks have already been initialised.

    """
    init_log = idaeslog.getInitLogger(blk.name, outlvl, tag="unit")
    solve_log = idaeslog.getSolveLogger(blk.name, outlvl, tag="unit")

    # Peparation: Unfix everything first
    
    fix_state_vars(blk)
    #fix_inlets(blk)


    # Step 1: Solve with state vars fixed
    with idaeslog.solver_log(solve_log, idaeslog.DEBUG) as slc:
        res = opt.solve(blk, tee=slc.tee)
    init_log.info_high("Staged Initialisation: State var solve: {}.".format(idaeslog.condition(res)))
    
    if not check_optimal_termination(res):
        raise InitializationError(
            f"{blk.name} failed to initialize with state vars. Please check "
            f"the output logs for more information, or try different guesses."
        )

    fix_replaced_state_vars(blk)

    with idaeslog.solver_log(solve_log, idaeslog.DEBUG) as slc:
        res = opt.solve(blk, tee=slc.tee)
    init_log.info_high("Staged Initialisation: Replaced var solve: {}.".format(idaeslog.condition(res)))
    
    if not check_optimal_termination(res):
        raise InitializationError(
            f"{blk.name} failed to initialize with replaced vars. Please check "
            f"the output logs for more information, or make sure the model is well-posed."
        )

    

    init_log.info(f"Initialization Complete: {idaeslog.condition(res)}")

