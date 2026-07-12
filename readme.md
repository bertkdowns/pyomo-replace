# Pyomo Replace

Getting to zero degrees of freedom in a model can be time consuming, as you figure out how many degrees of freedom are avaliable and which variables you need to set.

This library presents a way of ensuring you always have a square model, using a few simple rules:

- All models must specify "Canonical Variables" by default that need to be fixed to turn the model into a square problem.
- If you want to fix a different variable, you must also specify which Canonical Variable it "replaces".

Draft paper: https://waikatouniversitynz-my.sharepoint.com/:b:/g/personal/bd65_students_waikato_ac_nz/IQD19XG8vU5lSaS02vq7ZDPxAWzb8WaVgXSaCUI5gEM5jms?e=Z0FyFL

# Example usage:

See [example_idaes.py](./example_idaes.py)

The default Canonical Variables for a heater are:

```
inlet.flow_mol
inlet.enth_mol
inlet.pressure

heat_duty
deltaP
```

In this example, heat duty is replaced with outlet enthalpy, and the inlet pressure is replaced with the outlet pressure.

This means heat duty is unfixed, and so is inlet pressure. These will be calculated from the outlet enthalpy and pressure instead.

```
$ uv run example_idaes.py

Replacements in block fs:
(Variable -> Replaced Canonical Variable)
  fs.h1._enth_mol_outlet_ref -> fs.h1.heat_duty
  fs.h1._pressure_outlet_ref -> fs.h1._pressure_inlet_ref

Unreplaced canonical variables in block fs:
  fs.h1._flow_mol_inlet_ref
  fs.h1._enth_mol_inlet_ref
  fs.h1.deltaP

```

# Reasoning

This approach is designed to keep the model square through the replacement workflow, reducing the manual burden of degree-of-freedom management.

The person that builds a model generally knows how many variables need to be fixed for the problem to become square. Specifying the list of Canonical Variables for a block (or unit operation) provides an implicit form of documentation on how the modeller expects it is most likely to be used.

Initialisation methods generally are designed to work from a certain set of fixed variables, usually the Canonical Variables. By thinking in terms of replacement, you can provide an initial guess for every Canonical Variable you replace. These guesses can then be used by the initialisation routine to estimate the remaining variables. This avoids writing a different initialisation method for every combination of fixed variables.

# TODO

- Add unit tests
- Add an example with multiple unit ops and arcs
- Expand descriptions
