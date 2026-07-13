from idaes.models.unit_models import Heater
from idaes.core import declare_process_block_class
from idaes.models.unit_models.mixer import MixerData
from model import SpecificationState


@declare_process_block_class("SVMixer")
class SVMixerData(MixerData):
    """
    Mixer model with canonical variables for specification management.
    """

    def build(self,*args, **kwargs):
        """
        This method initializes the control volume and sets up the model.
        """
        super().build(*args, **kwargs)

        canonical_vars = [] # mixers don't have any degree of freedom
        
        # Setup the default canonical variables.
        # Allow_degrees_of_freedom is set to True because 
        # the inlet conditions are not fixed here.
        specifications = SpecificationState.for_flowsheet(self.flowsheet())
        specifications.register(canonical_vars)
        specifications.validate(self, allow_degrees_of_freedom=True)

        # We also need to set which ports are inlet and outlet, because 
        # IDAES doesn't store this information.
        inlet_list = self.create_inlet_list()
        for inlet_name in inlet_list:
            inlet = getattr(self, inlet_name)
            inlet.is_inlet = True
        self.outlet.is_inlet = False
