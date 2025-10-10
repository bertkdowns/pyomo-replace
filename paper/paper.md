---
title: Variable Replacement as a technique for Managing Complexity in large Equation-Oriented models
bibliography: refs.bib
---

# Introduction

Equation-oriented algebraic modelling is a powerful tool to represent certain types of physical systems, particularly those that closely follow first-principles behaviour and include non-linear dynamics. At its simplest, equation-oriented modelling is about specifying equations to represent the system and solving those equations to find the unknown properties. However, the use of numerical methods to solve the equations means that initial values to use when finding a solution, and scaling factors for variables, can be the difference between a model succeeding or failing to converge on a solution. This becomes more of a problem as the mathematical model grows larger. 

Pyomo is a framework for building mathematical models that is written in Python. It includes tools to manage abstraction and complexity in a mathematical model, and to define initialisation routines and scaling factors to enhance numerical stability. A particular feature is the ability to break a mathematical model into *blocks*, where blocks can be imported from different libraries. This encourages reuse, and empowers users to build more complex models, but it makes squaring a model, initialisation, and scaling more complicated. I propose that by defining a set of state variables to provide values or guesses for will simplify the process of squaring, initialising, and scaling a model. Our library, pyomo-replace, demonstrates the benefits of this approach in the Pyomo and IDAES ecosystem.

# Background on Mathematical Modelling

Fundamentally, a mathematical model is simply a set of mathematical equations, optionally with an objective function.

The main parts of these equations are:

- *Constants:* Fixed numbers that do not change.
- *Variables:* unknown values we solve the set of equations to find.
- *Constraints:* equality or inequality equations that are used to implicitly define the value, or solution space of, the variables. 
- An *Objective Function*: a function that is defined in terms of the variables, returns a value to minimise or maximise within the space of valid solutions. In square models an objective function is not required.

This is fundamentally all that is required in a mathematical model. However, pyomo also provides some additional modelling abstractions for easy programmatic creation and manipulation of models, borrowing from conventional software development data structures.

- Constants and Variables are represented as *Fixed Variables* and *Unfixed Variables* respectively. It is easy to change which variables are fixed and which are unfixed, so a model with the same structure can be used to solve for different variables. I.e either you can fix $x$ to calculate $y$, or you can fix $y$ to calculate $x$.
- Variables and Constraints can be indexed across a set. A variable or constraint is added for each item in the set. Sets are constant - you can't add or remove items during solving - but they provide a generalisation that makes it easy to scale up, down, or modify problems for slightly different cases.  
- Variables can be grouped into "Blocks". Blocks can also have sub-blocks inside them, making a tree data structure^[Variables and Blocks can be thought of like Files and Folders in a filesystem. Blocks only provide structure but no information, and can be nested inside each other, while variables contain the actual values in the model]. 

Blocks are of particular interest here. Similar to how a Class in object-oriented programming provides encapsulation of more complex functionality, Blocks are used to isolate the complex internal models of different parts of a system. For example, in a mathematical model of a chemical factory, a block may be used to model each individual unit operation (a pump, heater, tank, etc). The model inside the unit operation is isolated from the higher level model, which only cares about the properties of the fluid flowing in and out of the unit operation block. 

Pyomo also includes some even higher level modelling extensions:

- Pyomo.DAE allows defining Differential Algebraic Equations across "infinite" sets that are discretised, automatically creating the necessary constraints to define derivatives and integrals
- Pyomo.network allows you to represent your model as a graph: Blocks become nodes in the graph, and they can be connected to other nodes via edges called "arcs" that define equality constraints between variables. In many domains the graph view better represents the model structure. It also allows propogating initial values throughout a model. This is of particular importance as it allows sharing of information between distinct blocks.


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

The intuition behind variable replacement is similar. There are some variables that it is easy to think of as fully defining the system; we will call them "state variables". They are all linearly independent. All other variables can be defined in terms of these state variables^[This is analogus to the concept of a *critical set* in combinatorial design theory.]. In this example, the position of the accellerator pedal makes the most intuitive sense as the state variable, that is what you set to control the car's speed.

It follows by definition that if all state variables are fixed in a model, then the model will be fully defined, and have zero degrees of freedom. Fixing any other variable would cause the system to be over-defined. Thus, similar to in control theory, if you want to hold some other value constant, you need to also specify a state variable to "adjust". This is the fundamental principle behind variable replacement: start with all your state variables defined, and then if you want to set something else, you must choose a state variable to "replace", or unfix.

Starting with all the state variables fixed means you never have a under-defined model, and unfixing a state variable every time you fix something else means you never over-define your model. This makes it much clearer how your model is intended to be used. Initialisation and scaling methods also become much simpler if guesses are provided for all the state variables, as you only need to define one way to initialise/scale your model. 

# An example in IDAES.

To demonstrate, let us consider the example of a heater in IDAES using pyomo-replace.

First we must define the basic structure:

```
m = pyo.ConcreteModel()
m.fs = FlowsheetBlock(dynamic=False)
m.fs.pp = iapws95.Iapws95ParameterBlock()
m.fs.compressor = SVCompressor(property_package=m.fs.pp)
register_inlet_ports(m.fs)
pprint_replacements(m.fs)
```

This code is very similar to how a flowsheet is normally defined in IDAES. The only difference is in the last couple of lines:

- the `DutyHeater` class is an extension of the IDAES `Heater` class that defines the state variables that should be used by `pyomo-replace`.
- in most cases^[There are some exceptions, such as when both inlets are required to have the same pressure or temperature. However these are rare and there are other solutions to manage them.], the inlet ports need to be defined to fully specify the model. However, the inlet ports do not need to be defined if there is another model 'upstream' of the current model. register_inlet_ports registers the properties of all inlet ports that do not have another model upstream as state vars. This is all that is needed to fully define the model.
- pprint_replacements is a helper function that prints a list of all state variables, and any that are being replaced by other variables. It would print the following:

```
Unreplaced state variables:
  fs.compressor.deltaP
  fs.compressor.efficiency_isentropic
  fs.compressor.inlet.flow_mol
  fs.compressor.inlet.enth_mol
  fs.compressor.inlet.pressure
```

Replacing a variable is as simple as calling a function, passing the new variable to fix and the state variable to unfix:

```
  replace_state_var(m.fs.compressor.ratioP, m.fs.heater.outlet.pressure)
```

`pprint_replacements` would then show that `ratioP` has been replaced by `outlet.pressure`. 

```
Replaced state variables:
  fs.compressor.ratioP -> fs.h1.outlet.pressure

Unreplaced state variables in block fs:
  fs.compressor.efficiency_isentropic
  fs.compressor.inlet.flow_mol
  fs.compressor.inlet.enth_mol
  fs.compressor.inlet.pressure
```

You can then set a value for `outlet.pressure` and all the other state variables, and provide a guess for `ratioP`. This model will be square and can then be solved.


# Benefits

This method of replacing state variables to define your model does not fundamentally change the model itself, however it provides a number of practical benefits in terms of workflow and actually using mathematical modelling. It enforces a degree of regularity in the blocks that make up models, and in the overall structure. This increased predictability of behaviour leads to the following benefits.


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

The increased predictability and additional context required by defining the state variables in a model provides a natural form of documentation for a model.

Consider this snippet from the documentation of IDAES (slightly reworded for context):

> ``Compressor units have two degrees of freedom.
>
> Typical fixed variables are:

> - `outlet.pressure`, `ratioP` or `deltaP`,
> - `efficiency_isentropic`"

However, using the replace system, most of this information is already in the model The only extra piece of information is:

> "The state variable `ratioP` is often replaced by `outlet.pressure` or `deltaP`"


## Simplified Initialisation

Initial guesses greatly increase the robustness of solving equation-oriented models. Modelling toolboxes such as IDAES provide methods to automatically define initial guesses based on fixed variables. However, if you have fixed different variables to what the modelling library expects, these methods will not provide any benefit.

The concept of ``State Variables'' can simplify this process. The initialisation methods can be built to calculate initial values of all variables based on the initial values of the state variables. Only one initialisation method would be required, as long as initial guesses are provided for all the state variables. This standardises the initialisation process. 

## Simplified Scaling

In the same way as initialisation, calculating scaling factors depends on what values you already know. If initial scaling factors are provided for the state variables, it is much easier to calculate the other scaling factors. This standardises the scaling process. 


# Case Study: Ahuora Digital Twin Platform





