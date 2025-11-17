from idaes.models.unit_models import Heater
from idaes.core import declare_process_block_class
from idaes.models.unit_models.pressure_changer import CompressorData
from model import register_block
from idaes.core.scaling.util import get_scaling_factor, set_scaling_factor
from idaes.core.scaling.custom_scaler_base import CustomScalerBase

@declare_process_block_class("SVCompressor")
class SVCompressorData(CompressorData):
    """
    Heater model, but it's set up with heat duty and deltaP as state variables.
    """

    def build(self,*args, **kwargs):
        """
        Build method for the DynamicHeaterData class.
        This method initializes the control volume and sets up the model.
        """
        super().build(*args, **kwargs)

        state_vars = [self.deltaP, self.efficiency_isentropic]
        self.deltaP.fix(100) # Default value
        self.efficiency_isentropic.fix(0.8)
        
        # Setup the default state variables.
        # Allow_degrees_of_freedom is set to True because 
        # the inlet conditions are not fixed here.
        register_block(self, state_vars, allow_degrees_of_freedom=True)

        # We also need to set which ports are inlet and outlet, because 
        # IDAES doesn't store this information.
        self.inlet.is_inlet = True
        self.outlet.is_inlet = False


# Trying to test scaling methods, decided not to include it.
def scale_model(compressor):
    """
    From the scaling factors of the state variables, set the scaling factors of everything else.
    """
    scaler = CustomScalerBase()

    nominal_temp = scaler.get_expression_nominal_values(compressor.inlet.temperature)
    nominal_enth = scaler.get_expression_nominal_values(compressor.inlet.enth_mol)
    nominal_flow = scaler.get_expression_nominal_values(compressor.inlet.flow_mol)
    nominal_pressure = scaler.get_expression_nominal_values(compressor.inlet.pressure)

    nominal_work = scaler.get_expression_nominal_values(compressor.work_mechanical)
    nominal_efficiency = scaler.get_expression_nominal_values(compressor.efficiency_isentropic)

    # set scaling factors for the outlet conditions
    nominal_outlet_enth = nominal_enth + nominal_work / nominal_flow
    # I'm not sure how valid this is, it's missing some kind of coefficient for work to pressure conversion. 
    # probably depends on the fluid which gets complicated.
    nominal_outlet_pressure = nominal_pressure + nominal_work/nominal_flow 

    # but here's the general idea of how it would work
    set_scaling_factor(compressor.outlet.temperature, 1/nominal_temp)
    set_scaling_factor(compressor.outlet.enth_mol, 1/nominal_outlet_enth)
    set_scaling_factor(compressor.outlet.flow_mol, 1/nominal_flow)
    set_scaling_factor(compressor.outlet.pressure, 1/nominal_outlet_pressure)
    
    