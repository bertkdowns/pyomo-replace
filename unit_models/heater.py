from idaes.models.unit_models import Heater
from idaes.core import declare_process_block_class
from idaes.models.unit_models.heater import HeaterData
from model import SpecificationState
@declare_process_block_class("SVHeater")
class SVHeaterData(HeaterData):
    """
    Heater model with canonical variables for specification management.
    """

    def build(self,*args, **kwargs):
        """
        Build method for the DynamicHeaterData class.
        This method initializes the control volume and sets up the model.
        """
        super().build(*args, **kwargs)

        canonical_vars = [(self.heat_duty,"operation")]
        self.heat_duty.fix(100) # Default value
        if self.config.has_pressure_change:
            canonical_vars.append((self.deltaP,"design"))
            self.deltaP.fix(0) 
        if self.config.has_holdup:
            canonical_vars.append((self.control_volume.volume,"design"))
            canonical_vars.append((self.control_volume.energy_accumulation[0,"Liq"],"initial"))
            canonical_vars.append((self.control_volume.energy_accumulation[0,"Vap"],"initial"))
        
        # Setup the default canonical variables.
        # Allow_degrees_of_freedom is set to True because 
        # the inlet conditions are not fixed here.
        specifications = SpecificationState.for_flowsheet(self.flowsheet())
        specifications.register(canonical_vars)
        specifications.validate(self, allow_degrees_of_freedom=True)

        # We also need to set which ports are inlet and outlet, because 
        # IDAES doesn't store this information.
        self.inlet.is_inlet = True
        self.outlet.is_inlet = False
