# Security Review Workflow

A source-guided whitebox security review (pentest) using scenario-first methodology with OWASP/MITRE-aligned expert families.

Methodology: 1-to-1 replication of Hadrian OpenHack's scenario-first review model.

## Workflow Diagram

```
                                    ┌─────────────────────┐
                                    │    PHASE 1: INIT    │
                                    │     init-run        │
                                    │                     │
                                    │ • Clone/isolate     │
                                    │ • Create workspace  │
                                    │ • Write run-config  │
                                    │ • Log initial state │
                                    └────────┬────────────┘
                                             │
                                             ▼
                                    ┌─────────────────────┐
                                    │  PHASE 2: EXPERT    │
                                    │  SCOPE SELECTION    │
                                    │  select-expert-scope│
                                    │                     │
                                    │ • Pick OWASP/MITRE  │
                                    │   expert families   │
                                    │ • All or subset     │
                                    └────────┬────────────┘
                                             │
                                             ▼
                              ┌──────────────────────────────┐
                              │     PHASE 3: SOURCE RECON    │
                              │         run-recon            │
                              │                              │
                              │  ┌─────────────────────────┐ │
                              │  │ Scan codebase surface   │ │
                              │  │ → recon-items.jsonl     │ │
                              │  │ → routing-units.jsonl   │ │
                              │  └─────────────────────────┘ │
                              └──────────────┬───────────────┘
                                             │
                                             ▼
                              ┌──────────────────────────────┐
                              │   PHASE 4: SCENARIO ROUTING  │
                              │       route-scenarios        │
                              │                              │
                              │  Recon items ──► Routing     │
                              │  units ──► Scoped scenarios  │
                              │  (1 expert + 1 proof Q      │
                              │   per scenario)              │
                              └──────────────┬───────────────┘
                                             │
                                             ▼
                              ┌──────────────────────────────┐
                              │  PHASE 5: HUMAN APPROVAL     │
                              │      approve-backlog         │  ◄── max 3 attempts
                              │                              │      on reject
                              │  Review scenario backlog     │
                              │  ✓ Expert assignment         │──── (re-route with
                              │  ✓ Proof questions           │     feedback)
                              │  ✓ Coverage decisions        │
                              └──────────────┬───────────────┘
                                             │ approved
                                             ▼
                 ┌──────────────────────────────────────────────────────┐
                 │           PHASE 6: SCENARIO EXECUTION                │
                 │            execute-scenarios (loop)                  │
                 │                                                      │
                 │  For each scenario in backlog:                       │
                 │  ┌──────────────────────────────────────────────┐   │
                 │  │  Subagent (fresh context per scenario)       │   │
                 │  │                                              │   │
                 │  │  1. Read scenario prompt + expert manifest   │   │
                 │  │  2. Map reachable entrypoint                 │   │
                 │  │  3. Trace attacker data: source → sink       │   │
                 │  │  4. Check guards at sink context             │   │
                 │  │  5. Decide: verified / candidate / rejected  │   │
                 │  │  6. Check sibling sinks (same root cause)    │   │
                 │  │  7. Write → scenarios/finished/{id}.json     │   │
                 │  └──────────────────────────────────────────────┘   │
                 │                                                      │
                 │  ┌─────┐  ┌─────┐  ┌─────┐       ┌─────┐           │
                 │  │ S1  │  │ S2  │  │ S3  │ ...   │ Sn  │           │
                 │  │sub- │  │sub- │  │sub- │       │sub- │           │
                 │  │agent│  │agent│  │agent│       │agent│           │
                 │  └──┬──┘  └──┬──┘  └──┬──┘       └──┬──┘           │
                 │     └────────┴────────┴─────┬──────┘               │
                 │                              ▼                      │
                 │               ALL_SCENARIOS_COMPLETE                 │
                 └──────────────────────────────┬───────────────────────┘
                                                │
                                                ▼
                              ┌──────────────────────────────┐
                              │  PHASE 7: CANDIDATE BACKLOG  │
                              │   create-candidate-backlog   │
                              │                              │
                              │  Collect candidate findings  │
                              │  from all finished scenarios │
                              │  → finding-candidates/*.json │
                              └──────────────┬───────────────┘
                                             │
                                             ▼
              ┌─────────────────────────────────────────────────────────┐
              │         PHASE 8: FINDING TRIAGE (loop)                  │
              │           triage-findings                               │
              │                                                         │
              │  For each finding candidate:                            │
              │  ┌───────────────────────────────────────────────────┐  │
              │  │  Independent Triage Agent (fresh context)        │  │
              │  │                                                  │  │
              │  │  1. Verify evidence quality & reachability       │  │
              │  │  2. Real vulnerability vs false positive?        │  │
              │  │  3. Deduplicate against existing findings        │  │
              │  │  4. Re-rate severity independently               │  │
              │  │  5. Assign confidence: high / medium / low       │  │
              │  │                                                  │  │
              │  │  Decision:                                       │  │
              │  │    ┌──────────┐  ┌──────────┐  ┌──────────┐    │  │
              │  │    │ accepted │  │downgraded│  │ rejected │    │  │
              │  │    └────┬─────┘  └────┬─────┘  └────┬─────┘    │  │
              │  │         │             │              │          │  │
              │  │         ▼             ▼              ▼          │  │
              │  │   → findings/   → findings/    (discarded)      │  │
              │  │     {id}.md      {id}.md                        │  │
              │  │                                                  │  │
              │  │  Also: duplicate / needs_context                 │  │
              │  └───────────────────────────────────────────────────┘  │
              │                                                         │
              │  ┌──────┐  ┌──────┐  ┌──────┐       ┌──────┐          │
              │  │ C1   │  │ C2   │  │ C3   │ ...   │ Cm   │          │
              │  │triage│  │triage│  │triage│       │triage│          │
              │  │agent │  │agent │  │agent │       │agent │          │
              │  └──┬───┘  └──┬───┘  └──┬───┘       └──┬───┘          │
              │     └─────────┴─────────┴─────┬──────┘               │
              │                                ▼                       │
              │               ALL_CANDIDATES_TRIAGED                    │
              └────────────────────────────────┬───────────────────────┘
                                               │
                                               ▼
                              ┌──────────────────────────────┐
                              │  PHASE 9: HUMAN APPROVAL     │
                              │      approve-findings        │  ◄── max 3 attempts
                              │                              │      on reject
                              │  Review triage decisions:    │──── (re-triage with
                              │  ✓ Accepted evidence strong  │     feedback)
                              │  ✓ Rejections justified      │
                              │  ✓ Severity not inflated     │
                              │  ✓ Duplicates correct        │
                              └──────────────┬───────────────┘
                                             │ approved
                                             ▼
                              ┌──────────────────────────────┐
                              │  PHASE 10: RECORD FINDINGS   │
                              │       record-findings        │
                              │                              │
                              │  Write final finding reports │
                              │  → findings/*.md             │
                              └──────────────┬───────────────┘
                                             │
                                             ▼
                              ┌──────────────────────────────┐
                              │  PHASE 11: VALIDATE RUN      │
                              │       validate-run           │
                              │                              │
                              │  Artifact counts:            │
                              │   recon → routing → backlog  │
                              │   → finished → candidates    │
                              │   → triage → findings        │
                              │                              │
                              │  Coverage checks:            │
                              │  ✓ All scenarios finished    │
                              │  ✓ All candidates triaged    │
                              │  ✓ Final findings consistent │
                              └──────────────────────────────┘
```

## The Durable Chain

Every artifact follows this chain — nothing bypasses a step:

```
 recon item ──► routing unit ──► scenario ──► scenario result ──► finding candidate ──► triage decision ──► finding
```

## Expert Families (OWASP/MITRE-Aligned)

| # | Expert ID | Title |
|---|-----------|-------|
| 1 | `broken-access-control` | A01:2025 — Broken Access Control |
| 2 | `security-misconfiguration` | A02:2025 — Security Misconfiguration |
| 3 | `software-supply-chain-failures` | A03:2025 — Software Supply Chain Failures |
| 4 | `cryptographic-failures` | A04:2025 — Cryptographic Failures |
| 5 | `injection` | A05:2025 — Injection |
| 6 | `memory-buffer-boundary-errors` | CWE-119 — Memory/Buffer Boundary Errors |
| 7 | `insecure-design` | A06:2025 — Insecure Design |
| 8 | `authentication-failures` | A07:2025 — Authentication Failures |
| 9 | `software-data-integrity-failures` | A08:2025 — Software/Data Integrity Failures |
| 10 | `sensitive-information-exposure` | CWE-200 — Sensitive Information Exposure |
| 11 | `path-traversal-unrestricted-upload` | CWE-22/CWE-434 — Path Traversal & Unrestricted Upload |
| 12 | `unrestricted-resource-consumption` | API4:2023/CWE-770 — Unrestricted Resource Consumption |

## Artifact Directory Layout

```
$ARTIFACTS_DIR/
├── run-config.yaml              # Review metadata & scope
├── run-state.jsonl              # Phase tracking
├── recon-output/
│   ├── recon-items.jsonl        # Phase 3: Codebase surface items
│   └── routing-units.jsonl      # Phase 3: Attack-surface routing units
├── scenarios/
│   ├── backlog/                 # Phase 4: Routed scenarios (S*.json)
│   ├── finished/                # Phase 6: Expert review results (S*.json)
│   └── execution-state.json     # Loop tracking for scenario execution
├── finding-candidates/          # Phase 7: Extracted candidates (S*-F*.json)
├── finding-triage/
│   ├── prompts/                 # Phase 8: Triage prompts
│   ├── decisions/               # Phase 8: Triage decisions (S*-F*.json)
│   └── triage-state.json        # Loop tracking for triage
├── findings/                    # Phase 10: Final reportable findings (*.md)
└── logs/
    └── events.jsonl             # Event log across all phases
```

## Human Checkpoints

| Phase | Gate | Max Retries | What's Reviewed |
|-------|------|-------------|-----------------|
| Phase 5 | `approve-backlog` | 3 | Scenario assignments, proof questions, coverage |
| Phase 9 | `approve-findings` | 3 | Triage decisions, severity ratings, rejections |

## Key Design Principles

- **Per-scenario subagent**: Each scenario is reviewed in an isolated, fresh-context subagent — no cross-contamination
- **Per-candidate triage**: Each finding candidate is independently triaged by its own agent — not the expert who proposed it
- **No self-graded findings**: Findings are admitted only through the recorded chain (recon → routing → scenario → candidate → triage → finding)
- **Severity re-rating**: Triage agents independently verify severity rather than accepting the scenario expert's rating
