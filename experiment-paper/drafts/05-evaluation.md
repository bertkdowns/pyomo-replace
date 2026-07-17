# 5. Evaluation: Agent-Assisted Flowsheet Specification

## 5.1 Research Question and Experimental Design

We evaluated a narrow question: *does an explicit specification interface make it easier for a constrained coding agent to fully specify a supplied equation-oriented flowsheet?* This is an evaluation of the complete `pyomo-replace` workflow for one agent configuration, not a benchmark of language models or a general comparison of process-modelling systems.

Each task supplied `gpt-5.6-terra` with a Markdown case description and a Python template containing the flowsheet topology, unit operations, arcs, diagnostics, initialization and solve routines. The agent's only requested code change was to implement `specify_model`; it was instructed to run the model, use diagnostics, and continue until the described model solved. A clean OpenCode session was used for each run, with one prompt and no human follow-up. The recorded OpenCode versions were 1.17.20 for geothermal and 1.18.2--1.18.3 for the later cases.

The direct-fixing template required `var.fix()` calls. The replacement template exposed Canonical Variables and examples, required `specs.fix()`, and required a call to `specs.replace(canonical_var, replacement_var)` before fixing a non-canonical variable. It also included the framework's two-stage initialization: initialize from the canonical specification and guesses, then re-solve with active Replacements. To examine whether allowing direct-fixing workflows to set unfixed-variable values would offset this initialization advantage, a second direct condition permitted approximate `set_value()` guesses. Thus the comparison is between three workflows: direct fixing without guesses, direct fixing with optional guesses, and the replacement workflow.

The templates deliberately constrain the edit boundary and hold the flowsheet structure and unit names fixed. This reduces variation from model construction, but it also means that the test measures configuration of prepared templates rather than open-ended model authoring. The replacement and direct templates are not identical: in addition to the specification API, the replacement template supplies Canonical Variable metadata, replacement diagnostics, examples, and staged initialization. Results therefore estimate the effect of the complete workflow, not an isolated causal effect of Replacement metadata.

The cases cover: (1) a geothermal-heated n-butane power loop with heat exchangers, a pump, a turbine, and recycle; (2) a water-only heat-integration and steam-generation study with cooling loads, heat pumps, a boiler, and a steam header; and (3) a three-effect milk evaporator with direct-steam injection and three mechanical-vapor-recompression recycles. The latter adds two property domains and multiple coupled recycles. All cases are steady state.

We exported each session and recorded session duration, input, output and reasoning tokens, patches, changed lines, model runs, and failed model runs. A successful model execution is inferred from the non-failed execution recorded in each session; the records do not establish a separate numerical-accuracy metric beyond the task's solved-state and scenario-matching acceptance criterion.

## 5.2 Quantitative Results

Table 1 reports all currently aggregated sessions. There was one run for each flowsheet-workflow condition, so the values are observations, not estimates of a distribution. `Failures` counts model executions that did not complete successfully; it includes failures caused by the execution environment as well as model or specification failures when they occurred during the session.

| Flowsheet | Workflow | Duration (s) | Model runs | Failures | Patches | Input tokens | Output tokens | Reasoning tokens |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Geothermal | Direct fixing | 348.859 | 5 | 4 | 2 | 143,399 | 4,125 | 5,752 |
| Geothermal | Direct fixing + guesses | 385.333 | 10 | 7 | 8 | 102,538 | 5,696 | 5,968 |
| Geothermal | Replacement workflow | 110.529 | 2 | 1 | 1 | 68,774 | 2,547 | 1,553 |
| Heat integration | Direct fixing | 378.836 | 9 | 6 | 8 | 161,238 | 6,051 | 4,266 |
| Heat integration | Direct fixing + guesses | 426.478 | 12 | 11 | 10 | 150,738 | 7,888 | 5,959 |
| Heat integration | Replacement workflow | 207.406 | 3 | 2 | 2 | 58,580 | 3,338 | 2,284 |
| Milk evaporator | Direct fixing | 109.605 | 3 | 2 | 1 | 51,083 | 2,447 | 704 |
| Milk evaporator | Direct fixing + guesses | 93.516 | 3 | 2 | 1 | 62,338 | 1,792 | 521 |
| Milk evaporator | Replacement workflow | 113.809 | 2 | 1 | 1 | 51,143 | 2,380 | 843 |

**Table 1.** Session-level metrics from the exported OpenCode sessions. No repetitions or uncertainty intervals are available.

For the two cases selected in the original quantitative comparison, the replacement workflow was faster and involved fewer model executions than either direct condition. In the geothermal case, it took 110.529 s, compared with 348.859 s for direct fixing and 385.333 s when guesses were allowed. Relative to direct fixing, this is a 68.3% reduction in duration, from five to two model runs (60.0% fewer) and from four to one failed run (75.0% fewer). Relative to direct fixing with guesses, duration fell 71.3%, model runs fell from ten to two, and failures fell from seven to one. It also used one patch rather than two or eight.

In the heat-integration case, the replacement workflow took 207.406 s, versus 378.836 s for direct fixing and 426.478 s with guesses. This corresponds to 45.3% and 51.4% shorter recorded session durations, respectively. Model runs fell from nine and twelve to three; failed runs fell from six and eleven to two. The replacement session used two patches, compared with eight and ten. It also had lower input-token counts in both comparisons: 58,580 versus 161,238 and 150,738. These reductions are descriptive measurements of these sessions; token counts and wall-clock duration can also depend on tool execution, cached context, and the agent's exploration path.

The milk-evaporator sessions extend the demonstration but do not reproduce the same timing pattern. The replacement workflow had two runs and one failure, versus three runs and two failures for each direct workflow, with one patch in all three conditions. Its 113.809-s duration was 3.8% longer than direct fixing and 21.7% longer than direct fixing with guesses. The three sessions each recorded one non-failed model run. Consequently, this case supports the feasibility of applying the workflow to a more coupled, multi-domain flowsheet, but it is not evidence that replacement reduces elapsed time for every flowsheet.

## 5.3 Observed Behaviour and Scope

The session exports show that direct workflows required the agent to infer a sufficient and structurally valid collection of fixed variables from the process description, source code, and diagnostics. In contrast, the replacement workflow exposed a constrained operation: set an intended specification and identify the Canonical Variable it replaces. The replacement report made the active specification relationships inspectable, while the staged procedure retained values for released Canonical Variables as initialization guesses. These interface features are consistent with the reduced iteration observed in the geothermal and heat-integration sessions.

The result should not be read as proof that a zero counted degree of freedom is sufficient for solvability, or that the framework improves numerical robustness in general. A Replacement preserves the baseline specification count; it does not prove independence of equations, structural nonsingularity, feasibility, or convergence. Nor does this study measure process-model accuracy, physical-model validity, human usability, or the quality of downstream optimization and control decisions.

The quantitative evidence is limited to nine single sessions with one model family, one agent model (`gpt-5.6-terra`), closely related prompts, prepared templates, and no independent repetitions. The agent and OpenCode versions also varied across cases. Environment discovery and interpreter failures were among recorded failed executions, particularly in worktree-based direct sessions, so failure counts are not a pure numerical-solver outcome.
