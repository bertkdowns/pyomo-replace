from idaes.models.unit_models import Heater
from idaes.core import declare_process_block_class
from idaes.models.control.controller import PIDControllerData
from model import register_block, replacement_state


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

        canonical_vars = [(self.gain_p,"operation"),(self.gain_i,"operation"),(self.mv_ref,"operation")]
        
        # Setup the default canonical variables.
        # Allow_degrees_of_freedom is set to True because 
        # the inlet conditions are not fixed here.
        register_block(self, canonical_vars, allow_degrees_of_freedom=True)

        manipulated_var = self.config.manipulated_var
        # replace the manipulated variable ref with the setpoint (we can assume this is wanted so may as well do it automatically)
        replacement_state(self).replace(manipulated_var, self.setpoint)
