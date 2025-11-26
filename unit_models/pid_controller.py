from idaes.models.unit_models import Heater
from idaes.core import declare_process_block_class
from idaes.models.control.controller import PIDControllerData
from model import register_block, replace_state_var


@declare_process_block_class("SVPIDController")
class SVPIDControllerData(PIDControllerData):
    """
    PID Controller model
    """

    def build(self,*args, **kwargs):
        """
        This method initializes the control volume and sets up the model.
        """
        super().build(*args, **kwargs)

        state_vars = [self.gain_p,self.gain_i,self.mv_ref]
        
        # Setup the default state variables.
        # Allow_degrees_of_freedom is set to True because 
        # the inlet conditions are not fixed here.
        register_block(self, state_vars, allow_degrees_of_freedom=True)

        manipulated_var = self.config.manipulated_var
        # replace the manipulated variable ref with the setpoint (we can assume this is wanted so may as well do it automatically)
        replace_state_var(manipulated_var, self.setpoint)

