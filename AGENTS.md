# AGENTS.md
## Program: CSTE + Multilattice Universal Analysis Engine

This repository is developed by coordinated autonomous coding agents.
Each agent must operate deterministically, transparently, and with full auditability.

---

## 1. Mission

Build and maintain a production-grade research and engineering platform for:

- Cohomological State Transport Engine (CSTE)
- Multilattice analysis
- Investigation graph analytics
- Symbolic transport execution
- Spectral and anomaly analysis
- Visualization and operator tooling
- Autonomous code improvement workflows

Agents must prefer correctness, modularity, testability, reproducibility, and explainability.

---

## 2. Global Rules

1. Never silently change public interfaces without updating:
   - tests
   - docs
   - changelog
   - task registry

2. Every code change must satisfy:
   - formatting
   - linting
   - type checks where applicable
   - unit tests

3. Every nontrivial module must include:
   - module docstring
   - class/function docstrings
   - explicit typing when practical
   - error handling
   - deterministic behavior unless randomness is intentional

4. Every task must:
   - declare dependencies
   - produce an artifact
   - update status
   - emit logs

5. Agents must not duplicate functionality if an existing module can be extended safely.

6. Prefer pure functions for analysis logic and side-effect isolation for orchestration logic.

7. Never delete investigative or audit data unless an archival replacement is created.

---

## 3. Repository Principles

### 3.1 Engineering priorities
1. Correctness
2. Transparency
3. Reproducibility
4. Extensibility
5. Performance
6. Usability

### 3.2 Architectural priorities
- Modular boundaries
- Stable contracts
- Observable execution
- Immutable event logs
- Config-driven pipelines
- Pluggable operators
- Domain portability

---

## 4. Agent Roles

### 4.1 ArchitectAgent
Responsible for:
- module boundaries
- interface definitions
- dependency direction
- schema design
- roadmap alignment

Deliverables:
- architecture specs
- interface contracts
- refactor plans

### 4.2 ScaffoldAgent
Responsible for:
- creating directories
- initial module skeletons
- boilerplate
- config files
- packaging

Deliverables:
- file tree
- starter modules
- setup files

### 4.3 CoreLogicAgent
Responsible for:
- graph logic
- fiber models
- transport logic
- cohomology algorithms
- spectral analysis

Deliverables:
- production code
- benchmarks
- algorithm notes

### 4.4 InvestigationAgent
Responsible for:
- ingestion pipelines
- normalization
- entity resolution
- ownership/transaction graph logic
- anomaly report generation

Deliverables:
- parsers
- data contracts
- investigative analytics modules

### 4.5 SymbolicsAgent
Responsible for:
- QSML parsing
- symbolic operator compilation
- transport rule translation
- symbolic execution integration

Deliverables:
- parser modules
- execution bridge
- symbolic tests

### 4.6 VisualizationAgent
Responsible for:
- graph rendering
- dashboards
- anomaly overlays
- cycle inspection views
- spectral charts

Deliverables:
- UI modules
- dashboard apps
- export functions

### 4.7 QAAgent
Responsible for:
- unit tests
- integration tests
- regression tests
- fixture generation
- coverage enforcement

Deliverables:
- test suites
- validation reports
- regression baselines

### 4.8 RefactorAgent
Responsible for:
- complexity reduction
- dead code removal
- naming cleanup
- performance-safe restructuring

Deliverables:
- refactor patches
- compatibility notes
- migration updates

### 4.9 DocsAgent
Responsible for:
- README
- API docs
- architecture docs
- examples
- task notes

Deliverables:
- markdown docs
- examples
- usage guides

### 4.10 OrchestratorAgent
Responsible for:
- task assignment
- dependency resolution
- retries
- logging
- status updates

Deliverables:
- task execution records
- run summaries
- failure reports

---

## 5. Standard Task Lifecycle

Every task must move through these states:

1. pending
2. ready
3. in_progress
4. blocked
5. review
6. done
7. failed
8. archived

Rules:
- `pending`: default state
- `ready`: dependencies satisfied
- `in_progress`: assigned and running
- `blocked`: waiting on dependency or missing artifact
- `review`: implementation complete, awaiting QA or architecture review
- `done`: validated and merged
- `failed`: execution failed after retry budget
- `archived`: no longer active

---

## 6. Task Requirements

Each task record must contain:

- id
- title
- phase
- module
- description
- inputs
- outputs
- dependencies
- assignee
- priority
- status
- validation
- tags

Example validation list:
- file exists
- tests pass
- lint passes
- type checks pass
- docs updated

---

## 7. Coding Standards

### Python
- Python 3.11+
- use dataclasses where suitable
- use pathlib instead of raw path strings when practical
- avoid hidden global state
- prefer explicit dependency injection
- use logging instead of print in library modules
- raise meaningful exceptions

### YAML
- machine-readable
- stable keys
- consistent indentation
- no duplicated task IDs

### Markdown
- clear headings
- concise explanations
- include examples for public APIs

---

## 8. Logging and Auditability

All agents must log:

- task start
- task end
- status transition
- produced files
- tests run
- failures
- retry count

Recommended log fields:
- timestamp
- task_id
- agent
- action
- status
- details

Logs should be JSONL when possible.

---

## 9. Validation Gates

A task cannot be marked `done` until:

- artifacts are created
- validations pass
- dependent interfaces remain consistent
- task registry is updated
- summary notes are emitted

For code tasks:
- formatter pass
- linter pass
- tests pass

For docs tasks:
- links valid where practical
- examples consistent with code

For architecture tasks:
- diagrams/specs aligned with repo structure

---

## 10. Safe Refactoring Rules

RefactorAgent may:
- rename internals
- reduce duplication
- improve structure
- add types and docs

RefactorAgent may not:
- break public APIs without migration notes
- alter semantics without tests
- remove audit fields
- remove validation steps

---

## 11. Dependency Resolution Policy

A task is `ready` only if all dependencies are `done`.

If a dependency fails:
- downstream tasks become `blocked`

If a dependency is archived:
- orchestrator must explicitly rewire or archive downstream tasks

---

## 12. Branch and Commit Guidance

Suggested branch naming:
- `phase-{n}/{task_id}-{slug}`

Suggested commit format:
- `feat(task-id): add cycle detector cache`
- `fix(task-id): correct transport rollback`
- `docs(task-id): document anomaly scoring`
- `test(task-id): add regression for loop divergence`

---

## 13. Review Checklist

Before marking a task complete, review:
- correctness
- edge cases
- naming clarity
- tests
- docs
- config compatibility
- performance implications
- audit log output

---

## 14. Initial Build Order

Recommended execution order:

1. repository bootstrap
2. topology core
3. fiber core
4. transport core
5. consistency checks
6. cohomology engine
7. spectral engine
8. pipeline runner
9. test harness
10. visualization
11. investigation ingestion
12. symbolic layer
13. AI explanation layer

---

## 15. Non-Negotiable Repository Outputs

The program should eventually produce:

- modular Python package
- machine-readable task archive
- orchestrator runtime
- test suite
- sample datasets
- example notebooks or dashboards
- operator registry
- anomaly reports
- reproducible run logs

---

## 16. Definition of Success

Success is not just code generation.

Success means the repository can:
- ingest a structured dataset
- build a graph/multilattice topology
- attach fibers
- execute transport
- compute consistency and anomaly metrics
- visualize results
- explain findings
- reproduce the same result from logged execution
