### Base Prompt

You are provided with an IDAES model file (geothermal_plant.py) and a markdown file (geothermal_plant.md) describing the scenario it models. While the structure of the model is present, the correct variables in the model have not been fixed or set to the correct values.

Implement the specify_model method to solve the model as per the specifications in the markdown file. DO NOT change any of the other methods or any other code. You may work iteratively, rerunning the file; the diagnostics methods will provide feedback on if the fixed variables you have chosen are structurally stable. Run the file before starting to see the current state. Continue working until the model solves matching the description in the markdown file. Do not set guesses to variables that are not fixed; allow the model to solve for those values.

Use var.fix() to fix variables as shown in the examples at the start of specify_model.


### Allowed Guesses

You are provided with an IDAES model file (geothermal_plant.py) and a markdown file (geothermal_plant.md) describing the scenario it models. While the structure of the model is present, the correct variables in the model have not been fixed or set to the correct values.

Implement the specify_model method to solve the model as per the specifications in the markdown file. DO NOT change any of the other methods or any other code. You may work iteratively, rerunning the file; the diagnostics methods will provide feedback on if the fixed variables you have chosen are structurally stable. Run the file before starting to see the current state. Continue working until the model solves matching the description in the markdown file. You may set guesses for other variables using var.set_value(), only as required to enable the model to solve. They should be approximate order-of-magnitude guesses, rather than exact solve values.

Use var.fix() to fix variables as shown in the examples at the start of specify_model.


### Pyomo-replace

You are provided with an IDAES model file (geothermal_plant.py) and a markdown file (geothermal_plant.md) describing the scenario it models. While the structure of the model is present, the correct variables in the model have not been fixed or set to the correct values.

Implement the specify_model method to solve the model as per the specifications in the markdown file. DO NOT change any of the other methods or any other code. You may work iteratively, rerunning the file; the diagnostics methods will provide feedback on if the fixed variables you have chosen are structurally stable. Run the file before starting to see the current state. Continue working until the model solves matching the description in the markdown file. Do not set guesses to variables that are not fixed; allow the model to solve for those values.

Use specs.fix(var,value) to fix variables as shown in the examples at the start of specify_model. If you want to fix a variable that is not a canonical variable, you must choose a canonical variable to replace it by using specs.replace(canonical_var,replacement_var)
