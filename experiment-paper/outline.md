# Explicit Specification Interfaces for Equation-Oriented Process Models

## Positioning

Submit under **Frontiers of Computing and Algorithms in PSE**.

Lead contribution: `pyomo-replace` is a software framework that makes specification intent an explicit, composable interface of equation-oriented process models.

The AI experiment is evaluation evidence, rather than the paper's identity:

> Explicit specification metadata and controlled replacement operations reduce the effort required for an AI agent to produce executable, fully specified process models.

The paper should be grounded in chemical process modelling, with the software-engineering contribution expressed through an API, invariants, provenance, and a reusable initialization contract.

## Central Narrative

Equation-oriented process-model components expose equations and variables, but not their intended specification choices. Consequently, composing models, changing study intent, and delegating model configuration to tools or agents requires fragile, implicit knowledge.

`pyomo-replace` introduces an explicit specification interface through Canonical Variables, Specification Categories, and tracked Replacements. The interface preserves the baseline specification count by construction, records why each non-canonical variable is specified, supports staged initialization, and lets a client switch study intent without manually reconstructing a specification.

Across chemically meaningful flowsheets, the framework supports design and operation style changes. Controlled AI-agent tasks provide evidence that this interface reduces iterative model-configuration effort.

## Claims

The paper should claim that:

1. A model component can expose an explicit, inspectable specification interface, rather than only equations and variables.
2. Replacements represent an auditable change in specification: a non-canonical variable supplies one degree of freedom while the associated Canonical Variable becomes a Guess Variable.
3. The framework enables consistent baseline specifications and reusable staged initialization across study configurations.
4. In the scoped agent experiment, the interface reduces specification effort and failed solve iterations.

The paper should not claim that:

1. Zero counted degrees of freedom guarantees solvability.
2. The library universally improves numerical robustness.
3. The results show better human usability without a human study.
4. AI-agent performance generalizes across models, agents, or prompts.

## Paper Structure

### 1. Introduction: Specification Is an Interface Problem

Start with a realistic flowsheet change: specify outlet pressure or heat duty instead of pump work or heat-transfer coefficient. Explain that a normal algebraic modelling language exposes equations but not the intended specification choices.

State the software-framework contribution and the empirical evaluation contribution.

### 2. Background and Problem Definition

Provide concise equation-oriented modelling and degrees-of-freedom background. Explain the missing abstraction: tools can detect an over- or under-specified model but cannot express which specification should be exchanged, why, or how it initializes.

Position the work against Pyomo/IDAES workflows, structural diagnostics, design specifications, and initialization routines.

### 3. Specification-Management Framework

Define Canonical Variables, Specification Categories, Replacements, Replacement Candidates, and Guess Variables. Describe the invariants and limitations: preserving counted degrees of freedom is bookkeeping, not a structural or numerical solvability proof.

Present the API and the composition behavior for blocks and flowsheets. Describe staged initialization as an implementation consequence of the interface.

### 4. Chemical-Process Modelling Demonstrations

Use the geothermal plant as the main running example. Include a compact before/after specification table containing the requested physical target, replacement variable, Canonical Variable released, category, and interpretation.

Retain the dynamic tank only if indexed or dynamic Replacements are a capability needed for the conference paper. Mention the Ahuora GUI only as evidence that the metadata supports other clients, unless the GUI itself is evaluated.

### 5. Evaluation: Agent-Assisted Flowsheet Specification

State a narrow research question: does the framework make the specification task easier for a constrained AI coding agent?

Explain the common flowsheet structure, scenario descriptions, edit boundary, diagnostics, and acceptance criteria. Report success, session time, model executions, failed executions, patches, and tokens.

Explain qualitative failure modes. Direct specification requires discovering a valid set of variables and initialization guesses; Replacements provide the agent with a constrained operation and visible provenance.

### 6. Discussion

Interpret the agent study as evidence of a more machine-operable software interface, not as generic AI superiority. Explain relevance to reusable process-model libraries, digital twins, automated configuration, and future human-facing tools.

State the experimental limitations: one agent, one agent version, templated tasks, and limited independent runs. Also state that replacement and baseline templates differ in their initialization behavior, so the results should be interpreted as evidence for the complete framework workflow rather than an isolated causal effect of replacement metadata.

### 7. Conclusion

Restate the framework contribution and the bounded experimental result: explicit specification interfaces make equation-oriented process models more composable, interpretable, and operable by software tools.

## Proposed Figures and Tables

1. **Figure 1:** A motivating geothermal unit or mini-flowsheet contrasting direct variable fixing with a tracked Replacement.
2. **Figure 2:** Framework architecture: unit-model author declares Canonical Variables; flowsheet author composes units; a client or tool requests Replacements; initialization uses Guess Variables.
3. **Figure 3:** Agent-study comparison of session time, solve attempts, and failures for geothermal and heat-integration cases.
4. **Table 1:** Framework concepts, invariant, and user-visible effect.
5. **Table 2:** The three flowsheets, their modelling purpose, and the Replacement types demonstrated.
6. **Table 3:** Agent experiment results, including session duration, model runs, failed runs, patches, tokens, and final solve status.

## Existing Evaluation Evidence

The current data supports a scoped proof-of-concept evaluation with `gpt-5.6-terra`.

| Flowsheet | Direct fixing | Direct fixing with guesses | Replacement workflow |
| --- | --- | --- | --- |
| Geothermal | 348.9 s; 5 model runs; 4 failures | 385.3 s; 10 runs; 7 failures | 110.5 s; 2 runs; 1 failure |
| Heat integration | 378.8 s; 9 model runs; 6 failures | 426.5 s; 12 runs; 11 failures | 207.4 s; 3 runs; 2 failures |

The replacement workflow was faster and required fewer iterative solve attempts in both recorded cases. The milk-evaporator sessions report successful solutions but do not yet have aggregate metrics in `experiments/ai-gen/metrics.md`; present it as a qualitative demonstration unless those metrics are extracted.

## Candidate Titles

1. *Explicit Specification Interfaces for Equation-Oriented Process Models: A Pyomo Framework and Agent-Assisted Evaluation*
2. *pyomo-replace: Composable Specification Management for Equation-Oriented Process Flowsheets*
3. *From Variable Fixing to Specification Interfaces in Equation-Oriented Process Modelling*

## Abstract Shape

Equation-oriented process models expose equations and variables but rarely expose the intended choices that specify their degrees of freedom. This makes flowsheet composition, study reconfiguration, initialization, and automated model configuration dependent on implicit modeller knowledge. We present `pyomo-replace`, a Pyomo/IDAES framework that represents a model's default specifications as Canonical Variables and represents alternative specifications as tracked Replacements. The framework preserves the baseline specification count while recording the relationship between an imposed dependent variable and the Canonical Variable released as its Guess Variable. It also supports Specification Categories and staged initialization from canonical guesses. We demonstrate the approach on geothermal power, heat-integration, and multi-effect evaporation flowsheets. In controlled AI-agent configuration tasks, the framework reduced session time and failed solve iterations relative to direct variable fixing for two nontrivial flowsheets. The results indicate that explicit specification interfaces make equation-oriented process models more composable, interpretable, and operable by software tools.
