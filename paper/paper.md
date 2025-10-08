---
title: Variable Replacement as a technique for Managing Complexity in large Equation-Oriented models
bibliography: refs.bib
---

# Introduction

Equation-oriented algebraic modelling has become more widespread with the introduction of tools to build algebraic models in conventional programming languages such as python and Julia. Frameworks like Pyomo and JuMP allow for complex model specification, model transformations, and initialisation routines. This has allowed for much more complicated problems to be specified in a mathematical modelling language. However, larger problems are harder to reason about in conventional mathematical terms when the problem is too large to fit in one person's head; furthermore, users are increasingly coming from a non-mathematical background. A higher level of abstraction is needed to aid the scaling of algebraic modelling techniques.  


# Background on Mathematical Modelling

Fundamentally, a mathematical model is built from constants, variables, constraints, and (in the case of optimisation) an objective function.

- Constants are "Fixed" numbers that do not change.
- Variables are unknown values that are calculated to meet the constraints.
- Constraints (both equality and inequality constraints) are used to limit the space of valid solutions.
- An objective function is specified in terms of the variables, and returns a value to minimise or maximise within the space of valid solutions. If there is only a single valid solution, an objective function is not required.

However, nowadays mathematical models are constructed in terms of higher level objects. These reflect practical patterns in the use of mathematical modelling. The Python algebraic modelling framework Pyomo demonstrates many of these:

- Constants and Variables are represented as "Fixed" and "Unfixed" variables respectively. It is easy to change which variables are fixed and which are unfixed. This arose from the observation that often you are solving the same model for slightly different properties. For example, you might want to calculate Temperature from Pressure and Enthalpy, instead of calculating enthalpy from Pressure and Temperature.
- Variables and Constraints can be indexed across a set. A variable or constraint is added for each item in the set. Sets are constant (you can't add or remove items during solving), but it provides an easy way to scale up, down, or modify problems for slightly different cases.   
- Variables can be grouped into "Blocks". This provides a way of isolating tightly coupled constraints and encourages reuse of similar structures.

These components are then used in even higher level modelling extensions:

- Pyomo.DAE allows defining Differential Algebraic Equations across "infinite" sets that are discretised, automatically creating the necessary constraints to define derivatives and integrals
- Pyomo.network allows you to represent your model as a graph: Blocks become nodes in the graph, and they can be connected to other nodes via edges called "arcs" that define equality constraints between variables. In many domains the graph view better represents the model structure. It also allows propogating initial values throughout a model. 


# Current Challenges

## Squaring a model

These construction techniques make it possible to create libraries of pre-written blocks, containing all the constraints and variables to model a piece of a physical system. IDAES-PSE is a library built on top of Pyomo that creates blocks to represent chemical unit operations such as compressors, heaters, tanks, and many more. It uses pyomo.DAE to represent time as a continuous differentiable property, and Pyomo.network to represent the connections between unit operations. Because the constraints are abstracted, the user doesn't have to think too much about the mathematical modelling - instead it is a chemical simulation platform.

Invariably however, the user will come across the problem of Degrees of Freedom. In order to solve a set of equations exactly, a "square" model is required. This term is taken from linear algebra where a matrix must be square to be invertible, i.e have an exact solution. What it really means is that there must be the same number of equations (constraints) as there are unknowns (unfixed variables). Additionally, all the variables and equations must be linerarly independent. IDAES has methods to calculate the number of degrees of freedom, and if there are any over-defined or under-defined sets that make the model linearly dependent. Still, figuring out how many and which variables need to be "fixed" to make the model square can be a challenge. It becomes easier if the documentation of a block has defined exactly how many degrees of freedom it has, and which variables it expects to have fixed. 

## Initialisation & Scaling

In practice, Algebraic modelling problems are solved by initialising the unknown variables to a "best guess", and then performing an iterative search that gradually converges on the solution. In practice, this process does not always work, particularly when you are modelling non-convex systems and you start in the wrong region of convexity, or where your mathematical model is not designed for. Even if the algorithm is able to converge, it may take significantly longer than if you had started with a good initial guess. 

To help with this process, IDAES includes methods to initialise a model before solving. This involves solving part of a model, or using a simpler model to estimate what the true solution might be. However, these methods are often built around the assumption that you have fixed certain variables - if you are instead solving for those variables, the initialisation method is unlikely to work as well. 

Scaling works in a similar manner. In order for mathematical solvers to find accurate solutions, variables need to be scaled so that they are all approximately the same magnitude. The amount that these variables need to be scaled by is called the *scaling factor*, and it is usually some order of magnitude. IDAES includes methods to calculate the scaling factors of all variables, once you have provided the scaling factor of a few key variables. 

# An alternative intuition: Variable Replacement

In the physical world, the concept of "degrees of freedom" is not well defined. Everything is always "fully specified" whether intentionally or unintentionally as a part of the environment. The closest thing to "fixing" a property, or holding a property constant, is control theory. Let us consider a very simple model of a car's velocity:

$$
v = kx
$$

That is, the velocity $v$ of a car on flat ground is equal to some performance constant $k$ multiplied by the amount the accellerator pedal is depressed, $x$. If the accellerator is depressed further, the velocity of the car will increase. This can easily be modelled in an Algebraic Modelling language, with either the velocity of the accelleration fixed to fully define the system. In the physical world, the velocity of the car cannot be set; the only thing that can really be set is the position of the accellerator pedal. However, control theory allows you to instead hold $v$ constant, calculating the appropriate value of $x$ for that to be the case. 

The intuition behind variable replacement is similar: there are some variables that it is easy to think of as fully defining the system, we will call them "state variables". They are all linearly independent. All other variables can be defined in terms of these state variables. In this example, the position of the accellerator pedal makes the most intuitive sense as the state variable, as it fully defines the system.

It follows by definition that if all state variables are fixed in a model, then the model will be fully defined, and have zero degrees of freedom. Fixing any other variable would cause the system to be over-defined. Thus, similar to in control theory, if you want to hold some other value constant, you need to also specify a state variable to "adjust". This is the fundamental principle behind variable replacement: start with all your state variables defined, and then if you want to set something else, you must choose a state variable to "replace", or unfix.

# An example in IDAES.

Let us consider the example of a heater in IDAES.


First let us define the model in IDAES:

```
m = pyo.ConcreteModel()
m.fs = FlowsheetBlock(dynamic=False)
m.fs.pp = iapws95.Iapws95ParameterBlock()
m.fs.h1 = DutyHeater(property_package=m.fs.pp, has_pressure_change=True)
register_inlet_ports(m.fs)
pprint_replacements(m.fs)
```

This would pretty-print the state of the model, with no variables replaced:

```
Unreplaced state variables:
  fs.h1.heat_duty
  fs.h1.deltaP
  fs.h1.inlet.flow_mol
  fs.h1.inlet.temperature
  fs.h1.inlet.pressure
```

Replacing a variable is as simple as calling a function, passing the new variable to fix and the state variable to unfix:

```
replace_state_var(m.fs.h1.heat_duty, m.fs.h1.outlet.temperature)
```

`pprint_replacements` would then show that `heat_duty` has been replaced by the outlet temperature. 

```
Replaced state variables:
  fs.h1.heat_duty -> fs.h1.outlet.temperature

Unreplaced state variables in block fs:
  fs.h1.deltaP
  fs.h1.inlet.flow_mol
  fs.h1.inlet.temperature
  fs.h1.inlet.pressure
```



# Benefits

This method of replacing state variables to define your model does not fundamentally change the model itself, however it provides a number of practical benefits in terms of workflow and actually using mathematical modelling.

1. It fundamentally removes the problem of Degrees of Freedom when defining a model.
2. It provides a form of self-documentation for the system.
3. It simplifies the problem of initialisation.
4. It provides a standardised basis for calculating scaling factors.


## Removing the problem of Degrees of Freedom

To have a square model, you must have the same number of unknowns, or unfixed variables, as equations. A model that has more unknowns than constraints is said to have $n$ degrees of freedom, where $n_{\text{degrees\ of\ freedom}}$ is given by

$$
n_{\text{degrees\ of\ freedom}} =  n_{\text{variables}} - n_{\text{constraints}}
$$

Model libraries such as IDAES provide the equations, and then all that is required is to specify enough variables that the number of variables equals the number of unknowns. This can be done by repeatedly fixing variables in a part of a model that is not already over-defined^[i.e you must fix variables that are part a dulmage-mendelson underconstrained set.], until the model is fully defined.

Alternatively, if a set of state variables are already defined by the model library, the problem is already fully defined and there are zero degrees of freedom *by definition*. If a problem requires a variable to be fixed that is not a state variable, an appropriate^[i.e a state variable that would be part of the dulmage-mendelson overconstrained set if the other variable was fixed and nothing was unfixed] state variable must be unfixed too. 

## Self-Documentation

Consider this snippet from the documentation of the IDAES model library:


``Pressure Changer units generally have one or more degrees of freedom, depending on the thermodynamic assumption used.

Typical fixed variables are:

- outlet pressure, $P_{ratio}$ or $\Delta P$,
- unit efficiency (isentropic or pump assumption)."

By defining a set of state variables, for example outlet pressure and unit efficiency, most of this documentation is encoded in the model definition itself. The documentation could be simplified to:

`` There are one or two state variables, depending on the thermodynamic assumption used.

These are:

- outlet pressure, which may be replaced by $P_{ratio}$ or $\Delta P$,
- unit efficiency (isentropic or pump assumption)."

As the state vars are intrinsic the model, the only real piece of documentation that is required is:

``Outlet pressure may be replaced by $P_{ratio}$ or $\Delta P$''

## Simplified Initialisation

Initial guesses greatly increase the robustness of solving equation-oriented models. Modelling toolboxes such as IDAES provide methods to automatically define initial guesses based on fixed variables. However, if you have fixed different variables to what the modelling library expects, these methods will not provide any benefit.

The concept of ``State Variables'' can simplify this process. The initialisation methods can be built to calculate initial values of all variables based on the initial values of the state variables. Only one initialisation method would be required, as long as initial guesses are provided for all the state variables. This standardises the initialisation process. 

## Simplified Scaling

In the same way as initialisation, calculating scaling factors depends on what values you already know. If initial scaling factors are provided for the state variables, it is much easier to calculate the other scaling factors. This standardises the scaling process. 






