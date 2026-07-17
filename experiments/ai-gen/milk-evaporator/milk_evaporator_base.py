"""Steady-state three-effect milk evaporator with MVR heat recovery."""

from __future__ import annotations

import pyomo.environ as pyo
from pyomo.network import Arc, SequentialDecomposition
from pyomo.util.infeasible import log_infeasible_bounds, log_infeasible_constraints

import idaes.logger as idaeslog
from ahuora_builder.custom.custom_heat_exchanger import CustomHeatExchanger
from ahuora_builder.custom.custom_separator import CustomSeparator
from ahuora_builder.custom.direct_steam_injection import Dsi
from ahuora_builder.custom.translator import GenericTranslator, TranslatorType
from ahuora_builder.custom.updated_pressure_changer import Compressor
from ahuora_builder.custom.valve_wrapper import ValveWrapper
from ahuora_property_packages.helmholtz.helmholtz_builder import build_helmholtz_package
from ahuora_property_packages.milk.milk_builder import build_milk_package
from idaes.core import FlowsheetBlock
from idaes.core.solvers import get_solver
from idaes.core.util.model_statistics import degrees_of_freedom
from idaes.models.unit_models.separator import SplittingType
from idaes.core.util.model_diagnostics import DiagnosticsToolbox


TIME = 0


def build_milk_evaporator() -> pyo.ConcreteModel:
    """Build, connect, and specify the three-effect milk evaporator model."""
    model = pyo.ConcreteModel()
    model.fs = FlowsheetBlock(dynamic=False)
    setup_model(model)
    specify_model(model)
    return model


def setup_model(model: pyo.ConcreteModel) -> None:
    """Create property packages, unit operations, and process arcs."""
    fs = model.fs
    fs.milk = build_milk_package(["water", "milk_solid"])
    fs.water = build_helmholtz_package(["water"])
    fs.direct_steam_injection = Dsi(
        property_package=fs.milk,
        steam_property_package=fs.water,
    )
    fs.E1Valve = ValveWrapper(property_package=fs.milk)
    fs.E2Valve = ValveWrapper(property_package=fs.milk)
    fs.E3Valve = ValveWrapper(property_package=fs.milk)
    fs.E1HX = CustomHeatExchanger(
        hot_side_name="shell",
        cold_side_name="tube",
        shell={"property_package": fs.water, "has_pressure_change": True},
        tube={"property_package": fs.milk, "has_pressure_change": True},
    )
    fs.E2HX = CustomHeatExchanger(
        hot_side_name="shell",
        cold_side_name="tube",
        shell={"property_package": fs.water, "has_pressure_change": True},
        tube={"property_package": fs.milk, "has_pressure_change": True},
    )
    fs.HeatExchanger3 = CustomHeatExchanger(
        hot_side_name="shell",
        cold_side_name="tube",
        shell={"property_package": fs.water, "has_pressure_change": True},
        tube={"property_package": fs.milk, "has_pressure_change": True},
    )
    fs.E1PS = CustomSeparator(
        property_package=fs.milk,
        num_outlets=2,
        split_basis=SplittingType.phaseFlow,
    )
    fs.E2PS = CustomSeparator(
        property_package=fs.milk,
        num_outlets=2,
        split_basis=SplittingType.phaseFlow,
    )
    fs.PhaseSeparator3 = CustomSeparator(
        property_package=fs.milk,
        num_outlets=2,
        split_basis=SplittingType.phaseFlow,
    )
    fs.Translator1 = GenericTranslator(
        inlet_property_package=fs.milk,
        outlet_property_package=fs.water,
        translator_type=TranslatorType.pressure_enthalpy.value,
    )
    fs.Translator2 = GenericTranslator(
        inlet_property_package=fs.milk,
        outlet_property_package=fs.water,
        translator_type=TranslatorType.pressure_enthalpy.value,

    )
    fs.Translator3 = GenericTranslator(
        inlet_property_package=fs.milk,
        outlet_property_package=fs.water,
        translator_type=TranslatorType.pressure_enthalpy.value,
    )
    fs.Compressor1 = Compressor(property_package=fs.water)
    fs.E2MVR = Compressor(property_package=fs.water)
    fs.Compressor3 = Compressor(property_package=fs.water)
    fs.dsi_to_E1Valve = Arc(source=fs.direct_steam_injection.outlet, destination=fs.E1Valve.inlet)
    fs.E1Valve_to_E1HX = Arc(source=fs.E1Valve.outlet, destination=fs.E1HX.tube_inlet)
    fs.Compressor1_to_E1HX = Arc(source=fs.Compressor1.outlet, destination=fs.E1HX.shell_inlet)
    fs.E1HX_to_E1PS = Arc(source=fs.E1HX.tube_outlet, destination=fs.E1PS.inlet)
    fs.E1PS_to_E2Valve = Arc(source=fs.E1PS.outlet_1, destination=fs.E2Valve.inlet)
    fs.E1PS_to_Translator1 = Arc(source=fs.E1PS.outlet_2, destination=fs.Translator1.inlet)
    fs.Translator1_to_Compressor1 = Arc(source=fs.Translator1.outlet, destination=fs.Compressor1.inlet)
    fs.E2Valve_to_E2HX = Arc(source=fs.E2Valve.outlet, destination=fs.E2HX.tube_inlet)
    fs.E2MVR_to_E2HX = Arc(source=fs.E2MVR.outlet, destination=fs.E2HX.shell_inlet)
    fs.E2HX_to_E2PS = Arc(source=fs.E2HX.tube_outlet, destination=fs.E2PS.inlet)
    fs.E2PS_to_E3Valve = Arc(source=fs.E2PS.outlet_1, destination=fs.E3Valve.inlet)
    fs.E2PS_to_Translator2 = Arc(source=fs.E2PS.outlet_2, destination=fs.Translator2.inlet)
    fs.Translator2_to_E2MVR = Arc(source=fs.Translator2.outlet, destination=fs.E2MVR.inlet)
    fs.E3Valve_to_E3HX = Arc(source=fs.E3Valve.outlet, destination=fs.HeatExchanger3.tube_inlet)
    fs.Compressor3_to_E3HX = Arc(source=fs.Compressor3.outlet, destination=fs.HeatExchanger3.shell_inlet)
    fs.E3HX_to_E3PS = Arc(source=fs.HeatExchanger3.tube_outlet, destination=fs.PhaseSeparator3.inlet)
    fs.E3PS_to_Translator3 = Arc(source=fs.PhaseSeparator3.outlet_2, destination=fs.Translator3.inlet)
    fs.Translator3_to_Compressor3 = Arc(source=fs.Translator3.outlet, destination=fs.Compressor3.inlet)
    pyo.TransformationFactory("network.expand_arcs").apply_to(model)


def specify_model(model: pyo.ConcreteModel) -> None:
    """Set the model specifications and initial value guesses."""
    fs = model.fs
    water = fs.water
    fs.direct_steam_injection.inlet.mole_frac_comp[TIME, "water"].set_value(0.994)
    fs.direct_steam_injection.inlet.mole_frac_comp[TIME, "milk_solid"].set_value(0.006)
    fs.direct_steam_injection.inlet.mole_frac_comp.fix()
    fs.direct_steam_injection.steam_inlet.flow_mol.fix(0.853)
    fs.direct_steam_injection.steam_inlet.pressure.fix(200.0e3)
    fs.direct_steam_injection.steam_inlet.enth_mol.fix(
        pyo.value(water.htpx(T=393.41 * pyo.units.K, p=200.0e3 * pyo.units.Pa)),
    )
    fs.Compressor3.outlet.pressure.fix(72.0e3)

    # Continue implementing the model here.
    

    debug_model(model)
    if degrees_of_freedom(model) != 0:
        raise RuntimeError("The fully specified model must have zero degrees of freedom.")


def debug_model(model: pyo.ConcreteModel) -> None:
    """Print the model's structural degree-of-freedom status."""
    fs = model.fs
    print(f"Degrees of freedom: {degrees_of_freedom(model)}")
    dt = DiagnosticsToolbox(model)
    dt.display_overconstrained_set()
    dt.display_underconstrained_set()
    for unit in fs.component_data_objects(pyo.Block, descend_into=False, active=True):
        if hasattr(unit, "report"):
            unit.report()


def initialise_model(model: pyo.ConcreteModel) -> None:
    """Initialize the model in sequential order."""
    fs = model.fs
    sequence = SequentialDecomposition(iterLim=3)
    tears = [
        fs.Compressor1_to_E1HX,
        fs.E2MVR_to_E2HX,
        fs.Compressor3_to_E3HX,
    ]
    sequence.set_tear_set(tears)
    # These torn arcs carry the recompressed vapor that drives each effect.
    # Estimate the recycle flow from the exchanger UA and the expected
    # saturated-vapor temperature rise above the corresponding liquor effect.
    sequence.set_guesses_for(
        fs.E1HX.shell_inlet,
        {
            "flow_mol": {TIME: 0.8},
            "pressure": {TIME: 80.0e3},
            "enth_mol": {
                TIME: pyo.value(fs.water.htpx(p=80.0e3 * pyo.units.Pa, x=1))
            },
        },
    )
    sequence.set_guesses_for(
        fs.E2HX.shell_inlet,
        {
            "flow_mol": {TIME: 0.2},
            "pressure": {TIME: 56.0e3},
            "enth_mol": {
                TIME: pyo.value(fs.water.htpx(p=56.0e3 * pyo.units.Pa, x=1))
            },
        },
    )
    sequence.set_guesses_for(
        fs.HeatExchanger3.shell_inlet,
        {
            "flow_mol": {TIME: 0.03},
            "pressure": {TIME: 72.0e3},
            "enth_mol": {
                TIME: pyo.value(fs.water.htpx(p=72.0e3 * pyo.units.Pa, x=1))
            },
        },
    )
    print("Initialising model with sequential decomposition...")
    if degrees_of_freedom(model) != 0:
        raise RuntimeError("The fully specified model must have zero degrees of freedom.")
    def run_init(unit):
        unit.initialize(outlvl=idaeslog.WARNING)
    sequence.run(model, run_init )
    if degrees_of_freedom(model) != 0:
        raise RuntimeError(f"The fully specified model must have zero degrees of freedom. got {degrees_of_freedom(model)}")



def diagnose_failed_solve(model: pyo.ConcreteModel) -> None:
    """Print infeasibilities and custom unit diagnostics after a failed solve."""
    diagnose_toolbox = DiagnosticsToolbox(model)
    diagnose_toolbox.display_overconstrained_set()
    diagnose_toolbox.display_variables_at_or_outside_bounds()
    logger = idaeslog.getLogger(__name__)
    #log_infeasible_constraints(model, tol=1e-6, logger=logger)
    log_infeasible_bounds(model, tol=1e-6, logger=logger)
    print("Diagnosing failed solve...")
    for unit in model.fs.component_data_objects(pyo.Block, descend_into=False, active=True):
        if not hasattr(unit, "diagnose"):
            continue
        try:
            for component, message in unit.diagnose():
                print(f"Unit diagnostic [{component.name}]: {message}")
        except Exception as error:
            print(f"Unit diagnostic [{unit.name}]: {type(error).__name__}: {error}")


def solve(model: pyo.ConcreteModel | None = None):
    """Initialize and solve the model."""
    model = build_milk_evaporator() if model is None else model
    initialise_model(model)
    print("Performing final solve...")
    results = get_solver().solve(model,options={"max_iter": 1000}, tee=True, load_solutions=False)
    if results.solver.termination_condition != pyo.TerminationCondition.optimal:
        diagnose_failed_solve(model)
        debug_model(model)
        raise RuntimeError(f"Final solve failed: {results.solver.termination_condition}")
    model.solutions.load_from(results)
    return model, results


if __name__ == "__main__":
    solved_model, _results = solve()
