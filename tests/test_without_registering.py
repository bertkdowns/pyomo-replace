from model import *
import pyomo.environ as pyo
from unit_models.heater import DutyHeater
from idaes.core import FlowsheetBlock
from idaes.models.properties import iapws95
from .test_single_operation import assert_replacement_works


def setup():
    """
    Setup a simple flowsheet with a single heater unit operation.
    Only difference is this uses the DutyHeater class which automatically registers
    the state variables.
    """
    m = pyo.ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    m.fs.pp = iapws95.Iapws95ParameterBlock()
    m.fs.h1 = DutyHeater(property_package=m.fs.pp, has_pressure_change=True)

    register_inlet_ports(m.fs)

    m.fs.h1.inlet.flow_mol.fix(1)
    m.fs.h1.inlet.enth_mol.fix(3000)
    m.fs.h1.inlet.pressure.fix(1e5)

    return m


def test_replacements():
    
    m = setup()
    
    assert_replacement_works(m)