# AI Generated Flowsheet Experiments

This is a series of tests where we asking an AI agent to fully specify a flowsheet. We compare when the agent is using pyomo-replace to without using pyomo-replace.

The goal is to see whether pyomo-replace makes it easier for an AI agent to fully specify a flowsheet.

## Methodology

### Input data

We create a markdown file describing the flowsheet we are trying to build in detail. This provides a common reference point to make sure each case fully defines the model to the same conditions.

We also create a "template file" where we build the model structure, adding the unit operations and arcs, and initialisation and solving methods. This is to reduce variability in the result; without this, the agent may build a drastically different structure or initialisation method, which could have a large effect on the result. Instead, this means the agent will only focus on fixing the correct variables. Likewise, using the exact same unit operations and names makes it easier to compare between the cases.

The template file is slightly different between the two cases: where pyomo-replace is used, the models include variable replacement and fix the appropriate variables by default, in the way pyomo-replace is intended to be used. An example of fixing and replacing a few variables is also provided, to allow the agent to understand the intended workflow behind the library. To keep things equivalent, the base case shows how to directly fix those same variables.

This template file also provides debugging methods, printing the over-constrained or under-constrained sets and unit operation reports. In the case of pyomo-replace, it also prints the list of canonical variables and anything that is replacing them.

The template file for pyomo-replace also includes the standard two-stage initialisation pyomo-replace is designed to work with: first initialising without any active variable replacements, then re-solving with the variable replacements enabled.

Both the replaced and base case branches are available at https://github.com/waikato-ahuora-smart-energy-systems/Ahuora-Adaptive-Digital-Twin-Platform/pull/2243

### Prompt

We then run a clean opencode session (using v1.18.1), with a prompt such as the following:

```
You are provided with an IDAES model file (geothermal_plant.py) and a markdown file (geothermal_plant.md) describing the scenario it models. While the structure of the model is present, the correct variables in the model have not been fixed or set to the correct values.

Implement the specify_model method to solve the model as per the specifications in the markdown file. DO NOT change any of the other methods or any other code. You may work iteratively, rerunning the file; the diagnostics methods will provide feedback on if the fixed variables you have chosen are structurally stable. Run the file before starting to see the current state. Continue working until the model solves matching the description in the markdown file. 
```

We then provide extra information about the variable fixing method to use, to reinforce if we expect variable-replacement or directly fixing variables:


Default case:

```
Use var.fix() to fix variables as shown in the examples at the start of specify_model.
```

Pyomo-replace:

```
Use specs.fix(var,value) to fix variables as shown in the examples at the start of specify_model. If you want to fix a variable that is not a canonical variable, you must choose a canonical variable to replace it by using specs.replace(canonical_var,replacement_var)
```

For the base case, we also try with and without allowing the agent to specify additional "guess variables". This is because the replacement method has a staged initialisation method, and allowing the agent to specify guesses can compensate for initialisation being simpler.

```
Do not set guesses to variables that are not fixed; allow the model to solve for those values
...
You may set guesses for other variables using var.set_value(), only as required to enable the model to solve. They should be approximate order-of-magnitude guesses, rather than exact solve values.
```

We prompt the AI once, and do not provide any follow-up from there.

### Results


We export results using the following command:

```bash
opencode export <sessionID> > session.json
```

It can be viewed again with `opencode import session.json` and then `opencode -s <ses_...imported-id-here>`

Some of the things to look for in the results include:

- Did the agent successfully fix all the required variables?
- How many times did the agent attempt to solve the flowsheet?
- How many tokens did the agent use?
- How many lines of code did the agent produce?
- How many patches did the agent make?
- What was the total running time of the session?
- Did the flowsheet model successfully solve?

There are also some more qualitative things to look for:

- Did both models end up specifying the same properties, or did they use different properties to fully define the model?
- What did the model get confused or stuck in?
- What were the reasons for any failures?
- Did the model do anything unexpected?
