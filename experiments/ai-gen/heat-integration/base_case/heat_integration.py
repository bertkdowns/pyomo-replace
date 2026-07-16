"""Steady-state water-only heat-integration flowsheet."""

from __future__ import annotations

import pyomo.environ as pyo
from pyomo.network import Arc, SequentialDecomposition
from pyomo.util.infeasible import log_infeasible_bounds, log_infeasible_constraints

import idaes.logger as idaeslog
from ahuora_builder.custom.custom_heater import DynamicHeater
from ahuora_builder.custom.custom_separator import CustomSeparator
from ahuora_builder.custom.thermal_utility_systems.simple_heat_pump import SimpleHeatPump
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


def specify_model(model: pyo.ConcreteModel) -> None:
    """Set the flowsheet's direct Pyomo variable specifications and guesses."""
    fs = model.fs
    water = fs.water

    fs.warm_water_splitter.inlet.flow_mol.fix(633.9523654525086)
    fs.warm_water_splitter.inlet.pressure.fix(100.0e3)
    fs.warm_water_splitter.inlet.enth_mol.fix(
        pyo.value(water.htpx(T=288.15 * pyo.units.K, p=100.0e3 * pyo.units.Pa)),
    )
    # The steam heat pump supplies a fixed sink duty while its mechanical work adjusts.
    fs.steam_heat_pump.work_mechanical.unfix()
    fs.steam_heat_pump.heat_duty.fix(720.0e3)

    fs.warm_water_splitter.split_fraction[TIME, "cooling_tower_1"].fix(0.4189275479610033)
    fs.warm_water_splitter.split_fraction[TIME, "cooling_tower_2"].fix(0.41892754796059345)

    fs.cooling_tower_1.heat_duty[TIME].fix(100.0e3)
    fs.cooling_tower_1.deltaP[TIME].fix(0.0)
    fs.cooling_tower_2.heat_duty[TIME].fix(100.0e3)
    fs.cooling_tower_2.deltaP[TIME].fix(0.0)

    fs.air_source_heat_pump.source_inlet.flow_mol[TIME].fix(1000.0)
    fs.air_source_heat_pump.source_inlet.pressure[TIME].fix(100.0e3)
    fs.air_source_heat_pump.source_inlet.enth_mol[TIME].fix(
        pyo.value(water.htpx(T=298.15 * pyo.units.K, p=100.0e3 * pyo.units.Pa)),
    )
    fs.air_source_heat_pump.work_mechanical[TIME].fix(100.0e3)
    fs.air_source_heat_pump.approach_temperature.fix(10.0)
    fs.air_source_heat_pump.heat_duty[TIME].fix(315.838167e3)
    fs.air_source_heat_pump.coefficient_of_performance.unfix()
    fs.air_source_heat_pump.efficiency.unfix()

    fs.steam_heat_pump.approach_temperature.fix(5.0)
    fs.steam_heat_pump.efficiency.fix(0.54)

    fs.steam_demand_splitter.inlet.flow_mol[TIME].fix(23.128530015022072)
    fs.steam_demand_splitter.inlet.pressure[TIME].fix(1000.0e3)
    fs.steam_demand_splitter.inlet.enth_mol[TIME].fix(13349.6505)
    fs.steam_demand_splitter.split_fraction[TIME, "steam_heat_pump"].fix(0.848685511446811)
    fs.gas_boiler.deltaP[TIME].fix(0.0)

    fs.gas_boiler.control_volume.properties_out[TIME].enth_mol.fix(
        pyo.value(water.htpx(p=1000.0e3 * pyo.units.Pa, x=1.0)),
    )
    debug_model(model)
    if degrees_of_freedom(model) != 0:
        raise RuntimeError("The fully specified model must have zero degrees of freedom.")


def debug_model(model: pyo.ConcreteModel) -> None:
    """Print structural degree-of-freedom status and unit reports."""
    fs = model.fs
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


def initialise_model(model: pyo.ConcreteModel) -> None:
    """Initialize the flowsheet units in sequential order."""
    fs = model.fs
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
    """Initialize and solve the model with its direct variable specifications."""
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
