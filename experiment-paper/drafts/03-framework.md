# 3. Specification-Management Framework

Equation-oriented process models expose variables, constraints, and fixed states, but ordinarily do not expose the intended choices by which a modeller supplies the degrees of freedom of a reusable block. `pyomo-replace` adds that missing interface as flowsheet-level metadata and controlled state transitions. It does not alter the equations, the selected solver, or the underlying Pyomo/IDAES degree-of-freedom and structural-analysis tools.

## 3.1 Concepts and Baseline Contract

A **Specification** is a flowsheet-level declaration that a Canonical Variable, or its active Replacement, supplies one degree of freedom for the model. A **Canonical Variable** is registered by the author as the ordinary Specification for its owning block. Each Canonical Variable has a **Specification Category**, such as `inlet`, `operation`, `design`, or `initial`; categories are labels for model intent, not an additional mathematical constraint.

The registered Canonical Variables define the baseline specification. Registration fixes each newly registered variable. For unit models, registration can occur during construction; subsequently, `register_inlet_ports` registers variables on ports explicitly marked as inlets when those ports have no upstream source. Thus, a flowsheet author can compose registered unit models, expand their connections, register unconnected inlets, and validate the resulting baseline. Validation reports positive counted degrees of freedom as a likely missing Canonical Variable and negative counted degrees of freedom as a likely non-Canonical Variable that has been fixed. It is applied to the supplied block, rather than constituting a proof about a larger model.

**Table 1 placeholder.** Framework concepts, maintained condition, and user-visible effect. Include Specification, Canonical Variable, Specification Category, Replacement, Replacement Candidate, Guess Variable, Internal Replacement, External Replacement, and Provided External Replacement.

## 3.2 Replacement Semantics and Invariants

A **Replacement** is the active substitution of one Canonical Variable by one non-Canonical variable as the Specification for the same degree of freedom. Activating a Replacement unfixes the Canonical Variable and fixes the replacement variable. The released Canonical Variable is therefore a **Guess Variable**: it remains part of the model and retains a value that can be used as an initial guess, but it is no longer fixed in the solve state.

The operation maintains the baseline number of fixed Specifications by exchanging one fixed variable for one previously unfixed variable. The library enforces the following operational invariants:

- Both variables must belong to the `SpecificationState` flowsheet.
- The released variable must be a registered, currently fixed Canonical Variable.
- A Canonical Variable has at most one active Replacement; a repeated request for the same pair restores that pair's fixed/unfixed solve state rather than creating a second record.
- The replacement variable must be a non-Canonical, entirely unfixed variable. Indexed variables are treated atomically: partially fixed indexed variables are rejected.
- After the exchange, the library constructs a Pyomo incidence graph for the flowsheet and rejects the exchange if the Dulmage--Mendelsohn result contains unmatched constraints. In that case it restores the original fixed states.
- Undoing a Replacement fixes its Canonical Variable, unfixes its replacement variable, and removes the record. Deactivating a Specification Category undoes every active Replacement associated with that category.

These conditions make a Replacement auditable and preserve the counted baseline specification count. They do not establish that the new Specification is physically meaningful, feasible, nonsingular in every respect, or numerically solvable. The selection of a suitable Canonical Variable remains a modelling decision, and a zero counted degree of freedom remains bookkeeping rather than a solvability certificate.

## 3.3 Implementation and API

`SpecificationState.for_flowsheet(flowsheet)` obtains the authoritative state object, creating and attaching it to the flowsheet when needed. It stores registered `(Canonical Variable, Specification Category)` pairs and immutable `Replacement` records containing the Canonical Variable, replacement variable, and inherited category. The main client operations are:

```python
specifications = SpecificationState.for_flowsheet(model.fs)
specifications.register([(unit.heat_duty, "operation")])
specifications.register_inlet_ports(model.fs)
specifications.validate(model.fs)

specifications.replace(unit.heat_duty, unit.outlet.enth_mol)
specifications.undo(unit.heat_duty)
specifications.deactivate_category("design")
```

The inspection API exposes `canonical_variables_in`, `fixed_canonical_variables_in`, `replacement_candidates_in`, `replacements_in`, `internal_replacements_in`, `external_replacements_in`, `external_replacements_provided_by`, and `guesses_in`. A **Replacement Candidate** is an unfixed non-Canonical variable returned from the queried block. These queries make the current specification state available to reporting, initialization, and other clients without requiring them to infer intent from fixed flags alone.

## 3.4 Composition and Boundaries

The state is owned at the flowsheet level so that a Replacement can span block boundaries while retaining one authoritative record. For a queried block, an **Internal Replacement** has both its Canonical Variable and replacement variable inside that block. An **External Replacement** has its Canonical Variable inside the queried block and its replacement variable outside it. A **Provided External Replacement** has its replacement variable inside the queried block and its Canonical Variable outside: the queried block provides a Specification to another block. The separate queries distinguish these cases during block-level initialization and client presentation.

This design supports ordinary unit-model composition. Unit authors register their own Canonical Variables and mark inlet and outlet ports; the flowsheet author makes connections, registers unconnected inlet ports, and may add Replacements after composition. The library does not infer port direction from Pyomo itself, so port direction must be declared by the unit model. Nor does the library choose a Replacement automatically: it records and checks an explicit request.

## 3.5 Staged Initialization

The explicit distinction between solve-state Specifications and Guess Variables supports a reusable two-stage initialization pattern. `replacements_suspended_in(block)` temporarily fixes the relevant Canonical Variables and unfixes their replacement variables, while recording the replacement-variable values and fixed states. A unit initializer can first solve the unit in its Canonical Variable configuration. It then reactivates its Internal Replacements and solves again in the requested configuration. On exit, the context restores the solve-state Replacement configuration and saved values.

The supplied `staged_initialise` helper implements this sequence after inlet and outlet property blocks have been initialized: it suspends Replacements in the block, fixes the Canonical Variables, performs a canonical solve, reactivates Internal Replacements, and performs a second solve. A failed solve in either stage raises an initialization error. This is an initialization contract, not a guarantee that guesses are adequate or that every replacement configuration will initialize successfully.

For a block initializer, External Replacements are intentionally not reactivated as Internal Replacements. `external_replacements_suspended_in` is available when a caller must temporarily restore both External Replacements associated with the block and Provided External Replacements. This boundary-aware behavior avoids treating a variable owned by another block as a local replacement during unit initialization.

**Figure 2 placeholder.** Framework architecture: unit authors register Canonical Variables and port direction; the flowsheet composes units and unconnected inlet Specifications; a client activates Replacements; initialization first uses Canonical Variables as fixed Specifications and then restores Internal Replacements, leaving released Canonical Variables as Guess Variables.
