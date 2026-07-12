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
            (m.fs.h1.inlet.flow_mol, "inlet"),
            (m.fs.h1.inlet.enth_mol, "inlet"),
            (m.fs.h1.inlet.pressure, "inlet"),
            (m.fs.h1.heat_duty, "operation"),
            (m.fs.h1.deltaP, "design"),
        ],
    )
    return m


def test_replacements():
    m = setup()
    assert_replacement_works(m)


def test_replacement_state_initialisation_context_restores_solve_mode():
    m = setup()
    replacement_state(m.fs).replace(m.fs.h1.heat_duty, m.fs.h1.outlet.enth_mol)
    outlet_enth_mol = next(iter(m.fs.h1.outlet.enth_mol.values()))

    outlet_enth_mol.set_value(4500)

    assert not is_fixed(m.fs.h1.heat_duty)
    assert outlet_enth_mol.fixed

    with replacement_state(m.fs).initialisation_context(m.fs.h1) as state:
        assert is_fixed(m.fs.h1.heat_duty)
        assert not outlet_enth_mol.fixed

        state.activate_local_replacements_for_initialisation(m.fs.h1)

        assert not is_fixed(m.fs.h1.heat_duty)
        assert outlet_enth_mol.fixed

    assert not is_fixed(m.fs.h1.heat_duty)
    assert outlet_enth_mol.fixed
    assert pyo.value(outlet_enth_mol) == 4500


def test_external_replacements_are_not_reactivated_for_block_initialisation():
    m = pyo.ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    m.fs.b1 = pyo.Block()
    m.fs.b2 = pyo.Block()
    m.fs.b1.canonical = pyo.Var(initialize=1)
    m.fs.b2.replacement = pyo.Var(initialize=2)

    m.fs.b1.canonical.unfix()
    m.fs.b2.replacement.fix()
    replacement_state(m.fs).append(m.fs.b1.canonical, m.fs.b2.replacement)

    with replacement_state(m.fs).initialisation_context(m.fs.b1) as state:
        assert m.fs.b1.canonical.fixed
        assert not m.fs.b2.replacement.fixed

        state.activate_local_replacements_for_initialisation(m.fs.b1)

        assert m.fs.b1.canonical.fixed
        assert not m.fs.b2.replacement.fixed

    assert not m.fs.b1.canonical.fixed
    assert m.fs.b2.replacement.fixed


def assert_replacement_works(m):
    # Check initial canonical variables
    assert len(all_canonical_vars(m.fs)) == 5
    assert len(replacement_state(m.fs).replacements_in(m.fs)) == 0
    assert len(replacement_state(m.fs).guesses_in(m.fs)) == 0
    # should also be the same at the block level
    assert len(all_canonical_vars(m.fs.h1)) == 5
    assert len(replacement_state(m.fs).replacements_in(m.fs.h1)) == 0
    assert len(replacement_state(m.fs).guesses_in(m.fs.h1)) == 0
    print([v.name for v in list_available_vars(m.fs)])

    assert len(list(list_available_vars(m.fs))) == 6 # for the 3 outlet conditions, and the 3 references to those outlet conditions

    # Replace one variable
    replacement_state(m.fs).replace(m.fs.h1.heat_duty, m.fs.h1.outlet.enth_mol)


    assert len(all_canonical_vars(m.fs)) == 5  # The number of canonical vars shouldn't change
    assert m.fs.h1.outlet.enth_mol not in all_canonical_vars(m.fs)
    assert m.fs.h1.heat_duty in all_canonical_vars(m.fs.h1)

    assert len(replacement_state(m.fs).replacements_in(m.fs)) == 1
    # Replacements returns tuples of (canonical_var, new_var)
    assert replacement_state(m.fs).replacements_in(m.fs)[0][1] is m.fs.h1.outlet.enth_mol
    assert replacement_state(m.fs).replacements_in(m.fs)[0][0] is m.fs.h1.heat_duty


    assert len(replacement_state(m.fs).guesses_in(m.fs)) == 1
    assert replacement_state(m.fs).guesses_in(m.fs)[0] is m.fs.h1.heat_duty

    assert m.fs.h1.heat_duty not in list_fixed_canonical_vars(m.fs.h1)
    assert len(list_fixed_canonical_vars(m.fs)) == 4 # one canonical var is now a guess
