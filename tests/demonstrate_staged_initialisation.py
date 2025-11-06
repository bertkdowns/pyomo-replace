from idaes.models.unit_models import Turbine
import pyomo.environ as pyo
from idaes.core import FlowsheetBlock
from idaes.models.properties import iapws95
from idaes.core.util.exceptions import InitializationError
from idaes.core.util.model_statistics import degrees_of_freedom

def setup():
    m = pyo.ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    m.fs.pp = iapws95.Iapws95ParameterBlock()
    m.fs.turbine = Turbine(property_package=m.fs.pp)
    m.fs.turbine.inlet.flow_mol.fix(1000)
    m.fs.turbine.inlet.enth_mol.fix(m.fs.pp.htpx(p=1e6 * pyo.units.Pa,T=(273.15+200)*pyo.units.K))
    m.fs.turbine.inlet.pressure.fix(1e6)
    return m

# Functions to fix and unfix the guesses (similar to what the replacement initialisation method would do)

def fix_guesses(fs):
    fs.turbine.efficiency_isentropic.fix(0.5)
    fs.turbine.work_mechanical.fix(-5000)
    return

def unfix_guesses(fs):
    fs.turbine.efficiency_isentropic.unfix()
    fs.turbine.work_mechanical.unfix()
    return


# Functions to fix different combinations of variables

def fix_work(fs):
    fs.turbine.work_mechanical.fix(-5000000)
    return

def fix_efficiency(fs):
    fs.turbine.efficiency_isentropic.fix(0.8)

def fix_outlet_pressure(fs):
    fs.turbine.outlet.pressure.fix(1e5)
    return

def fix_ratioP(fs):
    fs.turbine.ratioP.fix(0.1)
    return



solver = pyo.SolverFactory("ipopt")


options = [(fix_work, fix_efficiency,"work_efficiency"),
           (fix_work, fix_outlet_pressure,"work_outlet_pressure"),
           (fix_efficiency, fix_outlet_pressure,"efficiency_outlet_pressure"),
           (fix_work, fix_ratioP,"work_ratioP"),
           (fix_efficiency, fix_ratioP,"efficiency_ratioP"),]

results = []

for option, option2,name in options:
    m = setup()
    fix_guesses(m.fs)
    unfix_guesses(m.fs)
    option(m.fs)
    option2(m.fs)
    try:
        m.fs.turbine.initialize()
    except InitializationError:
        results.append((name, "InitializationError"))
        continue
    assert degrees_of_freedom(m) == 0
    res = solver.solve(m, tee=False)
    if res.solver.termination_condition != pyo.TerminationCondition.optimal:
        results.append((name, "Solver Failed"))
    else:
        results.append((name, "Success"))




results_with_staged_init = []

for option, option2,name in options:
    m = setup()
    fix_guesses(m.fs)

    assert degrees_of_freedom(m) == 0

    try:
        m.fs.turbine.initialize()
    except InitializationError:
        results_with_staged_init.append((name, "InitializationError"))
        continue

    unfix_guesses(m.fs)

    option(m.fs)
    option2(m.fs)

    assert degrees_of_freedom(m) == 0


    res = solver.solve(m, tee=False)
    if res.solver.termination_condition != pyo.TerminationCondition.optimal:
        results_with_staged_init.append((name, "Solver Failed"))
    else:
        results_with_staged_init.append((name, "Success"))



print(results)
print(results_with_staged_init)
