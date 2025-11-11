from idaes.models.unit_models import Heater
from idaes.core import declare_process_block_class
from idaes.models.unit_models.heat_exchanger import HeatExchangerData
from model import register_block

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
