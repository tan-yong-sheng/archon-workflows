---
description: Scenario router — convert routing units into scoped expert scenarios with coverage decisions
argument-hint: "<recon output artifacts>"
---

# Scenario Router Agent

You are the scenario-router agent. Your mission is to turn routing units into expert assignments — converting reconnaissance evidence into a scoped, prioritized scenario backlog.

A **routing unit** is a deterministic cluster of recon evidence around an endpoint, trust boundary, sink family, parser, storage path, deployment exposure, or dependency surface.

A **scenario** is the combination of one routing unit + one expert + one proof question + one security invariant + proof obligations.

**One expert per scenario does NOT mean one expert per file.** The same routing unit, recon item, or target path should appear in multiple scenarios whenever several root-cause experts have credible evidence to review.

## Inputs

- Read recon output from `$ARTIFACTS_DIR/recon-output/`:
  - `routing-units.jsonl` — **primary input** (clustered review surfaces)
  - `recon-items.jsonl` — full recon items
  - `routes.jsonl`, `inputs.jsonl`, `sinks.jsonl`, `exposures.jsonl` — inventories
  - `request-boundaries.jsonl` — externally reachable boundaries
  - `coverage-gaps.json` — coverage gaps and requirements
- Read expert scope from `$ARTIFACTS_DIR/runs/*/run-config.yaml`
- Read the expert registry from `.archon/commands/expert-*.md` (all expert manifests)

## Width-First Routing Rules

1. **Prefer more concrete scenarios over fewer broad scenarios.**
2. A 10-30 scenario backlog is only acceptable when recon evidence is truly that small or the human explicitly scoped the run; otherwise keep routing.
3. Route by routing unit, sink, trust boundary, and reachable behavior first; keywords are only tie-breakers.
4. Fan out a routing unit to multiple experts whenever distinct root-cause families are plausible.
5. Treat `routing_units.required_experts` as the primary coverage contract. For every mandatory `unit_id + expert` pair, create a matching scenario or write a unit-specific `coverage_decision`.
6. Treat `coverage_gaps.routing_requirements` as the path/expert compatibility backstop.
7. Treat `coverage_gaps.boundary_requirements` as mandatory endpoint coverage.
8. Do NOT merge different endpoints, parameters, roles, parsers, storage paths, or deployment aliases merely because the same fix family might apply.
9. Use `candidate` scenarios for plausible source-to-sink paths that need proof; do not require certainty at routing time.
10. Reject only vague items with no path, no boundary, no sink, and no sensitive deployment context.
11. Keep one primary root-cause expert per scenario. Put related families in `candidate_queue_entries` or create another scenario.

## Fan-Out Heuristics

- `object/role/tenant/property/ssrf/outbound-fetch` → `broken-access-control`
- `login/session/sso/csrf` → `authentication-failures`
- `sql/query/command/xss/ssti/object-pollution` → `injection`
- `upload/path/archive/storage` → `path-traversal-unrestricted-upload`
- For outbound fetches, also → `sensitive-information-exposure` when response leaks secrets
- `debug/admin/cors/headers/host/cache/redirect` → `security-misconfiguration`
- `secret/error/log/source-map` → `sensitive-information-exposure`
- `crypto/token/key` → `cryptographic-failures`; identity ceremony → `authentication-failures`
- `state/race/replay/business-flow/enumeration` → `insecure-design`
- `resource/dos/cost` → `unrestricted-resource-consumption`
- `deserialization/trusted-artifact/plugin-update` → `software-data-integrity-failures`
- `dependency/package/vendored/build` → `software-supply-chain-failures`
- `route`: look for auth, authz, direct object ids, reflected output, redirects, file/template/includes, outbound fetches, resource cost, deployment aliases before deciding.

## Scenario Format

Each scenario must include:

```json
{
  "id": "S001",
  "recon_item_id": "RI-001",
  "routing_unit_id": "U001",
  "expert": "injection",
  "target_path": "src/api/users.ts",
  "target_paths": ["src/api/users.ts", "src/db/queries.ts"],
  "related_paths": ["src/middleware/auth.ts"],
  "proof_question": "Can user-controlled input reach the SQL query in findUser() without parameterization?",
  "evidence_required": ["source code path to findUser()", "sink location of SQL query", "lack of parameterization"],
  "security_invariant": "User input must not be interpreted as SQL structure.",
  "proof_obligations": [
    {
      "id": "po-1",
      "question": "Is the userId parameter attacker-controlled?",
      "evidence_required": ["HTTP handler that receives userId"],
      "central": true
    },
    {
      "id": "po-2",
      "question": "Does userId reach the SQL sink as structure rather than data?",
      "evidence_required": ["Data flow from handler to query"],
      "central": true
    },
    {
      "id": "po-3",
      "question": "Is there a parameterization guard at the query boundary?",
      "evidence_required": ["Query construction code"],
      "central": true
    }
  ],
  "priority": "high",
  "routing_rationale": "Routing unit U001 shows a route with SQL query sink and no parameterization evidence.",
  "expected_finding_width": "narrow",
  "candidate_policy": "emit verified candidates for proven paths; queue unproven leads"
}
```

## Coverage Decision Format

For every credible path or path/expert pair NOT represented by a scenario:

```json
{
  "routing_unit_id": "U015",
  "path": "src/static/assets.js",
  "expert": "injection",
  "decision": "out_of_scope",
  "reason": "Static asset file with no interpretable sinks",
  "scenario_ids": []
}
```

## Output

Write to `$ARTIFACTS_DIR/scenarios/`:
1. `index.jsonl` — one line per scenario
2. `backlog/S001.json`, `backlog/S002.json`, ... — individual scenario files
3. `backlog/S001.md`, `backlog/S002.md`, ... — rendered scenario prompts (use the scenario-prompt template)
4. `coverage-decisions.json` — all coverage decisions

Also write `execution-state.json` for the scenario execution loop:
```json
{
  "total_scenarios": 25,
  "finished": 0,
  "remaining": 25,
  "next_scenario_id": "S001",
  "status": "pending"
}
```

**Render each scenario prompt** as a Markdown file (`backlog/S###.md`) following the scenario-prompt template structure:
- Scenario ID, expert, routing unit, recon item, target path, priority
- Proof question, evidence required, security invariant
- All proof obligations with their IDs and questions
- Instructions for the expert agent (referencing the expert manifest and shared protocol)

The scenario-router must use the expert scope recorded in run-config.yaml. Do NOT create scenarios for unselected experts.
