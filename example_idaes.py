from model import *
import pyomo.environ as pyo
from unit_models.compressor import SVCompressor
from idaes.core import FlowsheetBlock
from idaes.models.properties import iapws95
from idaes.core.util.model_statistics import degrees_of_freedom


m = pyo.ConcreteModel()
m.fs = FlowsheetBlock(dynamic=False)
m.fs.pp = iapws95.Iapws95ParameterBlock()
m.fs.compressor = SVCompressor(property_package=m.fs.pp)
register_inlet_ports(m.fs)

pprint_replacements(m.fs)

replace_state_var(m.fs.compressor.ratioP, m.fs.compressor.outlet.pressure)
pprint_replacements(m.fs)


m.fs.compressor.inlet.flow_mol.fix(1)
m.fs.compressor.inlet.enth_mol.fix(3000)
m.fs.compressor.inlet.pressure.fix(1e5)
m.fs.compressor.efficiency_isentropic.fix(3500)
m.fs.compressor.outlet.pressure.fix(1.1e5)


print("degrees of freedom", degrees_of_freedom(m))

