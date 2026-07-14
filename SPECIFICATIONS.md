# Specifications

`specifications.py` contains the flowsheet-owned `SpecificationState` module.
It is the authoritative place for Canonical Variable registrations and active
Replacements:

```python
specifications = SpecificationState.for_flowsheet(m.fs)
specifications.register([(m.fs.heater.heat_duty, "operation")])
specifications.replace(m.fs.heater.heat_duty, m.fs.heater.outlet.enth_mol)
```

After assembly, callers use `m.fs.specifications`. No child block stores its
own Canonical Variable or Replacement state.

## Intent

The module keeps the rules for a Specification in one place:

- registration fixes newly declared Canonical Variables
- an active Replacement unfixes its Canonical Variable and fixes its replacement variable
- `Replacement` is an immutable value containing both variables and the captured Specification Category
- validation checks degrees of freedom for an explicitly chosen block
- queries describe Canonical Variables, Replacement Candidates, and Internal or External Replacements relative to a block

This gives flowsheet-wide Replacements a single owner while retaining block-scoped queries. In particular, sibling blocks can participate in an External Replacement without either child block becoming the authoritative owner.

## Temporary State

`replacements_suspended_in(block)` and
`external_replacements_suspended_in(block)` are reversible Specification
transitions. They temporarily restore Canonical Variables as active
Specifications, then restore the flowsheet solve state when the context exits.
They do not know about initialisation; `initialisation.py` chooses when to use
them.

## Public Interface

The public names exported by `specifications.py` are:

- `SpecificationState`
- `Replacement`

The public state interface is `flowsheet.specifications`. Helpers and stored
collections remain private implementation details.
