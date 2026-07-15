"""Steady-state geothermal-heated n-butane power-loop flowsheet."""

from __future__ import annotations

import pyomo.environ as pyo
from pyomo.network import Arc, SequentialDecomposition
from pyomo.util.infeasible import log_infeasible_bounds, log_infeasible_constraints

import idaes.logger as idaeslog
from ahuora_builder.custom.custom_heat_exchanger import CustomHeatExchanger
from ahuora_builder.custom.updated_pressure_changer import Pump, Turbine
from ahuora_builder.replacement.specifications import SpecificationState
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
    specs = SpecificationState.for_flowsheet(fs)
    specs.declare_inlet_port(fs.water_mixer.auxiliary)
    specs.register_unconnected_inlets()


def specify_model(model: pyo.ConcreteModel) -> None:
    """Set specifications and guesses, then activate all replacement targets."""
    fs = model.fs
    specs = SpecificationState.for_flowsheet(fs)
    butane = fs.butane
    water = fs.water

    # The circulation rate is the sole recycle specification without a unit owner.
    # This is the only variable that needs to be fixed like this.
    fs.pump.inlet.pressure[TIME].set_value(100.0e5)
    specs.anchor_loop_variable(fs.pump.inlet.flow_mol)
    specs.fix(fs.pump.inlet.flow_mol, 1.0)

    # This provides an example of fixing an inlet port conditions.
    # These variables can be fixed using specs.fix() as they are canonical variables.
    # The list of canonical variables is shown in debug_model() output.
    specs.fix(fs.vaporiser.shell_inlet.flow_mol, 770.9510005)
    specs.fix(fs.vaporiser.shell_inlet.pressure, 23.0e5)
    specs.fix(
        fs.vaporiser.shell_inlet.enth_mol,
        pyo.value(water.htpx(T=473.15 * pyo.units.K, p=23.0e5 * pyo.units.Pa)),
    )
    # This provides an example of replacing a canonical variable with a non-canonical variable,
    # specifying the condenser outlet temperature instead of the overall heat transfer coefficient.
    condenser_outlet_temperature = fs.condenser.shell.properties_out[TIME].get_as_var(
        fs.condenser.shell.properties_out[TIME].temperature
    )
    specs.replace(fs.condenser.overall_heat_transfer_coefficient, condenser_outlet_temperature)
    specs.fix(condenser_outlet_temperature, 274.970330261)
    print("Initial Specification State:")
    specs.report(fs)

    # CONTINUE IMPLEMENTING HERE.
    specs.replace(fs.pump.work_mechanical, fs.pump.outlet.pressure)
    specs.fix(fs.pump.outlet.pressure, 23.0e5)
    specs.fix(fs.pump.efficiency_pump, 0.7)

    specs.replace(fs.turbine.work_mechanical, fs.turbine.outlet.pressure)
    specs.fix(fs.turbine.outlet.pressure, 100.0e5)
    specs.fix(fs.turbine.efficiency_isentropic, 0.5)

    recuperator_cold_outlet_temperature = fs.recuperator.tube.properties_out[TIME].get_as_var(
        fs.recuperator.tube.properties_out[TIME].temperature
    )
    specs.replace(fs.recuperator.overall_heat_transfer_coefficient, recuperator_cold_outlet_temperature)
    specs.fix(recuperator_cold_outlet_temperature, 333.15)
    specs.fix(fs.recuperator.area, 1.0)
    specs.fix(fs.recuperator.hot_side.deltaP, 0.0)
    specs.fix(fs.recuperator.cold_side.deltaP, 0.0)

    preheater_cold_outlet_temperature = fs.preheater.tube.properties_out[TIME].get_as_var(
        fs.preheater.tube.properties_out[TIME].temperature
    )
    specs.replace(fs.preheater.overall_heat_transfer_coefficient, preheater_cold_outlet_temperature)
    specs.fix(preheater_cold_outlet_temperature, 353.15)
    specs.fix(fs.preheater.area, 5.0)
    specs.fix(fs.preheater.hot_side.deltaP, 0.0)
    specs.fix(fs.preheater.cold_side.deltaP, 0.0)

    vaporiser_cold_outlet_temperature = fs.vaporiser.tube.properties_out[TIME].get_as_var(
        fs.vaporiser.tube.properties_out[TIME].temperature
    )
    specs.replace(fs.vaporiser.overall_heat_transfer_coefficient, vaporiser_cold_outlet_temperature)
    specs.fix(vaporiser_cold_outlet_temperature, 423.15)
    specs.fix(fs.vaporiser.area, 5.0)
    specs.fix(fs.vaporiser.hot_side.deltaP, 0.0)
    specs.fix(fs.vaporiser.cold_side.deltaP, 0.0)

    specs.fix(fs.condenser.area, 5.0)
    specs.fix(fs.condenser.hot_side.deltaP, 0.0)
    specs.fix(fs.condenser.cold_side.deltaP, 0.0)
    specs.fix(fs.condenser.tube_inlet.flow_mol, 800.0)
    specs.fix(fs.condenser.tube_inlet.pressure, 100.0e3)
    specs.fix(
        fs.condenser.tube_inlet.enth_mol,
        pyo.value(water.htpx(T=274.15 * pyo.units.K, p=100.0e3 * pyo.units.Pa)),
    )

    specs.replace(fs.water_mixer.auxiliary.flow_mol, fs.preheater.shell_outlet.flow_mol)
    specs.fix(fs.preheater.shell_outlet.flow_mol, 925.1412006)
    specs.fix(fs.water_mixer.auxiliary.pressure, 150.0e3)
    specs.fix(
        fs.water_mixer.auxiliary.enth_mol,
        pyo.value(water.htpx(T=368.15 * pyo.units.K, p=150.0e3 * pyo.units.Pa)),
    )
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
    fs.pump.report()
    fs.turbine.report()
    fs.recuperator.report()
    fs.preheater.report()
    fs.vaporiser.report()
    fs.condenser.report()
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
