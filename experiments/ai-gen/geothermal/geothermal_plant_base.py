"""Steady-state geothermal-heated n-butane power-loop flowsheet."""

from __future__ import annotations

import pyomo.environ as pyo
from pyomo.network import Arc, SequentialDecomposition
from pyomo.util.infeasible import log_infeasible_bounds, log_infeasible_constraints

import idaes.logger as idaeslog
from ahuora_builder.custom.custom_heat_exchanger import CustomHeatExchanger
from ahuora_builder.custom.updated_pressure_changer import Pump, Turbine
from ahuora_property_packages.helmholtz.helmholtz_builder import build_helmholtz_package
from idaes.core import FlowsheetBlock
from idaes.core.solvers import get_solver
from idaes.core.util.model_statistics import degrees_of_freedom
from idaes.models.unit_models import Mixer, MomentumMixingType
from idaes.core.util.model_diagnostics import DiagnosticsToolbox


TIME = 0


def build_geothermal_plant() -> pyo.ConcreteModel:
    """Build, connect, and specify the geothermal power-loop model."""
    model = pyo.ConcreteModel()
    model.fs = FlowsheetBlock(dynamic=False)
    setup_model(model)
    specify_model(model)
    return model


def setup_model(model: pyo.ConcreteModel) -> None:
    """Create property packages, unit operations, and process arcs."""
    fs = model.fs
    fs.butane = build_helmholtz_package(["n-butane"])
    fs.water = build_helmholtz_package(["water"])
    fs.pump = Pump(property_package=fs.butane)
    fs.turbine = Turbine(property_package=fs.butane)
    fs.recuperator = CustomHeatExchanger(
        hot_side_name="shell",
        cold_side_name="tube",
        shell={"property_package": fs.butane, "has_pressure_change": True},
        tube={"property_package": fs.butane, "has_pressure_change": True},
    )
    fs.preheater = CustomHeatExchanger(
        hot_side_name="shell",
        cold_side_name="tube",
        shell={"property_package": fs.water, "has_pressure_change": True},
        tube={"property_package": fs.butane, "has_pressure_change": True},
    )
    fs.vaporiser = CustomHeatExchanger(
        hot_side_name="shell",
        cold_side_name="tube",
        shell={"property_package": fs.water, "has_pressure_change": True},
        tube={"property_package": fs.butane, "has_pressure_change": True},
    )
    fs.condenser = CustomHeatExchanger(
        hot_side_name="shell",
        cold_side_name="tube",
        shell={"property_package": fs.butane, "has_pressure_change": True},
        tube={"property_package": fs.water, "has_pressure_change": True},
    )
    fs.water_mixer = Mixer(
        property_package=fs.water,
        inlet_list=["geothermal", "auxiliary"],
        momentum_mixing_type=MomentumMixingType.minimize,
    )
    fs.condenser_to_pump = Arc(source=fs.condenser.shell_outlet, destination=fs.pump.inlet)
    fs.pump_to_recuperator = Arc(source=fs.pump.outlet, destination=fs.recuperator.tube_inlet)
    fs.recuperator_to_preheater = Arc(source=fs.recuperator.tube_outlet, destination=fs.preheater.tube_inlet)
    fs.preheater_to_vaporiser = Arc(source=fs.preheater.tube_outlet, destination=fs.vaporiser.tube_inlet)
    fs.vaporiser_to_turbine = Arc(source=fs.vaporiser.tube_outlet, destination=fs.turbine.inlet)
    fs.turbine_to_recuperator = Arc(source=fs.turbine.outlet, destination=fs.recuperator.shell_inlet)
    fs.recuperator_to_condenser = Arc(source=fs.recuperator.shell_outlet, destination=fs.condenser.shell_inlet)
    fs.vaporiser_to_mixer = Arc(source=fs.vaporiser.shell_outlet, destination=fs.water_mixer.geothermal)
    fs.mixer_to_preheater = Arc(source=fs.water_mixer.outlet, destination=fs.preheater.shell_inlet)
    pyo.TransformationFactory("network.expand_arcs").apply_to(model)


def specify_model(model: pyo.ConcreteModel) -> None:
    """fix variables and set guesses"""
    fs = model.fs
    butane = fs.butane
    water = fs.water

    # The flow circulation rate required deactivating the flow equality constraint
    # to allow it to anchor the flow rate.
    # This is the only variable that needs to be fixed like this.
    fs.pump.inlet.pressure[TIME].set_value(100.0e5)
    fs.condenser_to_pump.expanded_block.flow_mol_equality.deactivate()
    fs.pump.inlet.flow_mol.fix(1.0)

    # This provides an example of fixing an inlet port conditions.
    fs.vaporiser.shell_inlet.flow_mol.fix(770.9510005)
    fs.vaporiser.shell_inlet.pressure.fix(23.0e5)
    fs.vaporiser.shell_inlet.enth_mol.fix(
        pyo.value(water.htpx(T=473.15 * pyo.units.K, p=23.0e5 * pyo.units.Pa)),
    )
    # This provides an example of fixing outlet temperature. Temperature is an expression in helmholtz
    # property packages so we have to get it as a variable to fix it.
    condenser_outlet_temperature = fs.condenser.shell.properties_out[TIME].get_as_var(
        fs.condenser.shell.properties_out[TIME].temperature
    )
    condenser_outlet_temperature.fix(274.970330261)

    # CONTINUE IMPLEMENTING HERE.






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
    fs.pump.report()
    fs.turbine.report()
    fs.recuperator.report()
    fs.preheater.report()
    fs.vaporiser.report()
    fs.condenser.report()



def initialise_model(model: pyo.ConcreteModel) -> None:
    """Initialize in sequential order."""
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
    """Build, initialize, and solve the geothermal power-loop model."""
    model = build_geothermal_plant() if model is None else model
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
