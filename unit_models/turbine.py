from idaes.models.unit_models import Heater
from idaes.core import declare_process_block_class
from idaes.models.unit_models.pressure_changer import TurbineData
from model import register_block


@declare_process_block_class("SVTurbine")
class SVTurbineData(TurbineData):
    """
    Turbine model with canonical variables for specification management.
    """

    def build(self,*args, **kwargs):
        """
        Build method for the DynamicHeaterData class.
        This method initializes the control volume and sets up the model.
        """
        super().build(*args, **kwargs)

        canonical_vars = [(self.work_mechanical, "operation"), (self.efficiency_isentropic, "design")]
        self.work_mechanical.fix(100) # Default value
        self.efficiency_isentropic.fix(0.8)
        
        # Setup the default canonical variables.
        # Allow_degrees_of_freedom is set to True because 
        # the inlet conditions are not fixed here.
        register_block(self, canonical_vars, allow_degrees_of_freedom=True)

        # We also need to set which ports are inlet and outlet, because 
        # IDAES doesn't store this information.
        self.inlet.is_inlet = True
        self.outlet.is_inlet = False
