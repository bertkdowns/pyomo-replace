# Pyomo Replacement

Pyomo Replacement manages which model variables specify a flowsheet and how those specifications can be replaced while preserving a solvable model.

## Language

**Specification**:
A flowsheet-level declaration that a canonical variable, or its active replacement, supplies one degree of freedom for a model.
_Avoid_: state variable, configuration

**Canonical Variable**:
A variable registered as the ordinary specification for the block that owns it. It becomes a guess variable while an active replacement supplies that specification.
_Avoid_: state variable

**Specification Category**:
A label that groups Canonical Variables by their role, such as inlet, operation, design, or initial condition.
_Avoid_: variable type

**Replacement**:
The active substitution of a canonical variable with a non-canonical variable as the specification for the same degree of freedom.
_Avoid_: alias, link

**Internal Replacement**:
A Replacement whose canonical variable and replacement variable are both contained by the same queried block.
_Avoid_: local replacement, initialisation replacement

**External Replacement**:
A Replacement with one variable contained by a queried block and the other outside it.
_Avoid_: cross-block replacement

**Provided External Replacement**:
An External Replacement whose replacement variable is contained by the queried block and whose Canonical Variable is outside it. The queried block provides a Specification to another block.
_Avoid_: incoming replacement, outgoing replacement

**Replacement Candidate**:
An unfixed non-canonical variable that can potentially become a Replacement.
_Avoid_: available variable

**Guess Variable**:
A canonical variable made unfixed by an active replacement.
_Avoid_: replacement variable
