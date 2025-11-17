from idaes.models.unit_models import Heater
from idaes.core import declare_process_block_class
from idaes.models.unit_models.heater import HeaterData
from model import register_block
@declare_process_block_class("SVHeater")
class SVHeaterData(HeaterData):
    """
    Heater model, but it's set up with heat duty and deltaP as state variables.
    """

    def build(self,*args, **kwargs):
        """
        Build method for the DynamicHeaterData class.
        This method initializes the control volume and sets up the model.
        """
        super().build(*args, **kwargs)

        state_vars = [self.heat_duty]
        self.heat_duty.fix(100) # Default value
        if self.config.has_pressure_change:
            state_vars.append(self.deltaP)
            self.deltaP.fix(0) 
        if self.config.has_holdup:
            state_vars.append(self.control_volume.volume)
            state_vars.append(self.control_volume.energy_accumulation[0,"Liq"])
            state_vars.append(self.control_volume.energy_accumulation[0,"Vap"])
        
        # Setup the default state variables.
        # Allow_degrees_of_freedom is set to True because 
        # the inlet conditions are not fixed here.
        register_block(self, state_vars, allow_degrees_of_freedom=True)

        # We also need to set which ports are inlet and outlet, because 
        # IDAES doesn't store this information.
        self.inlet.is_inlet = True
        self.outlet.is_inlet = False
