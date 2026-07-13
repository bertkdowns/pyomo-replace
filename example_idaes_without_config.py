from model import *
import pyomo.environ as pyo
from idaes.models.unit_models import Heater
from idaes.core import FlowsheetBlock
from idaes.models.properties import iapws95


m = pyo.ConcreteModel()
m.fs = FlowsheetBlock(dynamic=False)
m.fs.pp = iapws95.Iapws95ParameterBlock()
m.fs.h1 = Heater(property_package=m.fs.pp, has_pressure_change=True)
m.fs.h1.inlet.flow_mol.fix(1)
m.fs.h1.inlet.enth_mol.fix(3000)
m.fs.h1.inlet.pressure.fix(1e5)

SpecificationState.for_flowsheet(m.fs)
m.fs.specifications.register(
    [
        (m.fs.h1.inlet.flow_mol, "operation"),
        (m.fs.h1.inlet.enth_mol, "operation"),
        (m.fs.h1.inlet.pressure, "operation"),
        (m.fs.h1.heat_duty, "operation"),
        (m.fs.h1.deltaP, "design"),
    ],
)

m.fs.specifications.replace(m.fs.h1.heat_duty, m.fs.h1.outlet.enth_mol)
m.fs.specifications.replace(m.fs.h1.inlet.pressure, m.fs.h1.outlet.pressure)


print(m.fs.specifications.replacements_in(m.fs))
