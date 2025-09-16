from model import *
import pyomo.environ as pyo
from idaes.models.unit_models import Heater
from idaes.core import FlowsheetBlock
from idaes.models.properties import iapws95
from idaes.models.unit_models import HeatExchanger1D
from pyomo.environ import units


m = pyo.ConcreteModel()
m.fs = FlowsheetBlock(dynamic=False)
m.fs.pp = iapws95.Iapws95ParameterBlock()
m.fs.hx = HeatExchanger1D(
    hot_side={
        "property_package":m.fs.pp,
        "transformation_method":'dae.collocation',
        "transformation_scheme": "LAGRANGE-RADAU",
    },
    cold_side={
        "property_package":m.fs.pp,
        "transformation_method":'dae.collocation',
        "transformation_scheme": "LAGRANGE-RADAU",
    },
    finite_elements=20,
    collocation_points=3,
    flow_type="countercurrent",
)


m.fs.hx.hot_side_inlet.flow_mol.fix(10)
m.fs.hx.hot_side_inlet.enth_mol.fix(m.fs.pp.htpx(T=(120+273.15) * units.K, p=1e6 * units.Pa))
m.fs.hx.hot_side_inlet.pressure.fix(1e6) # 10 bar

m.fs.hx.cold_side_inlet.flow_mol.fix(30)
m.fs.hx.cold_side_inlet.enth_mol.fix(m.fs.pp.htpx(T=(20+273.15) * units.K, p=1e5 * units.Pa))
m.fs.hx.cold_side_inlet.pressure.fix(1e5) # 1 bar

m.fs.hx.area.fix(5) # m^2
m.fs.hx.length.fix(1)
# m.fs.hx.heat_transfer_coefficient.fix(50) # W/m^2-K
# m.fs.hx.heat_transfer_coefficient[0,0.5].fix(500)
# Add a variable for overall heat transfer coefficient
m.fs.hx.overall_heat_transfer_coefficient = pyo.Var(m.fs.hx.flowsheet().time, initialize=500, bounds=(1, 1e4), units=units.W/units.m**2/units.K)

@m.fs.hx.Constraint(m.fs.hx.flowsheet().time,m.fs.hx.hot_side.length_domain )
def overall_heat_transfer_coefficient_def(b, t, x):
    return b.overall_heat_transfer_coefficient[t] == b.heat_transfer_coefficient[t,x]


m.fs.hx.initialize()

solver = pyo.SolverFactory('ipopt')
solver.solve(m, tee=True)

for t in m.fs.hx.cold_side.properties.values():
    print(pyo.value(t.temperature))

# Draw a plot
import matplotlib.pyplot as plt
x = [pyo.value(m.fs.hx.cold_side.length * (i) / 20) for i in range(21)]
y1 = [pyo.value(m.fs.hx.cold_side.properties[0,i/20].temperature - 273.15) for i in range(21)]
y2 = [pyo.value(m.fs.hx.hot_side.properties[0,i/20].temperature - 273.15) for i in range(21)]
plt.plot(x, y1, label='Cold side')
plt.plot(x, y2, label='Hot side')
plt.xlabel('Length (m)')
plt.ylabel('Temperature (C)')
plt.legend()
plt.show()