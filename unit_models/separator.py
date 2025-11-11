from idaes.models.unit_models import Heater
from idaes.core import declare_process_block_class
from idaes.models.unit_models.separator import SeparatorData, SplittingType
from model import register_block


@declare_process_block_class("SVSeparator")
class SVSeparatorData(SeparatorData):
    """
    Heater model, but it's set up with heat duty and deltaP as state variables.
    """

    def build(self,*args, **kwargs):
        """
        This method initializes the control volume and sets up the model.
        """
        super().build(*args, **kwargs)

        outlet_list = self.create_outlet_list()
        state_vars = []
        if self.config.split_basis == SplittingType.componentFlow:
            for outlet_name in outlet_list[:-1]: # exclude last outlet
                for compound in self.config.property_package.component_list:
                    state_vars.append(
                        self.split_fraction[outlet_name, compound]
                    )

        elif self.config.split_basis == SplittingType.totalFlow:
            for outlet_name in outlet_list[:-1]:
                state_vars.append(self.split_fraction[outlet_name])
        elif self.config.split_basis == SplittingType.phaseFlow:
            for outlet_name in outlet_list[:-1]:
                for phase in self.config.property_package.phase_list:
                    state_vars.append(
                        self.split_fraction_phase[outlet_name, phase]
                    )
        elif self.config.split_basis == SplittingType.phaseComponentFlow:
            for outlet_name in outlet_list[:-1]:
                for phase in self.config.property_package.phase_list:
                    for compound in self.config.property_package.get_phase_compounds(phase):
                        state_vars.append(
                            self.split_fraction_phase_compound[
                                outlet_name, phase, compound
                            ]
                        )
        else:
            raise ValueError(
                f"Unsupported split_basis {self.config.split_basis} "
                "in SVSeparator. This should never happen and is probably a bug."
            )

                
            
        
        
        # Setup the default state variables.
        # Allow_degrees_of_freedom is set to True because 
        # the inlet conditions are not fixed here.
        register_block(self, state_vars, allow_degrees_of_freedom=True)

        # We also need to set which ports are inlet and outlet, because 
        # IDAES doesn't store this information.
        self.inlet.is_inlet = True
        for outlet_name in outlet_list:
            outlet = getattr(self, outlet_name)
            outlet.is_inlet = False