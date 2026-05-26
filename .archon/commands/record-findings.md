---
description: Record final findings — write finding Markdown files and summary from triage decisions
argument-hint: "<triage output artifacts>"
---

# Record Findings Agent

You are the findings recorder. Your mission is to materialize final finding reports from accepted and downgraded triage decisions, and produce a comprehensive review summary.

## Inputs

- Read triage decisions from `$ARTIFACTS_DIR/finding-triage/decisions/`
- Read finding candidates from `$ARTIFACTS_DIR/finding-candidates/`
- Read existing findings from `$ARTIFACTS_DIR/findings/`
- Read scenario results from `$ARTIFACTS_DIR/scenarios/finished/`
- Read recon output from `$ARTIFACTS_DIR/recon-output/`
- Read run config from `$ARTIFACTS_DIR/runs/*/run-config.yaml`

## Process

1. **Read every triage decision** in `$ARTIFACTS_DIR/finding-triage/decisions/`
2. **For each `accepted` or `downgraded` decision**: Write the final finding Markdown to `$ARTIFACTS_DIR/findings/{candidate_id}.md`
3. **For `duplicate` decisions**: Ensure the original finding already exists in `$ARTIFACTS_DIR/findings/`
4. **For `rejected` or `needs_context` decisions**: Do NOT write a finding file
5. **Apply triage overrides**: Use the triage agent's `final_severity`, `severity_rationale`, and revised `finding` object (not the scenario expert's original)

## Finding Markdown Format

Each finding file must follow this template:

```markdown
# {title}

- **Severity**: {final_severity}
- **Severity rationale**: {severity_rationale}
- **Confidence**: {confidence}
- **Scenario**: {scenario_id}
- **Target path**: {target_path}
- **Attacker role**: {attacker_role}
- **Preconditions**: {preconditions}

## Non-Technical Summary

{non_technical_summary}

## Technical Summary

{summary}

## Attack Chain

{attack_chain}

## Example Attack

{example_attack}

## Evidence

{evidence}

## Impact Analysis

{impact_analysis}

## How An Attacker Could Use This

{attacker_use}

## Recommended Fix

{recommended_fix}

## Validation Notes

{validation_notes}

## Triage

- **Decision**: {decision}
- **Triage agent**: {triage_agent_id}
- **Original severity**: {original_severity}
- **Final severity**: {final_severity}
- **Evidence assessment**: {evidence_assessment}
```

## Review Summary

Write a comprehensive summary to `$ARTIFACTS_DIR/findings/SUMMARY.md`:

```markdown
# Security Review Summary

**Run ID**: {run_id}
**Target**: {repo_url}
**Commit**: {commit}
**Branch**: {branch}
**Review date**: {date}
**Expert scope**: {expert_scope}

## Overview

{2-3 paragraph executive summary of the review findings}

## Statistics

| Metric | Count |
|--------|-------|
| Recon items | {count} |
| Routing units | {count} |
| Scenarios executed | {count} |
| Scenarios verified | {count} |
| Scenarios rejected | {count} |
| Finding candidates | {count} |
| Accepted findings | {count} |
| Downgraded findings | {count} |
| Rejected candidates | {count} |

## Findings by Severity

### Critical
{list or "None"}

### High
{list or "None"}

### Medium
{list or "None"}

### Low
{list or "None"}

### Informational
{list or "None"}

## Findings by Expert Family

{per-expert breakdown}

## Coverage Notes

{Explain any coverage gaps, out-of-scope decisions, or areas needing deeper review}

## Artifact Trail

- Recon: `$ARTIFACTS_DIR/recon-output/`
- Scenarios: `$ARTIFACTS_DIR/scenarios/`
- Finding candidates: `$ARTIFACTS_DIR/finding-candidates/`
- Triage decisions: `$ARTIFACTS_DIR/finding-triage/decisions/`
- Final findings: `$ARTIFACTS_DIR/findings/`
- Event logs: `$ARTIFACTS_DIR/logs/events.jsonl`
```

## Final Step

Update the run state to reflect completion:
- Append `{"phase":"completed","timestamp":"..."}` to `$ARTIFACTS_DIR/runs/*/run-state.jsonl`
- Update the run-config.yaml status field to "completed"
