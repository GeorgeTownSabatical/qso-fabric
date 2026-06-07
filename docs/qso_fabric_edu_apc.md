# QSO Fabric EDU: APC Development Workflow

This document maps the APC educational toolchain to the ten high-impact
outcomes requested for community benefit.

Status reminder:
- APC outputs are explicitly speculative and non-validated.

## Tool Surface

- `qso.edu.apc.bootstrap`
- `qso.edu.apc.runs`
- `qso.edu.apc.audit`
- `qso.edu.apc.resources`
- resource URI: `qso://edu/apc`
- CLI: `qso-edu-apc-bootstrap`

## Ten Outcomes -> Implementation

1. Reproducible theory audits:
   - `qso.edu.apc.audit` or `qso.edu.apc.bootstrap`
   - audit artifacts in run folder (`audit/reproducible_audit.*`)

2. Public speculative checklist template:
   - `qso.edu.apc.resources`
   - `checklist_template` field and `templates/speculative_model_checklist.md`

3. Open falsifiability scorecards:
   - `qso.edu.apc.resources`
   - `scorecard_template` and `templates/falsifiability_scorecard.json`

4. Teaching pipeline (axioms -> equations -> checks -> predictions):
   - `qso.edu.apc.resources`
   - `teaching_pipeline` and `curriculum/teaching_pipeline.*`

5. Crowdsourced parameter sweeps:
   - `qso.edu.apc.bootstrap`
   - `crowd/crowdsweep_pack.json` + `crowd/crowdsweep_instructions.md`

6. Apples-to-apples model comparison harness:
   - `qso.edu.apc.bootstrap` with `baseline_models`
   - `comparison/model_comparison.*`

7. Shared artifact library:
   - generated in each run: `library/artifact_library_index.json`

8. Misinformation-risk controls:
   - `controls/misinformation_controls.*`
   - mandatory speculative banner + blocked/allowed phrase policy

9. General scientific-method framework (beyond physics):
   - `framework/scientific_method_framework.*`
   - set `domain` input in `qso.edu.apc.bootstrap`

10. Community red-team reviews:
   - `red_team/red_team_pack.json`
   - `red_team/red_team_template.md`

11. Bayesian model comparison (automatic in every bootstrap run):
   - `validation/apc_bayes_comparison_latest.json`
   - `validation/apc_bayes_comparison_latest.md`
   - Includes prior-sensitivity matrix + robustness band across APC prior families.

## JSON-RPC Example

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"qso.create_sandbox","arguments":{"session_token":"apc-demo"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"qso.edu.apc.bootstrap","arguments":{"sandbox_id":"<sandbox_id>","mode":"exhaustive","domain":"physics","baseline_models":["LambdaCDM+SM","Toy-EFT"],"owner":"community"}}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"qso.edu.apc.runs","arguments":{"sandbox_id":"<sandbox_id>"}}}
{"jsonrpc":"2.0","id":4,"method":"resources/read","params":{"uri":"qso://edu/apc","arguments":{}}}
```

## Artifact Path Pattern

Artifacts are generated under:

`.codex/state/mcp_qso_edu/apc_fabric_edu/<sandbox_id>/runs/run_<timestamp>_<mode>_<suffix>/`

## CLI Example

```bash
qso-edu-apc-bootstrap \
  --session-token apc-community \
  --mode exhaustive \
  --domain physics \
  --baseline-models-csv "LambdaCDM+SM,Toy-EFT,Phase-Only Baseline" \
  --publish-dir .codex/state/mcp_qso_edu/apc_published \
  --json-output .codex/state/mcp_qso_edu/apc_last_run.json
```

## On-Demand CI

- Workflow file: `.github/workflows/apc-edu-bundle.yml`
- Trigger manually with `workflow_dispatch`.
- Workflow uploads the generated bundle via `actions/upload-artifact`.
