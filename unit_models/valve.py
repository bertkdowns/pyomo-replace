from idaes.core import declare_process_block_class
from idaes.models.unit_models.valve import ValveData
from model import register_block, is_child_of

from idaes.core.util.exceptions import PropertyNotSupportedError, InitializationError
import idaes.logger as idaeslog
from idaes.core.solvers import get_solver
from pyomo.environ import (
    value,
    check_optimal_termination,
    Component,
    Reference,
    Var,
)
from model_initialisation import (
    record_model_definition,
    restore_model_definition,
    fix_replaced_state_vars,
    fix_state_vars,
    unfix_everything,
    staged_initialise,
)

@declare_process_block_class("SVValve")
class SVValveData(ValveData):
    """
    Heater model, but it's set up with heat duty and deltaP as state variables.
    """

    def build(self,*args, **kwargs):
        """
        This method initializes the control volume and sets up the model.
        """
        super().build(*args, **kwargs)

        state_vars = [self.valve_opening, self.Cv] # these can be used to calculate CV
        self.valve_opening.fix(0.9) # Default value
        self.Cv.fix(1)
        
        # Setup the default state variables.
        # Allow_degrees_of_freedom is set to True because 
        # the inlet conditions are not fixed here.
        register_block(self, state_vars, allow_degrees_of_freedom=True)

        # We also need to set which ports are inlet and outlet, because 
        # IDAES doesn't store this information.
        self.inlet.is_inlet = True
        self.outlet.is_inlet = False
    
    def initialize_build(
        blk,
        state_args=None,
        routine=None,
        outlvl=idaeslog.NOTSET,
        solver=None,
        optarg=None,
    ):
        """
        General wrapper for pressure changer initialization routines

        Keyword Arguments:
            routine : str stating which initialization routine to execute
                        * None - use routine matching thermodynamic_assumption
                        * 'isentropic' - use isentropic initialization routine
                        * 'isothermal' - use isothermal initialization routine
            state_args : a dict of arguments to be passed to the property
                         package(s) to provide an initial state for
                         initialization (see documentation of the specific
                         property package) (default = {}).
            outlvl : sets output level of initialization routine
            optarg : solver options dictionary object (default=None, use
                     default solver options)
            solver : str indicating which solver to use during
                     initialization (default = None, use default solver)

        Returns:
            None
        """
        init_log = idaeslog.getInitLogger(blk.name, outlvl, tag="unit")
        solve_log = idaeslog.getSolveLogger(blk.name, outlvl, tag="unit")

        # Create solver
        opt = get_solver(solver, optarg)

        cv = blk.control_volume
        t0 = blk.flowsheet().time.first()
        state_args_out = {}
        state = record_model_definition(blk)
        unfix_everything(blk)

        # Initialize state blocks
        properties_in_state_flags = cv.properties_in.initialize(
            outlvl=outlvl,
            optarg=optarg,
            solver=solver,
            hold_state=True,
            state_args=state_args,
        )
        cv.properties_out.initialize(
            outlvl=outlvl,
            optarg=optarg,
            solver=solver,
            hold_state=False,
            state_args=state_args_out,
        )
        init_log.info_high("Initialization Step 1 Complete.")

        # ---------------------------------------------------------------------
        # Solve unit.
        # 2 stage process:
        # 1. unfix everything, fix our state vars, and solve.
        # 2. if a state var has been replaced by something in this block,
        #  unfix it, fix that, and solve again.
        staged_initialise(blk, opt, outlvl)
        

        # ---------------------------------------------------------------------
        # Release Inlet state
        blk.control_volume.release_state(properties_in_state_flags, outlvl)

        restore_model_definition(blk, state)


    