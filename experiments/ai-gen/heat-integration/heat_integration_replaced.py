"""Steady-state water-only heat-integration flowsheet."""

from __future__ import annotations

import pyomo.environ as pyo
from pyomo.network import Arc, SequentialDecomposition
from pyomo.util.infeasible import log_infeasible_bounds, log_infeasible_constraints

import idaes.logger as idaeslog
from ahuora_builder.custom.custom_heater import DynamicHeater
from ahuora_builder.custom.custom_separator import CustomSeparator
from ahuora_builder.custom.thermal_utility_systems.simple_heat_pump import SimpleHeatPump
from ahuora_builder.replacement.specifications import SpecificationState
from ahuora_property_packages.helmholtz.helmholtz_builder import build_helmholtz_package
from idaes.core import FlowsheetBlock
from idaes.core.solvers import get_solver
from idaes.core.util.model_statistics import degrees_of_freedom
from idaes.models.unit_models import Mixer, MomentumMixingType
from idaes.core.util.model_diagnostics import DiagnosticsToolbox


TIME = 0


def build_heat_integration_model() -> pyo.ConcreteModel:
    """Build, connect, and specify the heat-integration model."""
    model = pyo.ConcreteModel()
    model.fs = FlowsheetBlock(dynamic=False)
    setup_model(model)
    specify_model(model)
    return model


def setup_model(model: pyo.ConcreteModel) -> None:
    """Create property packages, unit operations, and process arcs."""
    fs = model.fs
    fs.water = build_helmholtz_package(["water"])
    fs.warm_water_splitter = CustomSeparator(
        property_package=fs.water,
        outlet_list=["cooling_tower_1", "cooling_tower_2", "air_source_sink"],
    )
    fs.cooling_tower_1 = DynamicHeater(property_package=fs.water, has_pressure_change=True)
    fs.cooling_tower_2 = DynamicHeater(property_package=fs.water, has_pressure_change=True)
    fs.air_source_heat_pump = SimpleHeatPump(
        source={"property_package": fs.water, "has_pressure_change": False},
        sink={"property_package": fs.water, "has_pressure_change": False},
    )
    fs.waste_heat_mixer = Mixer(
        property_package=fs.water,
        inlet_list=["cooling_tower_1", "cooling_tower_2", "air_source_sink"],
        momentum_mixing_type=MomentumMixingType.minimize,
    )
    fs.steam_heat_pump = SimpleHeatPump(
        source={"property_package": fs.water, "has_pressure_change": False},
        sink={"property_package": fs.water, "has_pressure_change": False},
    )
    fs.steam_demand_splitter = CustomSeparator(
        property_package=fs.water,
        outlet_list=["steam_heat_pump", "gas_boiler"],
    )
    fs.gas_boiler = DynamicHeater(property_package=fs.water, has_pressure_change=True)
    fs.steam_mixer = Mixer(
        property_package=fs.water,
        inlet_list=["steam_heat_pump", "gas_boiler"],
        momentum_mixing_type=MomentumMixingType.minimize,
    )
    fs.warm_water_to_cooling_tower_1 = Arc(
        source=fs.warm_water_splitter.cooling_tower_1,
        destination=fs.cooling_tower_1.inlet,
    )
    fs.warm_water_to_cooling_tower_2 = Arc(
        source=fs.warm_water_splitter.cooling_tower_2,
        destination=fs.cooling_tower_2.inlet,
    )
    fs.warm_water_to_air_source_heat_pump = Arc(
        source=fs.warm_water_splitter.air_source_sink,
        destination=fs.air_source_heat_pump.sink_inlet,
    )
    fs.cooling_tower_1_to_waste_heat = Arc(
        source=fs.cooling_tower_1.outlet,
        destination=fs.waste_heat_mixer.cooling_tower_1,
    )
    fs.cooling_tower_2_to_waste_heat = Arc(
        source=fs.cooling_tower_2.outlet,
        destination=fs.waste_heat_mixer.cooling_tower_2,
    )
    fs.air_source_heat_pump_to_waste_heat = Arc(
        source=fs.air_source_heat_pump.sink_outlet,
        destination=fs.waste_heat_mixer.air_source_sink,
    )
    fs.waste_heat_to_steam_heat_pump = Arc(
        source=fs.waste_heat_mixer.outlet,
        destination=fs.steam_heat_pump.source_inlet,
    )
    fs.steam_demand_to_steam_heat_pump = Arc(
        source=fs.steam_demand_splitter.steam_heat_pump,
        destination=fs.steam_heat_pump.sink_inlet,
    )
    fs.steam_demand_to_gas_boiler = Arc(
        source=fs.steam_demand_splitter.gas_boiler,
        destination=fs.gas_boiler.inlet,
    )
    fs.steam_heat_pump_to_header = Arc(
        source=fs.steam_heat_pump.sink_outlet,
        destination=fs.steam_mixer.steam_heat_pump,
    )
    fs.gas_boiler_to_header = Arc(
        source=fs.gas_boiler.outlet,
        destination=fs.steam_mixer.gas_boiler,
    )
    pyo.TransformationFactory("network.expand_arcs").apply_to(model)
    specs = SpecificationState.for_flowsheet(fs)
    specs.register_unconnected_inlets()


def specify_model(model: pyo.ConcreteModel) -> None:
    """Set specifications and guesses, then activate all replacement targets."""
    fs = model.fs
    specs = SpecificationState.for_flowsheet(fs)
    water = fs.water
        
    # This provides examples of fixing feed-port conditions.
    # These variables can be fixed using specs.fix() as they are canonical variables.
    # The list of canonical variables is shown in debug_model() output.
    specs.fix(fs.warm_water_splitter.inlet.flow_mol, 633.9523654525086)
    specs.fix(fs.warm_water_splitter.inlet.pressure, 100.0e3)
    specs.fix(
        fs.warm_water_splitter.inlet.enth_mol,
        pyo.value(water.htpx(T=288.15 * pyo.units.K, p=100.0e3 * pyo.units.Pa)),
    )
    # The steam heat pump supplies a fixed sink duty while its mechanical work adjusts.
    specs.replace(fs.steam_heat_pump.work_mechanical, fs.steam_heat_pump.heat_duty)
    specs.fix(fs.steam_heat_pump.heat_duty, 720.0e3)
    print("Initial Specification State:")
    specs.report(fs)

    # CONTINUE IMPLEMENTING HERE.






    debug_model(model)
    if degrees_of_freedom(model) != 0:
        raise RuntimeError("The fully specified model must have zero degrees of freedom.")


def debug_model(model: pyo.ConcreteModel) -> None:
    """Print the model's specification state and structural degree-of-freedom status."""
    fs = model.fs
    specs = fs.specifications
    print(f"Degrees of freedom: {degrees_of_freedom(model)}")
    dt = DiagnosticsToolbox(model)
    dt.display_overconstrained_set()
    dt.display_underconstrained_set()
    fs.warm_water_splitter.report()
    fs.cooling_tower_1.report()
    fs.cooling_tower_2.report()
    fs.air_source_heat_pump.report()
    fs.waste_heat_mixer.report()
    fs.steam_heat_pump.report()
    fs.steam_demand_splitter.report()
    fs.gas_boiler.report()
    fs.steam_mixer.report()
    # This prints the canonical variables, and if they are replaced, the replacement variable.
    # The replacement system is used to maintain zero degrees of freedom; if you want to fix
    # a different variable, you have to replace a canonical variable with it (to maintain zero degrees of freedom).
    specs.report(fs)


def initialise_model(model: pyo.ConcreteModel) -> None:
    """Initialize in sequential order while replacements are temporarily reverted."""
    fs = model.fs
    specifications = fs.specifications
    sequence = SequentialDecomposition(run_first_pass=True)
    sequence.options.tear_method = "Wegstein"
    sequence.options.iterLim = 5
    sequence.options.tol = 1e-6
    sequence.options.solve_tears = False
    graph = sequence.create_graph(model)
    tears = sequence.tear_set_arcs(graph, method="heuristic")
    sequence.set_tear_set(tears)
    for tear in tears:
        sequence.set_guesses_for(
            tear.destination,
            {
                name: {TIME: pyo.value(variable[TIME])}
                for name, variable in tear.destination.vars.items()
                if TIME in variable
            },
        )
    print("Initialising model with sequential decomposition...")
    with specifications.replacements_suspended_in(fs):
        sequence.run(model, lambda unit: unit.initialize(outlvl=idaeslog.INFO))
        initial_results = get_solver().solve(model, tee=True, load_solutions=False)
        if initial_results.solver.termination_condition != pyo.TerminationCondition.optimal:
            diagnose_failed_solve(model)
            raise RuntimeError(f"Initial solve failed: {initial_results.solver.termination_condition}")
        model.solutions.load_from(initial_results)


def diagnose_failed_solve(model: pyo.ConcreteModel) -> None:
    """Print infeasibilities and custom unit diagnostics after a failed solve."""
    logger = idaeslog.getLogger(__name__)
    log_infeasible_constraints(model, tol=1e-6, logger=logger)
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
    """Initialize a model, restore replacements, and solve its final specification state."""
    model = build_heat_integration_model() if model is None else model
    initialise_model(model)
    print("Performing final solve...")
    results = get_solver().solve(model, tee=True, load_solutions=False)
    if results.solver.termination_condition != pyo.TerminationCondition.optimal:
        diagnose_failed_solve(model)
        raise RuntimeError(f"Final solve failed: {results.solver.termination_condition}")
    model.solutions.load_from(results)
    return model, results


if __name__ == "__main__":
    solved_model, _results = solve()
