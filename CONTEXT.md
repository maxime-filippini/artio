# Artio

Artio is a visual authoring environment for data-transformation workflows expressed as Python using Polars.

## Language

**Workflow**:
A named, code-defined data-transformation process whose structure can be inspected and edited through a graphical or code-based interface.
_Avoid_: Pipeline, job, flow

**Workflow definition**:
The canonical Python source code that expresses a Workflow in terms of Polars operations.
_Avoid_: Graph definition, visual definition

**Workflow graph**:
A derived directed acyclic graph that represents the data dependencies and transformations in a Workflow definition for visualization and structured editing.
_Avoid_: Workflow definition, pipeline

**Workflow revision**:
A monotonically increasing version of a successfully derived Workflow graph. A failed reconciliation does not create a new revision.
_Avoid_: File version, source revision

**Workflow input schema**:
The named, typed contract declared by a Workflow for execution-time values shared by its Sources and Transformations. Workflow inputs are not Workflow graph nodes or dependency edges.
_Avoid_: Source schema, DAG parameter

**Workflow input**:
A validated value supplied for one field of a Workflow input schema for a particular execution.
_Avoid_: Source, dependency, global variable

**Source span**:
The inclusive-start, exclusive-end location of a declaration or Diagnostic in a Workflow definition, expressed as a one-based line and zero-based column.
_Avoid_: Source range, offset

**Transformation**:
A named Workflow graph node that accepts one or more upstream Polars lazy frames and returns a Polars lazy frame using ordinary Polars code. Managed Transformations are lazy-first.
_Avoid_: Step, task, operator

**Decision tree**:
An independently managed, named set of ordered conditional branches in which the first matching condition selects a branch and an explicit fallback covers every remaining row. A Transformation can use a Decision tree to produce a Polars expression.
_Avoid_: Rules engine, ternary

**Expression asset**:
A named, reusable Polars expression authored independently of a Transformation. Decision trees are Expression assets.
_Avoid_: Helper, macro

**Tree parameter**:
A named input declared by a Decision tree and explicitly bound at each use to either a column or a literal. Tree parameters have no default bindings.
_Avoid_: Default value, implicit input

**Fixture**:
A named local Parquet sample-data declaration that can be reused by Workflow sources and Decision trees.
_Avoid_: Inline path, test case

**Tree fixture binding**:
A Fixture and explicit Tree parameter bindings used to execute and inspect a Decision tree independently of a Workflow.
_Avoid_: Assertion, workflow source

**Verified Decision tree**:
A Decision tree revision that successfully executes against its Tree fixture binding and exposes its resulting schema and bounded rows for inspection.
_Avoid_: Proven correct, assertion-passing

**Managed node**:
A source, Transformation, or output declaration that Artio can identify and modify structurally in a Workflow definition. Transformations are declared as decorated Python functions.
_Avoid_: Generated code, visual node

**Module setup**:
Ordinary top-level Python in a Workflow definition that runs when Artio loads the module but does not declare, form part of, or receive structural edits to the Workflow graph.
_Avoid_: Graph node, managed code

**Opaque transformation**:
A Managed Transformation whose declared identity and dependencies are understood by Artio but whose body is not in the supported visual Polars subset.
_Avoid_: Invalid transformation, hidden node

**Reconciliation**:
The process of loading a changed Workflow definition in an isolated worker, deriving its declarations and dependency metadata, parsing its Transformation bodies, and synchronizing its supported graph representation, diagnostics, and Preview with the client. Module setup is executed but remains outside the graph and structural-editing boundary.
_Avoid_: Code generation, file sync

**Preview**:
A bounded execution of a selected Workflow node against sample data that exposes its resulting schema, rows, and diagnostics for auditing authored transformations.
_Avoid_: Production run, job execution

**Diagnostic**:
A non-destructive report from parsing, Polars schema planning, or Preview execution that describes the current state of a Workflow definition.
_Avoid_: Validation error, warning

**Sample data**:
The deliberately limited local Parquet input supplied to a Preview in place of, or as a safe subset of, a Workflow source's production input.
_Avoid_: Fixture, production data

**Source**:
A named Managed node that supplies a Polars lazy frame to a Workflow. A Preview binds each Source independently to local Parquet Sample data.
_Avoid_: Input, dataset

**Output**:
A named declaration of a final Workflow lazy frame for previewing and downstream composition. It does not itself write data to an external destination.
_Avoid_: Sink, export

**Workspace**:
A local directory explicitly configured for Artio authoring, containing registered Workflow definitions and their Preview bindings.
_Avoid_: Repository, project
