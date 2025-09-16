# Pyomo Replace

Getting to zero degrees of freedom in a model can be time consuming, as you figure out how many degrees of freedom are avaliable and which variables you need to set.

This library presents a way of ensuring you always have a square model, using a few simple rules:

- Specify "State Variables" by default that need to be fixed to turn the model into a square problem.
- If you want to fix a different variable, you must also specify which state variable it "replaces".





# Example usage:

See [example_idaes.py](./example_idaes.py)

The default state variables for a heater are:

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
$ python example_idaes.py

Replacements in block fs:
  fs.h1.heat_duty -> fs.h1._enth_mol_outlet_ref
  fs.h1._pressure_inlet_ref -> fs.h1._pressure_outlet_ref

Unreplaced state variables in block fs:
  fs.h1._flow_mol_inlet_ref
  fs.h1._enth_mol_inlet_ref
  fs.h1.deltaP

```