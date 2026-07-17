# Experiment Insights

## Scope and evidence

These are controlled, single-session configuration tasks with `gpt-5.6-terra`. In each session the agent was asked to implement only `specify_model`, using a scenario description, a supplied flowsheet template, and structural diagnostics. The direct conditions used `var.fix()`; the replacement condition used `specs.fix()` and required a `Replacement` before fixing a non-Canonical Variable. The recorded metrics count Python commands matching a model-file pattern; a nonzero tool exit is a failed model run. They do not by themselves establish physical correctness or a general performance distribution. Sources are `experiments/ai-gen/methodology.md`, `metrics.md`, final per-condition model files, and the exported `session.json` traces.

The replacement templates include the intended two-stage initialization: initialize with Replacements suspended, when Canonical Variables are fixed and the associated replacement variables are Guess Variables, then restore Replacements for the final solve. The direct templates do not have that same initialization contract. Thus comparisons evaluate the complete workflow, not replacement metadata alone.

## Per-case account

### Geothermal organic power loop

The scenario, retained in the session exports as `geothermal-plant-summary.md`, describes a steady-state, closed n-butane loop heated by geothermal water, with recuperation and a cooling-water utility. The final direct and replacement sources both express physical targets including pump and turbine outlet pressures, exchanger outlet temperatures, exchanger areas and zero pressure drops, the geothermal feed, and cooling-side conditions. In the replacement source, pressure and temperature targets are expressed as Replacements for Canonical Variables such as mechanical work and overall heat-transfer coefficient; this makes the released Canonical Variable a Guess Variable during staged initialization.

| Condition | Duration (s) | Model runs | Failed runs | Patches | Input tokens | Trace outcome |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Direct fixing | 348.9 | 5 | 4 | 2 | 143,399 | Final session report records zero DOF and IPOPT optimality. |
| Direct fixing with guesses | 385.3 | 10 | 7 | 8 | 102,538 | Final session report records zero DOF and IPOPT optimality. |
| Replacement workflow | 110.5 | 2 | 1 | 1 | 68,774 | Final session report records zero DOF and optimal initialization and final solve. |

The replacement run was 238.3 s shorter than the recorded direct run and used three fewer model runs; it was 274.8 s shorter than direct fixing with guesses and used eight fewer runs. These are observations from one run per condition, not estimates of an expected speedup. The direct-with-guesses trace illustrates the burden of hand-managed initialization: it added coarse enthalpy `set_value()` calls across the loop and required repeated investigation of preheater initialization and flow-target choices. Its final report says, “Added coarse enthalpy initial guesses required for stable initialization” (`geothermal/base_with_guesses/session.json`, line 5051).

The replacement report provides a corroborating provenance observation: its specification report explicitly prints `fs.condenser.overall_heat_transfer_coefficient -> ...temperature_var`, while the final trace states that calculated coefficients, duties, work, and auxiliary flow were left unfixed (`geothermal/replaced_case/session.json`, lines 794 and 2271). This is the intended behavior: a physical target supplies the Specification while the associated Canonical Variable becomes a Guess Variable. A notable direct-workflow failure mode was the temptation to fix a scenario-derived auxiliary flow rather than represent the specified downstream total-flow target; the trace includes a review finding that called this out before the agent revised the approach (`geothermal/base_with_guesses/session.json`, line 4308).

### Heat integration and steam generation

The session-retained scenario describes a water-only, steady-state heat-recovery and steam-generation study: two cooling loads and an air-source heat pump feed a steam heat pump, gas boiler, and export header. The final replacement model uses Replacements for the steam heat-pump duty, air-source heat-pump coefficient of performance, steam quality targets, boiler outlet condition, and steam split. This is a more varied use of the framework than geothermal: both operation and design Specification Categories are present, and several non-Canonical targets are made explicit.

| Condition | Duration (s) | Model runs | Failed runs | Patches | Input tokens | Trace outcome |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Direct fixing | 378.8 | 9 | 6 | 8 | 161,238 | Final session report records zero DOF and two optimal solves. |
| Direct fixing with guesses | 426.5 | 12 | 11 | 10 | 150,738 | Final session report records zero DOF and two optimal solves. |
| Replacement workflow | 207.4 | 3 | 2 | 2 | 58,580 | Final session report records zero DOF and optimal initialization and final solve. |

The replacement run was 171.4 s shorter than direct fixing and used six fewer model runs; against direct fixing with guesses it was 219.1 s shorter and used nine fewer runs. Again, these are single-run differences only. The direct-with-guesses condition was not helped by the permission to set guesses in this trace; it had the largest number of runs and failures. Its final source also contains many manually set initialization values, whereas the replacement template supplies staged initialization.

This case exposes an important failure mode independent of degree-of-freedom bookkeeping. The replacement agent first attempted to use `vapor_frac` as a replacement target, received an attribute failure, inspected the state block, and replaced it with `enth_mol` calculated from pressure and vapor fraction (`heat-integration/replaced_case/session.json`, lines 1748 and 2348). The trace also contains an IPOPT warning that an air-source heat-pump subproblem “Converged to a locally infeasible point” during an intermediate initialization despite later completion (`base_case/session.json`, line 4029). Zero degrees of freedom and an eventual optimal final solve should therefore not be presented as evidence that every intermediate initialization was unproblematic.

The scenario itself appears to contain a steam-feed-pressure inconsistency. The direct-with-guesses trace says it selected the “saved 1,000 kPa steam-state basis to resolve the documented feed-pressure inconsistency” (`heat-integration/base_with_guesses/session.json`, line 4683). This must be reported as an experimental-material ambiguity, not as an agent or framework result.

### Three-effect milk evaporator with MVR

This case is a three-effect milk concentration train with direct steam injection, three pressure reductions, three vapor-liquid separators, and three mechanical-vapor-recompression recycle loops. The scenario explicitly gives feed composition and conditions, valve drops, separator splits, heat-exchanger U and area, zero drops, and compressor efficiencies and outlet pressures. In the replacement source, each compressor outlet-pressure Specification replaces the respective compressor-work Canonical Variable. The three resulting Replacements are a compact, repeated example of the intended pattern.

| Condition | Duration (s) | Model runs | Failed runs | Patches | Input tokens | Trace outcome |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Direct fixing | 109.6 | 3 | 2 | 1 | 51,083 | Final session report records zero DOF and IPOPT `Optimal Solution Found`. |
| Direct fixing with guesses | 93.5 | 3 | 2 | 1 | 62,338 | Final session report records zero DOF and IPOPT `Optimal Solution Found`. |
| Replacement workflow | 113.8 | 2 | 1 | 1 | 51,143 | Final session report records zero DOF and IPOPT `Optimal Solution Found`. |

All three recorded sessions succeeded, but this case does not support a time advantage for the replacement workflow: its 113.8 s duration exceeded direct fixing by 4.2 s and direct fixing with guesses by 20.3 s. It did use one fewer model run and failed run. The appropriate interpretation is that the framework accommodated repeated compressor-pressure Replacements and staged solving on a recycle flowsheet, not that it improved all task outcomes.

An environmental failure occurred in the direct-with-guesses session: “The default interpreter cannot import the installed scientific stack because its SciPy and NumPy binaries are incompatible” (`milk-evaporator/base_with_guesses/session.json`, line 540). The agent switched to the local environment and later obtained an optimal solve. This is a session/tooling issue and should not be attributed to the specification interface. The replacement session also first ran with incomplete direct-steam-injection and valve values visible in diagnostics, then patched the requested values and solved; this supports reporting iterative correction, not one-shot correctness.

## Key result insights

1. In both larger recorded cases, the replacement workflow had fewer recorded model runs, fewer failed model runs, fewer patches, shorter duration, and fewer input tokens than either direct condition. Geothermal was 2 runs/1 failure with replacements versus 5/4 direct and 10/7 direct-with-guesses; heat integration was 3/2 versus 9/6 and 12/11.
2. The milk case qualifies that pattern. All conditions reached a recorded optimal solve; replacement used fewer runs but was not faster. The evidence supports heterogeneous task-level behavior, not universal numerical or agent-performance superiority.
3. The specification reports and final sources show the mechanism expected of the framework: a scenario-facing non-Canonical Variable becomes the active Replacement, its Canonical Variable is released as a Guess Variable, and the relationship is inspectable. Examples include condenser outlet temperature versus overall heat-transfer coefficient, heat-pump duty/COP/dryness targets versus Canonical Variables, and compressor outlet pressure versus compressor work.
4. Direct fixing required the agent to discover which fixed variables to release and, in difficult cases, to create initialization guesses. Replacements constrained that choice to an explicit API operation and preserved an auditable association. This is evidence of a more machine-operable specification interface, not proof that direct fixing cannot work.

## Results versus discussion

**Results should report:** the three flowsheets and task boundary; the exact one-run metrics table; recorded final-session solve status and structural diagnostic status; the explicit Replacements represented in final sources; and concise, traceable factual observations such as the `vapor_frac` to enthalpy correction and the milk environment error.

**Discussion should interpret:** the lower iterative effort in geothermal and heat integration as scoped evidence that explicit Canonical Variables and Replacements assist this agent in these templates; the inspectable relationship between a physical target and the released Guess Variable; and why staged initialization is useful in equation-oriented flowsheets. It should explain, rather than hide, the milk counterexample and the failure modes. It should not characterize zero counted degrees of freedom as a solvability proof.

## Limitations

- There is one recorded run per condition, using one model family (`gpt-5.6-terra`); no variance, confidence interval, or statistical claim is available.
- The methodology says OpenCode v1.18.1, but session metadata records v1.17.20, v1.18.2, and v1.18.3. Version consistency should be clarified before publication.
- Replacement and direct templates intentionally differ: Replacements, diagnostics, and their two-stage initialization are part of the replacement template; direct-with-guesses also changes the prompt and permits `set_value()` guesses. Effects cannot be causally isolated to metadata, API, prompt, or initialization procedure.
- The scenarios and model structures are supplied and the agent edits only `specify_model`; this is a constrained configuration task, not a test of flowsheet construction, physical-model validation, or human usability.
- Geothermal and heat-integration scenario markdown is available in the session exports rather than as a retained case-local file; the heat-integration materials contain a pressure-basis ambiguity.
- Session self-reports and solver markers support recorded completion, but were not independently re-executed here. Structural zero DOF, a clean Dulmage-Mendelsohn report, and IPOPT optimality do not establish a unique, physically valid, or robust solution.
- Environment and repository-state issues appear in traces, including the milk SciPy/NumPy mismatch. Runtime and token measurements include agent exploration and tooling effects, not just specification reasoning.
