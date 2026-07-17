# Background and Literature Review Blueprint

## Purpose and Scope

This section should establish a narrow problem: equation-oriented process models expose equations, variables, and structural diagnostics, but usually do not expose an inspectable interface describing the intended baseline Specifications and valid changes to them. It should motivate `pyomo-replace` as a Pyomo/IDAES framework for recording that interface, not as a new equation-solving, structural-analysis, process-control, or general AI system.

The section should be concise in the submitted paper. This document is deliberately more detailed: it identifies questions to answer, literature to ground them, references already available, targeted additions, and the claims that must remain the paper's own contribution.

Use the project vocabulary consistently:

- A **Specification** is the flowsheet-level declaration that a Canonical Variable, or its active Replacement, supplies one degree of freedom.
- A **Canonical Variable** is a model author's ordinary Specification; when replaced, it becomes a **Guess Variable**.
- A **Replacement** explicitly records the non-canonical variable fixed in place of a Canonical Variable.
- A **Specification Category** labels the role of Canonical Variables, for example inlet, operation, design, or initial condition.

Avoid calling Canonical Variables “state variables,” and avoid describing a Replacement as an alias, link, or configuration. Do not call the framework's bookkeeping a proof that a model is “solvable.”

## Recommended Narrative Order

1. Equation-oriented process modelling and AML abstraction establish why reusable component models expose variables and equations but require specification choices.
2. DoF counting and structural diagnostics establish what present tools can diagnose, and their limit: they do not encode intended exchange relationships or study rationale.
3. Initialization establishes why a changed Specification affects workflow even when counted DoF is retained.
4. Modular flowsheets, ports, and composition establish why the information must survive model assembly and cross-block connections.
5. Design specifications and control connections show related domain concepts for selecting targets and manipulated quantities, while distinguishing them from persistent specification-interface metadata.
6. Software interfaces, metadata, and provenance explain the contribution's representational value: an API with invariants and traceable Replacements.
7. AI-assisted scientific software construction motivates machine-operable interfaces and frames the agent experiment as scoped evaluation evidence, not the paper's primary contribution.

## 1. Equation-Oriented Process Modelling and AMLs

### Questions the review must answer

- What is equation-oriented process modelling, and why is it useful for nonlinear, coupled process flowsheets?
- What abstraction do AMLs and process-model libraries provide through variables, constraints, Blocks, unit models, property packages, Ports, and Arcs?
- Why does an AML's flexible ability to fix or unfix variables leave Specification intent outside the ordinary equation/variable interface?

### Bodies of work to cover

- Equation-oriented flowsheeting and simultaneous process modelling.
- AML design and implementation: declarative model construction, symbolic representation, and composition.
- Open process-modelling platforms and reusable unit/property libraries, especially the Pyomo/IDAES setting used in the paper.
- Equation-based object-oriented modelling as a useful adjacent comparison for component composition, but not evidence that all such environments lack equivalent metadata.

### Existing references to retain from `refs.bib`

- `shacham1982equation`: foundational equation-oriented flowsheeting context.
- `biegler2010nonlinear` and `dowling2015framework`: nonlinear equation-oriented process-model/flowsheet context.
- `fourer1990ampl`, `hart2011pyomo`, `lubin2023jump`, and `robichaud2010introduction`: AML examples. In the final paper, retain only the examples needed for the argument; Pyomo and IDAES should be central.
- `bynum2021pyomo`: current Pyomo reference if a book reference is preferable alongside or instead of the 2011 article.
- `miller2018next` and `lee2021idaes`: IDAES framework, libraries, and process-modelling scope.
- `amador2019introduction` and `casella2008beyond`: gPROMS and equation-based object-oriented modelling as adjacent systems.
- `nicholson2018pyomo`: retain if dynamic/discretized modelling is mentioned.

### Search terms and source types to add

- Search: `equation-oriented process simulation specification degrees of freedom`, `equation-based modelling component interface`, `Modelica connector equation system structural analysis`, `process modelling library reusable unit model interface`.
- Prefer: seminal peer-reviewed process-systems-engineering papers; official architecture papers for mature open frameworks; primary framework documentation only for precise API behavior.
- Add at most one recent review of equation-oriented versus sequential-modular process simulation if it directly supports the distinction used here.

### How this supports novelty

It lets the paper make a precise contrast: existing AMLs make mathematical structure programmable and composable; `pyomo-replace` adds a separate explicit interface for *intended Specifications*. The claim is not that AMLs cannot fix/unfix variables, nor that Blocks alone fail to encapsulate equations.

### Boundaries

- Do not claim all AMLs or all process simulators lack mechanisms analogous to defaults, causality, design specifications, or model annotations without a systematic comparative study.
- Do not present the paper as a replacement for an AML, an equation-based language, a property package, or a solver.
- The statement that normal Pyomo/IDAES models expose variables and constraints but not this particular canonical/replacement relation is a framework observation; support general statements about AML capabilities with citations or documentation.

## 2. DoF, Structural Analysis, and Diagnostics

### Questions the review must answer

- What does DoF counting provide for a specified equation system, and what assumptions make simple variable-minus-constraint counts only operational heuristics?
- What do incidence-based structural analysis, Dulmage-Mendelsohn decomposition, and Jacobian diagnostics identify in under-, over-, and well-constrained systems?
- Why do these diagnostics identify structural symptoms or candidate sets but not the modeller's intended Specification, the rationale for a particular exchange, or an initialization contract?

### Bodies of work to cover

- Classical process design/control DoF analysis.
- Bipartite graph and Dulmage-Mendelsohn structural analysis in declarative/equation-based models.
- Modern equation-oriented diagnostics, including IDAES structural and Jacobian tooling.
- Modular structural analysis/type systems as adjacent work on component-level reasoning.

### Existing references to retain from `refs.bib`

- `luyben1996design`: design and control degrees of freedom; use for process-domain framing, not a proof of the framework's replacement rule.
- `bunus2001debugging`: structural-singularity debugging using Dulmage-Mendelsohn decomposition.
- `lee2024model` and `allan2024jacobian`: current diagnostics and roadblocks in equation-oriented models.
- `nilsson2008type`: modular/type-based structural analysis as adjacent work.
- `biegler2010nonlinear`: numerical and model formulation context.

### Search terms and source types to add

- Search: `Dulmage Mendelsohn decomposition equation based modelling`, `structural analysis equation oriented process models`, `IDAES DegeneracyHunter incidence analysis`, `structural nonsingularity process flowsheet`, `degrees of freedom process simulation independent equations`.
- Prefer: primary algorithm papers or established textbooks for structural claims; IDAES papers/documentation for the behavior of its diagnostic tools.
- Verify terminology carefully: use “Dulmage-Mendelsohn,” not an unsupported variant, and distinguish structural rank from numerical Jacobian rank.

### How this supports novelty

This literature defines the baseline capability that `pyomo-replace` complements. Diagnostics can determine that a proposed Specification is structurally problematic or identify implicated variables/constraints. The framework records a modeller-selected mapping from a fixed non-canonical variable to a released Canonical Variable and maintains the baseline *count* through that operation. It does not infer the mapping automatically.

### Claims requiring citations

- Definitions and standard practice for DoF analysis.
- What Dulmage-Mendelsohn and Jacobian-based diagnostics can detect.
- The assertion that structural diagnostics are commonly used in IDAES workflows.

### Paper's own contribution and boundaries

- The Canonical Variable/Replacement representation, query behavior, and count-preserving operation are the paper's contribution; demonstrate them in Methods, rather than cite them as established literature.
- Say “preserves the baseline Specification count” or “preserves counted DoF under the stated bookkeeping,” never “guarantees a square/solvable model” without qualification.
- Explicitly state that zero counted DoF does not prove equation independence, structural nonsingularity, feasibility, conditioning, or nonlinear solver convergence.
- Do not claim that a Replacement is structurally valid merely because it pairs one fixed and one unfixed variable. Suitability remains a matter for domain expertise and diagnostics.

## 3. Model Initialization and Staged Solution Workflows

### Questions the review must answer

- Why can nonlinear, equation-oriented process models require initialization even when the final model is structurally well posed?
- Which established initialization methods are relevant: sequential decomposition/tearing, homotopy or continuation, simplified models, warm starts, decomposition, and staged release of variables?
- Why does an explicit baseline Specification provide a reusable initialization contract when a study uses active Replacements?

### Bodies of work to cover

- Initialization of nonlinear algebraic and dynamic/DAE models.
- Process-flowsheet sequential decomposition, tearing, and recycle initialization.
- Initialization support within IDAES unit models and flowsheets.
- Staged procedures that solve a nearby or simplified formulation before the intended formulation.

### Existing references to retain from `refs.bib`

- `SAFDARNEJAD201539`: staged initialization strategies for dynamic optimization.
- `lee2021idaes`: IDAES capabilities and process-model context.
- `pyomo_network_doc`: Pyomo Network and sequential-decomposition behavior; update the version/access date or replace with the current official documentation when drafting.
- `Carpanzano01062000` and `bahainv2016tearing`: only retain after validating bibliographic quality and direct relevance.
- `lawrynczuk2022initialisation`: retain only if the text needs NMPC-specific initialization context.
- `dowling2015framework`: relevant if the discussion includes large-scale equation-oriented flowsheet solution.

### Search terms and source types to add

- Search: `initialization equation oriented process simulation review`, `IDAES initialization framework unit models`, `homotopy initialization process flowsheet equation oriented`, `sequential decomposition tear stream initialization process simulation`.
- Prefer: peer-reviewed process-simulation or optimization work for general methods; official IDAES initialization documentation and source-linked examples for framework-specific behavior.

### How this supports novelty

The novelty is not a new numerical initialization algorithm. The framework makes a staged workflow operationally reusable: temporarily restore Canonical Variables as active Specifications, initialize from their values or guesses, then restore Replacements and solve the intended configuration. This connects specification metadata to an initialization contract that model authors can implement once.

### Claims requiring citations

- Nonlinear models' sensitivity to initialization and descriptions of established methods.
- Assertions about IDAES initialization routines and Pyomo Network's tear handling.
- Any quantitative or general reliability claim for staged initialization.

### Paper's own contribution and boundaries

- Cite prior initialization literature, then describe `replacements_suspended_in` and staged restoration as the framework mechanism.
- The turbine and flowsheet demonstrations may support an observed result for their stated models; they do not establish universal initialization robustness.
- Make clear that guesses, scaling, feasible bounds, model formulation, recycle strategy, and solver settings still matter.
- The agent comparison has different templates and initialization behavior between arms. It is evidence for the complete workflow, not an isolated causal estimate of metadata or staged initialization alone.

## 4. Modular and Compositional Modelling

### Questions the review must answer

- How do reusable unit models, Ports/connectors, Arcs, and property packages enable flowsheet assembly?
- Why can a unit's apparent local DoF depend on external connections and flowsheet-level Specifications?
- What must a specification-management interface do when a Replacement crosses a queried block boundary or when components are added/removed?

### Bodies of work to cover

- Object-oriented/equation-based component modelling.
- Pyomo Blocks, Ports, Arcs, and Network transformations; IDAES flowsheet and unit-model composition.
- Modular structural analysis and interface/connector semantics.
- Sequential-modular and equation-oriented integration where helpful to distinguish a connection from a Specification.

### Existing references to retain from `refs.bib`

- `hart2011pyomo`, `bynum2021pyomo`, `lee2021idaes`, and `miller2018next`.
- `pyomo_network_doc`: source for the exact semantics of Network/Arc expansion and sequential decomposition; refresh before publication.
- `nilsson2008type` and `casella2008beyond`: adjacent compositional structural-analysis/equation-based work.
- `hensen2005embedding`: retain only if the final text discusses hybrid sequential-modular/equation-oriented simulators and the source is verified as appropriate.

### Search terms and source types to add

- Search: `Pyomo Block Port Arc network transformation documentation`, `IDAES modular flowsheet unit model ports`, `equation based object oriented modelling connectors composition`, `modular structural analysis equation systems interfaces`.
- Prefer: official Pyomo/IDAES documentation for exact API/connection behavior; peer-reviewed framework or language papers for general compositional claims.

### How this supports novelty

The paper's implementation has one flowsheet-owned `SpecificationState`, while queries are relative to a requested block. This enables Internal Replacements, External Replacements, and Provided External Replacements without incorrectly assigning authority to a child block. That is a concrete composition behavior beyond a per-unit list of defaults.

### Boundaries

- Do not claim that components are independently square in every assembled flowsheet. Connections and external Specifications alter the relevant system.
- Do not equate a Port/Arc connection, which creates model relationships, with a Replacement, which changes the Specification set.
- Dynamic/indexed Replacements should appear only if the final implementation and evidence support them. Matching index cardinality is bookkeeping, not a proof of structural validity across time.

## 5. Design Specifications, Control Connections, and Study Intent

### Questions the review must answer

- How do process simulators express a target output by manipulating an input, and how do control-oriented studies relate controlled variables, manipulated variables, and design variables?
- Why are these concepts relevant to a modeller choosing an alternative Specification?
- Why is a simulator Design Spec or control loop not the same object as a tracked Replacement?

### Bodies of work to cover

- Process design and control degrees of freedom.
- Design-specification/targeting features in commercial and open simulators.
- Steady-state process control and manipulated-versus-controlled-variable selection.
- Design, performance-rating, operation, estimation, and optimization study modes.

### Existing references to retain from `refs.bib`

- `luyben1996design`: central reference for the design/control DoF connection.
- `biegler1997systematic` and `pistikopoulos2021process`: broad PSE and process design/operation framing.
- `aspenplus111_userguide`, `amador2019introduction`, and `tangsriwong2020modeling`: examples of simulator design-spec features. Prefer current vendor documentation for feature descriptions; do not rest broad claims on an old manual alone.
- `microsoft_goalseek_support`: remove from the main literature review unless the paper explicitly needs a simple pedagogical analogy; it is not process-modelling scholarship.
- `casella2008beyond`: possible equation-based control design connection, subject to close reading.

### Search terms and source types to add

- Search: `process simulator design specification manipulated variable target output`, `design and control degrees of freedom chemical process Luyben`, `steady state process model controlled manipulated variables`, `gPROMS design specification documentation`, `DWSIM adjust design specification documentation`.
- Prefer: process-control textbooks and primary PSE literature for conceptual claims; current vendor manuals only to establish a specific feature exists.

### How this supports novelty

Design-spec and control literature supplies the physical rationale for many Replacements: a measured outlet condition may be the target while work, duty, transfer coefficient, or valve position is calculated. `pyomo-replace` does not implement a controller, an optimizer, or a target-solving algorithm. It represents, at the flowsheet level, which Canonical Variable is released when that target is imposed and retains the intent/category/provenance of the exchange.

### Claims requiring citations

- Definitions and relationships of design/control DoF, manipulated variables, and controlled variables.
- The availability and behavior of named simulator features.
- Statements about typical design, operation, performance-rating, or estimation workflows.

### Paper's own contribution and boundaries

- Specification Categories support clients switching study intent; they do not automatically determine a physically appropriate control structure or design decision.
- A Replacement is not an implemented feedback loop and does not claim controllability, observability, closed-loop stability, or regulatory-control feasibility.
- Do not claim that all design-to-operation transitions can be performed by removing category-specific Replacements; present that as an operation supported for models authored with the stated contract.

## 6. Software Engineering: Interfaces, Metadata, and Provenance

### Questions the review must answer

- What does software-engineering literature say about explicit interfaces, contracts, encapsulation, metadata, and provenance as supports for reuse, inspection, and automation?
- Which of those ideas transfer directly to scientific-model libraries, and which should be framed as an analogy rather than a demonstrated equivalence?
- What information must be captured to explain a non-canonical fixed variable: released Canonical Variable, category, ownership, lifecycle, and initialization role?

### Bodies of work to cover

- API/interface contracts and design by contract.
- Scientific software metadata, model provenance, and reproducibility.
- Semantic annotations/model interchange in process or equation-based modelling, if directly comparable.
- Software traceability and change provenance, particularly where a model configuration must be inspected after assembly.

### Existing references to retain from `refs.bib`

- The existing bibliography has no strong, direct source for interface contracts, metadata, provenance, or scientific-software traceability. Do not use the current type-system analogy in `content.tex` as a literature claim without appropriate sources.
- `hart2011pyomo` and `lee2021idaes` can support the concrete framework abstractions, not general software-engineering conclusions.

### Search terms and source types to add

- Search: `design by contract software interfaces Meyer`, `scientific software provenance metadata reproducibility`, `computational model provenance workflow provenance`, `model metadata traceability engineering simulation`, `FAIR computational models metadata`.
- Search process-specific candidates: `CAPE-OPEN model metadata interoperability`, `Modelica annotations documentation provenance`, `semantic annotation process model interoperability`.
- Prefer: seminal software-engineering primary sources for contracts; peer-reviewed scientific-workflow/provenance literature; standards/specifications for named metadata or interoperability mechanisms.

### How this supports novelty

This lens provides the paper's central framing. A `SpecificationState` is an interface owned by the flowsheet, not a hidden convention distributed across arbitrary `fix()` calls. Immutable Replacement records and block-relative queries expose provenance: what is specified, what Canonical Variable was released, its category, and whether the relation crosses a block boundary. The invariant is a controlled, inspectable API transition rather than a claim that the mathematical problem is validated.

### Claims requiring citations

- General claims that explicit contracts/metadata/provenance improve reuse, auditability, reproducibility, or automation.
- Descriptions of any named provenance standards or interoperability systems.

### Paper's own contribution and boundaries

- “Auditable” should mean the framework records and can query the Replacement relationship. Do not imply regulatory audit compliance, full computational reproducibility, or complete provenance of equations, data, parameters, solver versions, and execution environments.
- Treat the type-system comparison as a brief analogy, not a proof that the framework has type-system guarantees.
- Do not claim improved human interpretability as an empirical result without a human study. The paper can state that the metadata is *designed to make* intent inspectable and show examples.

## 7. AI-Assisted Scientific Software and Model Construction

### Questions the review must answer

- What is known about AI coding agents or language models assisting scientific software, mathematical modelling, or engineering workflows?
- Why do constrained APIs, explicit schemas, diagnostics, and visible provenance plausibly help a tool operate a model-construction task?
- What does the controlled experiment actually measure, and what cannot be generalized from it?

### Bodies of work to cover

- AI-assisted programming and coding-agent evaluation.
- Language models for scientific computing, symbolic/mathematical reasoning, or engineering modelling, only where the work is relevant to executable model construction.
- Tool-using agents, structured interfaces, and constrained action spaces.
- Benchmark design and threats to validity for agent evaluations.

### Existing references to retain from `refs.bib`

- No existing reference directly supports this body of work. Do not cite general PSE/digital-twin papers as evidence that AI agents construct models effectively.
- `walmsley2024adaptive` and `severinsen2024digital` may remain for the application context of digital twins, not for AI-agent claims.

### Search terms and source types to add

- Search: `LLM coding agent evaluation software engineering benchmark`, `AI agent scientific computing code generation evaluation`, `large language models equation oriented modelling process systems engineering`, `language model engineering design automation scientific software`, `tool use constrained action space language models`.
- Prefer: peer-reviewed or well-documented benchmark studies; primary system papers; careful surveys from software engineering, scientific computing, or PSE. Label preprints as such and avoid using product announcements as evidence.
- Search specifically for process-systems-engineering applications, but do not broaden the paper around weakly related “AI for chemistry” work.

### How this supports novelty

The literature can motivate the need for machine-operable scientific-software interfaces. The paper's new evidence is narrower: in recorded, constrained `gpt-5.6-terra` sessions, a replacement workflow required less session time and fewer failed model executions for the geothermal and heat-integration tasks than the recorded direct-fixing cases. The contribution is interface evidence in a process-modelling task, not a new agent or benchmark.

### Claims requiring citations versus experiment evidence

Claims needing citations:

- General capabilities, limitations, reproducibility concerns, and evaluation practice for AI coding agents.
- General assertion that structured interfaces can help automated tools, if made beyond the experiment's measured setting.

Claims supported by this paper's methods/results, not external citations:

- The prompts, edit boundary, templates, diagnostics, agent version, and measurements used in the experiment.
- The recorded outcomes for this agent/model/task configuration.
- Qualitative failure modes observed in exported sessions, provided they are reported as observations rather than generalized causes.

### Boundaries

- Do not claim better human usability, generic AI superiority, or broad gains in software engineering productivity.
- Do not generalize across agents, model versions, prompts, flowsheets, programming environments, or independently repeated runs.
- State that replacement and baseline templates differ in initialization behavior; the comparison evaluates the complete workflow and cannot isolate the causal contribution of Replacement metadata.
- Avoid presenting token count, session duration, patches, or solve attempts as universal quality metrics. Define each operationally in Methods.

## Cross-Cutting Citation Discipline

Use citations for field facts, definitions, historical claims, framework/tool behavior, simulator features, and generalizations beyond the demonstrated models. Use the paper's Methods, API listing, and results for the new framework and experiment.

| Statement type | Evidence to use |
| --- | --- |
| Equation-oriented modelling, AMLs, process-library capabilities | Foundational/primary framework literature |
| DoF and structural diagnostic behavior | Structural-analysis literature and current tool documentation |
| Initialization strategies and numerical sensitivity | Numerical/process-systems literature |
| Design specifications and control concepts | Process control/design literature; current simulator documentation for product features |
| Interfaces, metadata, provenance | Software-engineering and scientific-provenance literature |
| Agent capability or evaluation practice | AI/software-engineering evaluation literature |
| Canonical Variables, Categories, Replacements, Guess Variables, ownership and queries | This paper's Methods and implementation |
| Measured geothermal/heat-integration outcomes | This paper's controlled experiment |

Avoid citation laundering: a vendor manual can establish that a feature exists, but not a broad scientific conclusion; an IDAES diagnostic report can establish tool behavior, but not prove the framework's novelty; a single agent experiment cannot support claims about AI systems generally.

## Explicit Exclusions for the Final Review

- No exhaustive history of AMLs, commercial simulators, Modelica, optimization, digital twins, or AI for science.
- No tutorial derivation of graph matching, Dulmage-Mendelsohn decomposition, nonlinear programming, or controller synthesis beyond what is necessary to state the gap.
- No comparison matrix claiming feature coverage across Pyomo, IDAES, gPROMS, Aspen Plus, DWSIM, Modelica, or other platforms unless each feature is verified from primary sources.
- No claim that the framework automatically selects a valid Replacement, repairs structural singularity, chooses good guesses, scales equations, finds feasible solutions, or replaces diagnostics.
- No claim that the framework implements process control, optimization, model predictive control, state estimation, or digital-twin lifecycle management.
- No claim of universal numerical robustness, maintainability, interpretability, or usability improvements.
- No claim that the AI experiment establishes causal effects of metadata independently of templates, initialization, prompts, or diagnostics.

## Drafting Checklist

- Lead with the missing abstraction, not with generic digital-twin motivation.
- Define “Specification” before discussing DoF; retain “Canonical Variable,” “Replacement,” and “Guess Variable” consistently.
- Put the operational DoF caveat adjacent to the first count equation.
- State that diagnostics and domain judgement remain necessary when selecting a Replacement.
- Distinguish connections/equations from Specifications, and structural validity from numerical convergence.
- Make initialization a workflow consequence of the explicit interface, not an unqualified solver improvement claim.
- Treat design/control concepts as motivation for study-dependent Specification changes, not as an assertion that a Replacement is a controller.
- Describe provenance concretely as stored relationships and queries, not as full model reproducibility.
- Place AI literature late and keep the agent study subordinate to the framework contribution.
- Refresh all documentation citations, vendor manuals, URLs, versions, and access dates immediately before submission.
