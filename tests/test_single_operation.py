from model import *
import pyomo.environ as pyo
from idaes.models.unit_models import Heater
from idaes.core import FlowsheetBlock
from idaes.models.properties import iapws95



def setup():
    m = pyo.ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    m.fs.pp = iapws95.Iapws95ParameterBlock()
    m.fs.h1 = Heater(property_package=m.fs.pp, has_pressure_change=True)
    m.fs.h1.inlet.flow_mol.fix(1)
    m.fs.h1.inlet.enth_mol.fix(3000)
    m.fs.h1.inlet.pressure.fix(1e5)

    register_block(
        m.fs.h1,
        [
            m.fs.h1.inlet.flow_mol,
            m.fs.h1.inlet.enth_mol,
            m.fs.h1.inlet.pressure,
            m.fs.h1.heat_duty,
            m.fs.h1.deltaP,
        ],
    )
    return m


def test_replacements():
    m = setup()
    # Check initial state
    assert len(list_state_vars(m.fs)) == 5
    assert len(list_replacements(m.fs)) == 0
    assert len(list_guesses(m.fs)) == 0
    # should also be the same at the block level
    assert len(list_state_vars(m.fs.h1)) == 5
    assert len(list_replacements(m.fs.h1)) == 0
    assert len(list(list_guesses(m.fs.h1))) == 0

    assert len(list(list_available_vars(m.fs))) == 5

    # Replace one variable
    replace_state_var(m.fs.h1.heat_duty, m.fs.h1.outlet.enth_mol)
    assert len(list_state_vars(m.fs)) == 5
    assert len(list_replacements(m.fs)) == 1
    assert len(list_guesses(m.fs)) == 1
    assert list_guesses(m.fs)[0] is m.fs.h1.heat_duty
    assert len(list_fixed_state_vars(m.fs)) == 4 # one state var is now a guess
