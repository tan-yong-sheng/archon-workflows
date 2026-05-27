#!/usr/bin/env python3
"""Scan finished scenario results, extract finding candidates, and create the triage backlog."""
import json
import sys
import os
from pathlib import Path


def main():
    workspace = os.environ.get("ARTIFACTS_DIR", ".")
    candidates_dir = Path(workspace) / "finding-candidates"
    triage_dir = Path(workspace) / "finding-triage"

    candidates_dir.mkdir(parents=True, exist_ok=True)
    (triage_dir / "prompts").mkdir(parents=True, exist_ok=True)
    (triage_dir / "decisions").mkdir(parents=True, exist_ok=True)

    finished_dir = Path(workspace) / "scenarios" / "finished"
    candidate_count = 0
    candidate_ids = []

    if finished_dir.exists():
        for result_file in sorted(finished_dir.glob("S*.json")):
            try:
                with open(result_file) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            scenario_id = result_file.stem
            findings = data.get("findings", [])

            for i, finding in enumerate(findings):
                candidate_id = f"{scenario_id}-F{i + 1:03d}"
                candidate = {
                    "candidate_id": candidate_id,
                    "scenario_id": scenario_id,
                    "source_result": scenario_id,
                    "expert": data.get("expert", "unknown"),
                    "status": "pending_triage",
                    "finding": finding,
                }

                candidate_path = candidates_dir / f"{candidate_id}.json"
                with open(candidate_path, "w") as cf:
                    json.dump(candidate, cf, indent=2)

                candidate_ids.append(candidate_id)
                candidate_count += 1

    # Write triage state
    triage_state = {
        "total_candidates": candidate_count,
        "triaged": 0,
        "remaining": candidate_count,
        "next_candidate_id": candidate_ids[0] if candidate_ids else None,
        "status": "pending" if candidate_count > 0 else "no_candidates",
        "candidate_ids": candidate_ids,
    }

    with open(triage_dir / "triage-state.json", "w") as f:
        json.dump(triage_state, f, indent=2)

    # Log event
    logs_dir = Path(workspace) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone

    event = {
        "event": "create_candidate_backlog",
        "total_candidates": candidate_count,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(logs_dir / "events.jsonl", "a") as f:
        f.write(json.dumps(event) + "\n")

    print(f"Created {candidate_count} finding candidates for triage")


if __name__ == "__main__":
    main()
