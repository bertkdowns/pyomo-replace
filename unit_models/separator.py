from idaes.models.unit_models import Heater
from idaes.core import declare_process_block_class
from idaes.models.unit_models.separator import SeparatorData, SplittingType
from model import SpecificationState


@declare_process_block_class("SVSeparator")
class SVSeparatorData(SeparatorData):
    """
    Separator model with canonical variables for specification management.
    """

    def build(self,*args, **kwargs):
        """
        This method initializes the control volume and sets up the model.
        """
        super().build(*args, **kwargs)

        outlet_list = self.create_outlet_list()
        canonical_vars = []
        if self.config.split_basis == SplittingType.componentFlow:
            for outlet_name in outlet_list[:-1]: # exclude last outlet
                for compound in self.config.property_package.component_list:
                    canonical_vars.append(
                        (self.split_fraction[outlet_name, compound], "operation")
                    )

        elif self.config.split_basis == SplittingType.totalFlow:
            for outlet_name in outlet_list[:-1]:
                canonical_vars.append((self.split_fraction[outlet_name], "operation"))
        elif self.config.split_basis == SplittingType.phaseFlow:
            for outlet_name in outlet_list[:-1]:
                for phase in self.config.property_package.phase_list:
                    canonical_vars.append(
                        (self.split_fraction_phase[outlet_name, phase], "operation")
                    )
        elif self.config.split_basis == SplittingType.phaseComponentFlow:
            for outlet_name in outlet_list[:-1]:
                for phase in self.config.property_package.phase_list:
                    for compound in self.config.property_package.get_phase_compounds(phase):
                        canonical_vars.append(
                            (self.split_fraction_phase_compound[
                                outlet_name, phase, compound
                            ], "operation")
                        )
        else:
            raise ValueError(
                f"Unsupported split_basis {self.config.split_basis} "
                "in SVSeparator. This should never happen and is probably a bug."
            )

                
            
        
        
        # Setup the default canonical variables.
        # Allow_degrees_of_freedom is set to True because 
        # the inlet conditions are not fixed here.
        specifications = SpecificationState.for_flowsheet(self.flowsheet())
        specifications.register(canonical_vars)
        specifications.validate(self, allow_degrees_of_freedom=True)

        # We also need to set which ports are inlet and outlet, because 
        # IDAES doesn't store this information.
        self.inlet.is_inlet = True
        for outlet_name in outlet_list:
            outlet = getattr(self, outlet_name)
            outlet.is_inlet = False
