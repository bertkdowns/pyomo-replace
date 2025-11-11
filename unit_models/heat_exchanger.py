from idaes.core import declare_process_block_class
from idaes.models.unit_models.heat_exchanger import HeatExchangerData
from model import register_block
import idaes.logger as idaeslog
from idaes.core.util.exceptions import ConfigurationError, InitializationError
from idaes.core.solvers import get_solver
# Import Pyomo libraries
from pyomo.environ import (
    units as pyunits,
    check_optimal_termination,
)

@declare_process_block_class("SVHeatExchanger")
class SVHeatExchangerData(HeatExchangerData):
    """
    Heater model, but it's set up with heat duty and deltaP as state variables.
    """

    def build(self,*args, **kwargs):
        """
        Build method for the DynamicHeaterData class.
        This method initializes the control volume and sets up the model.
        """
        super().build(*args, **kwargs)

        state_vars = [self.overall_heat_transfer_coefficient, self.area]
        self.overall_heat_transfer_coefficient.fix(50) # Default value
        self.area.fix(5)

        hot_side = self.hot_side
        cold_side = self.cold_side
        
        if self.config.hot_side.has_pressure_change:
            state_vars.append(hot_side.deltaP)
            hot_side.deltaP.fix(0)
        if self.config.cold_side.has_pressure_change:
            state_vars.append(cold_side.deltaP)
            cold_side.deltaP.fix(0)
        
        # Setup the default state variables.
        # Allow_degrees_of_freedom is set to True because 
        # the inlet conditions are not fixed here.
        register_block(self, state_vars, allow_degrees_of_freedom=True)

        # We also need to set which ports are inlet and outlet, because 
        # IDAES doesn't store this information.
        hot_side_inlet = getattr(self, "hot_side_inlet")
        cold_side_inlet = getattr(self, "cold_side_inlet")
        hot_side_outlet = getattr(self, "hot_side_outlet")
        cold_side_outlet = getattr(self, "cold_side_outlet")
        hot_side_inlet.is_inlet = True
        cold_side_inlet.is_inlet = True
        hot_side_outlet.is_inlet = False
        cold_side_outlet.is_inlet = False
    

    def initialize_build(
        self,
        state_args_1=None,
        state_args_2=None,
        outlvl=idaeslog.NOTSET,
        solver=None,
        optarg=None,
        duty=None,
    ):
        """
        Heat exchanger initialization method.

        Args:
            state_args_1 : a dict of arguments to be passed to the property
                initialization for the hot side (see documentation of the specific
                property package) (default = {}).
            state_args_2 : a dict of arguments to be passed to the property
                initialization for the cold side (see documentation of the specific
                property package) (default = {}).
            outlvl : sets output level of initialization routine
            optarg : solver options dictionary object (default=None, use
                     default solver options)
            solver : str indicating which solver to use during
                     initialization (default = None, use default solver)
            duty : an initial guess for the amount of heat transferred. This
                should be a tuple in the form (value, units), (default
                = (1000 J/s))

        Returns:
            None

        """
        # Set solver options
        init_log = idaeslog.getInitLogger(self.name, outlvl, tag="unit")
        solve_log = idaeslog.getSolveLogger(self.name, outlvl, tag="unit")

        # Create solver
        opt = get_solver(solver, optarg)

        flags1 = self.hot_side.initialize(
            outlvl=outlvl, optarg=optarg, solver=solver, state_args=state_args_1
        )

        init_log.info_high("Initialization Step 1a (hot side) Complete.")

        flags2 = self.cold_side.initialize(
            outlvl=outlvl, optarg=optarg, solver=solver, state_args=state_args_2
        )

        init_log.info_high("Initialization Step 1b (cold side) Complete.")
        # ---------------------------------------------------------------------
        # Solve unit without heat transfer equation
        self.heat_transfer_equation.deactivate()

        # Get side 1 and side 2 heat units, and convert duty as needed
        s1_units = self.hot_side.heat.get_units()
        s2_units = self.cold_side.heat.get_units()

        # Check to see if heat duty is fixed
        # WE will assume that if the first point is fixed, it is fixed at all points
        if not self.cold_side.heat[self.flowsheet().time.first()].fixed:
            cs_fixed = False
            if duty is None:
                # Assume 1000 J/s and check for unitless properties
                if s1_units is None and s2_units is None:
                    # Backwards compatibility for unitless properties
                    s1_duty = -1000
                    s2_duty = 1000
                else:
                    s1_duty = pyunits.convert_value(
                        -1000, from_units=pyunits.W, to_units=s1_units
                    )
                    s2_duty = pyunits.convert_value(
                        1000, from_units=pyunits.W, to_units=s2_units
                    )
            else:
                # Duty provided with explicit units
                s1_duty = -pyunits.convert_value(
                    duty[0], from_units=duty[1], to_units=s1_units
                )
                s2_duty = pyunits.convert_value(
                    duty[0], from_units=duty[1], to_units=s2_units
                )

            self.cold_side.heat.fix(s2_duty)
            for i in self.hot_side.heat:
                self.hot_side.heat[i].value = s1_duty
        else:
            cs_fixed = True
            for i in self.hot_side.heat:
                self.hot_side.heat[i].set_value(self.cold_side.heat[i])

        with idaeslog.solver_log(solve_log, idaeslog.DEBUG) as slc:
            res = opt.solve(self, tee=slc.tee)
        init_log.info_high("Initialization Step 2 {}.".format(idaeslog.condition(res)))
        if not cs_fixed:
            self.cold_side.heat.unfix()
        self.heat_transfer_equation.activate()
        # ---------------------------------------------------------------------
        # Solve unit
        with idaeslog.solver_log(solve_log, idaeslog.DEBUG) as slc:
            res = opt.solve(self, tee=slc.tee)
        init_log.info_high("Initialization Step 3 {}.".format(idaeslog.condition(res)))
        # ---------------------------------------------------------------------
        # Release Inlet state
        self.hot_side.release_state(flags1, outlvl=outlvl)
        self.cold_side.release_state(flags2, outlvl=outlvl)

        init_log.info("Initialization Completed, {}".format(idaeslog.condition(res)))

        if not check_optimal_termination(res):
            raise InitializationError(
                f"{self.name} failed to initialize successfully. Please check "
                f"the output logs for more information."
            )
