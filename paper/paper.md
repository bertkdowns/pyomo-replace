---
title: Variable Replacement as a technique for Managing Complexity in large Equation-Oriented models
bibliography: refs.bib
---

# Introduction

Equation-oriented algebraic modelling is a powerful tool to represent certain types of physical systems, particularly those that closely follow first-principles behaviour and include non-linear dynamics [@shacham1982equation]. At its simplest, equation-oriented modelling is about specifying equations to represent the system and solving those equations to find the unknown properties. However, the use of numerical methods to solve the equations means that initial values to use when finding a solution, and scaling factors for variables, can be the difference between a model succeeding or failing to converge on a solution. This becomes more of a problem as the mathematical model grows larger. 

Pyomo [@hart2011pyomo] is a framework for building mathematical models that is written in Python. It includes tools to manage abstraction and complexity in a mathematical model, and to define initialisation routines and scaling factors to enhance numerical stability. A particular feature is the ability to break a mathematical model into *blocks*, where blocks can be imported from different libraries. This encourages reuse, and empowers users to build more complex models, but it makes squaring a model, initialisation, and scaling more complicated. This article proposes that defining a set of state variables to provide values or guesses for will simplify the process of squaring, initialising, and scaling a model. Our library, pyomo-replace, demonstrates the benefits of this approach in the Pyomo and IDAES [@miller2018next] ecosystem.

# Background on Equation-Oriented Modelling

Fundamentally, an Equation-Oriented Model is simply a set of mathematical equations, optionally with an objective function [@biegler2010nonlinear].

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

- Pyomo.DAE [@nicholson2018pyomo] allows defining Differential Algebraic Equations across "infinite" sets that are discretised, automatically creating the necessary constraints to define derivatives and integrals
- Pyomo.network [@bynum2021pyomo] allows you to represent your model as a graph: Blocks become nodes in the graph, and they can be connected to other nodes via edges called "arcs" that define equality constraints between variables. In many domains the graph view better represents the model structure. It also allows propogating initial values throughout a model. This is of particular importance as it allows sharing of information between distinct blocks.


# Current Difficulties in Equation Oriented Modelling

## Squaring a model

Pyomo's construction techniques make it possible to create libraries of pre-written blocks, containing all the constraints and variables to model a piece of a physical system [@dowling2015framework]. IDAES-PSE [@miller2018next] is a library built on top of Pyomo that creates blocks to represent chemical unit operations such as compressors, heaters, tanks, and many more. It uses pyomo.DAE to represent time as a continuous differentiable property, and Pyomo.network to represent the connections between unit operations. Because the constraints are abstracted, the user doesn't have to think too much about the mathematical modelling - instead it is a chemical simulation platform.

Invariably however, the user will come across the problem of Degrees of Freedom. In order to solve a set of equations exactly, a "square" model is required. This term is taken from linear algebra where a matrix must be square to be invertible, i.e have an exact solution. What it really means is that there must be the same number of equations (constraints) as there are unknowns (unfixed variables). Additionally, all the variables and equations must be linerarly independent. 

IDAES has methods to calculate the number of degrees of freedom, and if there are any over-defined or under-defined sets that make the model linearly dependent [@lee2024model]. Still, figuring out how many and which variables need to be "fixed" to make the model square can be a challenge. It becomes easier if the documentation of a block has defined exactly how many degrees of freedom it has, and which variables it expects to have fixed. 

## Initialisation & Scaling

In practice, Algebraic modelling problems are solved by initialising the unknown variables to a "best guess", and then performing an iterative search that gradually converges on the solution. In practice, this process does not always work, particularly when you are modelling non-convex systems and you start in the wrong region of convexity, or outside of the region your model was designed for [@casella2008beyond]. Even if the algorithm is able to converge, it may take significantly longer than if you had started with a good initial guess. 

To help with this process, IDAES includes methods to initialise a model before solving. This involves solving part of a model, or using a simpler model to estimate what the true solution might be. However, these methods are often built around the assumption that you have fixed certain variables - if you are instead solving for those variables, the initialisation method is unlikely to work as well. 

Scaling works in a similar manner. In order for mathematical solvers to find accurate solutions, variables need to be scaled so that they are all approximately the same magnitude. The amount that these variables need to be scaled by is called the *scaling factor*, and it is usually some order of magnitude. IDAES includes methods to calculate the scaling factors of all variables, once you have provided the scaling factor of a few key variables. 

# Related Work

The field of static structural analysis has helped to solve some of the problems of squaring a model. In [@bunus2001debugging], a method is proposed to help debug when a model is singular, by using Dulmage-Mendelson Decomposition to identify sets of constraints that are over-constrained or under-constrained. These methods are commonly used in frameworks such as IDAES to help ensure a square model is valid [@lee2024model]. However, while these techniques are applicable to an entire "flat" system of equations, it is hard to apply them to an individual block without understanding of what external constraints are applied. Some preliminary work has been conducted to show that in some cases issues can be identified in this level [@nilsson2008type], but it is limited in its ability to detect errors and does not appear to have much uptake in systems such as Pyomo.

As initialisation and scaling are also common problems across equation-oriented modelling tools, a number of approaches have been considered to help overcome the numeric issues that arise during solving. Simple strategies include initialising at random points, initialising at zero, initialising at a previously solved location, or solving a simpler model first [@lawrynczuk2022initialisation]. IDAES models generally take the latter approach, initialising parts of the model at a time, removing some of the more complex constraints or solving a relaxed problem first. Pyomo Network includes methods to run sequential decomposition, which initialises every block in order once any blocks it depends on have been initialised [@pyomo_network_doc].

Scaling is mostly a concern when variables have wildly different orders of magnitude. For example, when power is measured in order of $10^9$ $J$ but valve cross sectional areas are measured in the order of $10^{-2}$ $m^2$, the difference can quickly approach the precision of a floating-point number [@casella2017importance]. To remedy this, variables need to be scaled to similar orders of magnitude. Pyomo provides preprocessing tools for this. Often many variables require similar scaling factors based on the model definition, and so libraries such as IDAES provide tools to automatically propogate scaling factors across variables, after a few initial scaling factors are added [@idaes_scaling_doc]. However, the scaling factors the modeller needs to provide depend on the implementation of the model, and may be different to the variables that are fixed or the guesses that are required for initialisation.

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
- in most cases^[There are some exceptions, such as when both inlets are required to have the same pressure or temperature. However these are rare and there are other solutions to manage them, such as treating these inlets as outlets instead.], the inlet ports need to be defined to fully specify the model. However, the inlet ports do not need to be defined if there is another model 'upstream' of the current model. register_inlet_ports registers the properties of all inlet ports that do not have another model upstream as state vars. This is all that is needed to fully define the model.
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

Model libraries such as IDAES provide the equations, and then all that is required is to specify enough variables that the number of variables equals the number of unknowns. This can be done by repeatedly fixing variables in a part of a model that is not already over-defined^[i.e You must fix variables that are part a Dulmage-Mendelson underconstrained set.], until the model is fully defined.

Alternatively, if a set of state variables are already defined by the model library, the problem is already fully defined and there are zero degrees of freedom *by definition*. If a problem requires a variable to be fixed that is not a state variable, an appropriate^[i.e A state variable that would be part of the Dulmage-Mendelson overconstrained set if the other variable was fixed and nothing was unfixed] state variable must be unfixed too. 

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

Initial guesses greatly increase the robustness of solving equation-oriented models. Modelling toolboxes such as IDAES provide methods to automatically define initial guesses based on fixed variables. However, if different variables are fixed to the ones the modelling library expects, these methods will not provide any benefit, and may even cause additional problems.

![Alternative initialisation routine, making use of state variables to avoid the need for different initialisation methods.](assets/initialisation-methods.drawio.png)


The concept of "State Variables" can simplify this process, by splitting the initialisation into two parts. First, the initialisation methods can calculate initial values of all variables based on the initial values (or guesses) of the state variables. Then, once the model has been initialised in a sensible location, any state variables that are replaced can be unfixed, and the variables that are replacing them can be fixed back to their original values. The block can then be re-solved to calculate the correct value of any "guessed" state variable.

This limits the logic in initialisation routines, as only one initialisation method is required be required. It does require that initial guesses are provided for all the state variables, but this is a reasonable tradeoff. This standardises the initialisation process to work across all sets of fixed variables, while still giving the model library developer freedom to develop whatever initialisation method they think is best.

## Simplified Scaling

In the same way as initialisation, calculating scaling factors depends on what values you already know. If initial scaling factors are provided for the state variables, it is much easier to calculate the other scaling factors. This standardises the scaling process. 


# Case Study: Ahuora Digital Twin Platform

The Ahuora Digital Twin Platform is a web-based process simulation environment. It is built using IDAES and Pyomo as the equation-oriented modelling libraries. 

A user interface creates additional challenges when fully defining models, because users can add or remove unit operations at any time. This leads to unpredictable behaviour when a degrees of freedom approach is used. For example, when a unit operation is removed from the flowsheet, it might cause the model to be over specified. Which variables should be unfixed?

Instead, we have opted for a state-variables based approach to setting all the degrees of freedom. This means that users never have to worry about making sure they have zero degrees of freedom in their model, as their model always has zero degrees of freedom no matter what they do. If a different value is chosen, an appropriate state variable has to be chosen and "replaced". In the example image, the "Heat Added" variable in the evaporator is being replaced by the Temperature at the outlet stream. An initial value for "Heat Added" is entered, which is updated to the correct value when the model solves. In contrast, the "Pressure Drop" variable is fixed at 0 kPa.

![Heat Pump with in the Ahuora Platform, demonstrating variable replacement.](assets/ahuora-replacement.png)

This provides a sensible way to deal with adding or removing unit operations. When a unit operation is added, it's state variables and inlet ports are fixed by default to ensure the degrees of freedom are still zero. When a unit operation is removed, anything that is replacing it's state variables is also unfixed, and any inlet ports that were previously connected to the outlet of the unit operation are fixed, again keeping the degrees of freedom at zero. 

The GUI also does not provide any way to write custom initialisation routines, so it is imperative that generic initialisation routines are used that will support any use case. The replace logic helps with this too - as long as guesses are specified for the state variables, these can be used in the initialisation routine. This enables us to specify any set of variables to define the conditions of an inlet stream, wheras IDAES is typically limited to only a certain set of properties.

After the model has been initialised once, previous solves can also be used for initialisation. While scaling methods have not been built into the Ahuora Digital Twin Platform at this time, they also be based off the state variables, so as long as the scaling factors of the state variables are set appropriately, the whole model will be scaled appropriately.

# Conclusion

Variable replacemnt provides an alternative way of maintaining a square model in an equation oriented framework, particularly when scaling up to larger equation oriented models. If state variables are defined on each block added to a model, it becomes simpler to build initialisation and scaling methods around them, and to reason about the degrees of freedom. The Ahuora Ditial Twin Platform provides a case study on how this is beneficial, particularly so in a GUI tool. These techniques could be used to standardise the creation of libraries of equation oriented models that can be used as building blocks for larger flowsheets. 


# Bibliography