from specifications import SpecificationState
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

    SpecificationState.for_flowsheet(m.fs)
    m.fs.specifications.register(
        [
            (m.fs.h1.inlet.flow_mol, "inlet"),
            (m.fs.h1.inlet.enth_mol, "inlet"),
            (m.fs.h1.inlet.pressure, "inlet"),
            (m.fs.h1.heat_duty, "operation"),
            (m.fs.h1.deltaP, "design"),
        ],
    )
    m.fs.specifications.validate(m.fs.h1)
    return m


def test_replacements():
    m = setup()
    assert_replacement_works(m)


def test_suspended_replacements_restore_solve_mode():
    m = setup()
    m.fs.specifications.replace(m.fs.h1.heat_duty, m.fs.h1.outlet.enth_mol)
    outlet_enth_mol = next(iter(m.fs.h1.outlet.enth_mol.values()))

    outlet_enth_mol.set_value(4500)

    assert not all(item.fixed for item in m.fs.h1.heat_duty.values())
    assert outlet_enth_mol.fixed

    with m.fs.specifications.replacements_suspended_in(m.fs.h1) as specifications:
        assert all(item.fixed for item in m.fs.h1.heat_duty.values())
        assert not outlet_enth_mol.fixed

        for replacement in specifications.internal_replacements_in(m.fs.h1):
            specifications.replace(
                replacement.canonical_variable,
                replacement.replacement_variable,
            )

        assert not all(item.fixed for item in m.fs.h1.heat_duty.values())
        assert outlet_enth_mol.fixed

    assert not all(item.fixed for item in m.fs.h1.heat_duty.values())
    assert outlet_enth_mol.fixed
    assert pyo.value(outlet_enth_mol) == 4500


def test_external_replacements_are_not_reactivated_for_block_initialisation():
    m = pyo.ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    m.fs.b1 = pyo.Block()
    m.fs.b2 = pyo.Block()
    m.fs.b1.canonical = pyo.Var(initialize=1)
    m.fs.b2.replacement = pyo.Var(initialize=2)

    SpecificationState.for_flowsheet(m.fs)
    m.fs.specifications.register([(m.fs.b1.canonical, "operation")])
    m.fs.specifications.replace(m.fs.b1.canonical, m.fs.b2.replacement)

    assert len(m.fs.specifications.external_replacements_in(m.fs.b1)) == 1
    assert len(m.fs.specifications.external_replacements_provided_by(m.fs.b2)) == 1

    with m.fs.specifications.external_replacements_suspended_in(m.fs.b2):
        assert m.fs.b1.canonical.fixed
        assert not m.fs.b2.replacement.fixed

    assert not m.fs.b1.canonical.fixed
    assert m.fs.b2.replacement.fixed

    with m.fs.specifications.replacements_suspended_in(m.fs.b1) as specifications:
        assert m.fs.b1.canonical.fixed
        assert not m.fs.b2.replacement.fixed

        for replacement in specifications.internal_replacements_in(m.fs.b1):
            specifications.replace(
                replacement.canonical_variable,
                replacement.replacement_variable,
            )

        assert m.fs.b1.canonical.fixed
        assert not m.fs.b2.replacement.fixed

    assert not m.fs.b1.canonical.fixed
    assert m.fs.b2.replacement.fixed


def assert_replacement_works(m):
    # Check initial canonical variables
    assert len(m.fs.specifications.canonical_variables_in(m.fs)) == 5
    assert len(m.fs.specifications.replacements_in(m.fs)) == 0
    assert len(m.fs.specifications.guesses_in(m.fs)) == 0
    # should also be the same at the block level
    assert len(m.fs.specifications.canonical_variables_in(m.fs.h1)) == 5
    assert len(m.fs.specifications.replacements_in(m.fs.h1)) == 0
    assert len(m.fs.specifications.guesses_in(m.fs.h1)) == 0
    print([v.name for v in m.fs.specifications.replacement_candidates_in(m.fs)])

    assert len(list(m.fs.specifications.replacement_candidates_in(m.fs))) == 6 # for the 3 outlet conditions, and the 3 references to those outlet conditions

    # Replace one variable
    m.fs.specifications.replace(m.fs.h1.heat_duty, m.fs.h1.outlet.enth_mol)


    assert len(m.fs.specifications.canonical_variables_in(m.fs)) == 5
    assert m.fs.h1.outlet.enth_mol not in m.fs.specifications.canonical_variables_in(m.fs)
    assert m.fs.h1.heat_duty in m.fs.specifications.canonical_variables_in(m.fs.h1)

    assert len(m.fs.specifications.replacements_in(m.fs)) == 1
    replacement = m.fs.specifications.replacements_in(m.fs)[0]
    assert replacement.replacement_variable is m.fs.h1.outlet.enth_mol
    assert replacement.canonical_variable is m.fs.h1.heat_duty
    assert replacement.category == "operation"


    assert len(m.fs.specifications.guesses_in(m.fs)) == 1
    assert m.fs.specifications.guesses_in(m.fs)[0] is m.fs.h1.heat_duty

    assert m.fs.h1.heat_duty not in m.fs.specifications.fixed_canonical_variables_in(m.fs.h1)
    assert len(m.fs.specifications.fixed_canonical_variables_in(m.fs)) == 4
