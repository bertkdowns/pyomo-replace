from model import *
import pyomo.environ as pyo
from unit_models.heater import DutyHeater
from idaes.core import FlowsheetBlock
from idaes.models.properties import iapws95


m = pyo.ConcreteModel()
m.fs = FlowsheetBlock(dynamic=False)
m.fs.pp = iapws95.Iapws95ParameterBlock()
m.fs.h1 = DutyHeater(property_package=m.fs.pp, has_pressure_change=True)
register_inlet_ports(m.fs)

pprint_replacements(m.fs)


replace_state_var(m.fs.h1.heat_duty, m.fs.h1.outlet.enth_mol)
replace_state_var(m.fs.h1.inlet.pressure, m.fs.h1.outlet.pressure)
pprint_replacements(m.fs)


m.fs.h1.inlet.flow_mol.fix(1)
m.fs.h1.inlet.enth_mol.fix(3000)
m.fs.h1.inlet.pressure.fix(1e5)
m.fs.h1.outlet.enth_mol.fix(3500)
m.fs.h1.outlet.pressure.fix(1.1e5)

