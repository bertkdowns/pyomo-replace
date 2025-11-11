from idaes.models.unit_models import Heater
from idaes.core import declare_process_block_class
from idaes.models.unit_models.mixer import MixerData
from model import register_block


@declare_process_block_class("SVMixer")
class SVMixerData(MixerData):
    """
    Heater model, but it's set up with heat duty and deltaP as state variables.
    """

    def build(self,*args, **kwargs):
        """
        This method initializes the control volume and sets up the model.
        """
        super().build(*args, **kwargs)

        state_vars = [] # mixers don't have any degree of freedom
        
        # Setup the default state variables.
        # Allow_degrees_of_freedom is set to True because 
        # the inlet conditions are not fixed here.
        register_block(self, state_vars, allow_degrees_of_freedom=True)

        # We also need to set which ports are inlet and outlet, because 
        # IDAES doesn't store this information.
        inlet_list = self.create_inlet_list()
        for inlet_name in inlet_list:
            inlet = getattr(self, inlet_name)
            inlet.is_inlet = True
        self.outlet.is_inlet = False
