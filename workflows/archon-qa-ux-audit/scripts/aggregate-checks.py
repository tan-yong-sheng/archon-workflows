#!/usr/bin/env python3
"""
Aggregate Deterministic Check Results

Combines results from all rule-based check scripts into a single
aggregate JSON file. This is the input for the AI judge step.

Deterministic — no AI. Just JSON merging and counting.
"""

import json
import os
import sys
from pathlib import Path


def aggregate_results(artifacts_dir):
    """Combine all check category results into one aggregate file."""
    checks_dir = os.path.join(artifacts_dir, "checks")

    categories = ["axe-core", "heuristic", "ai-slop", "usability"]
    all_findings = []
    total_pass = 0
    total_fail = 0
    category_summaries = {}

    for category in categories:
        results_path = os.path.join(checks_dir, category, "results.json")
        if not os.path.exists(results_path):
            category_summaries[category] = {
                "status": "missing",
                "findings": [],
                "pass_count": 0,
                "fail_count": 0
            }
            continue

        try:
            data = json.loads(Path(results_path).read_text())
        except (json.JSONDecodeError, Exception) as e:
            category_summaries[category] = {
                "status": f"error: {str(e)}",
                "findings": [],
                "pass_count": 0,
                "fail_count": 0
            }
            continue

        # Handle axe-core format (array of page results)
        if category == "axe-core":
            if isinstance(data, dict) and "error" in data:
                category_summaries[category] = {
                    "status": f"error: {data['error']}",
                    "findings": [],
                    "pass_count": 0,
                    "fail_count": 0
                }
                continue

            # Convert axe-core violations to our finding format
            axe_findings = []
            for page_result in data if isinstance(data, list) else []:
                if not isinstance(page_result, dict) or "error" in page_result:
                    continue
                url = page_result.get("url", "")
                for violation in page_result.get("violations", []):
                    axe_findings.append({
                        "id": f"AXE-{len(axe_findings)+1:03d}",
                        "check": f"accessibility/axe-core/{violation.get('id', 'unknown')}",
                        "verdict": "fail",
                        "severity": "critical" if violation.get("impact") == "critical" else
                                    "major" if violation.get("impact") in ("serious", "moderate") else "minor",
                        "band": "ux",
                        "subtype": "act",
                        "title": violation.get("description", "Accessibility violation"),
                        "description": f"{violation.get('description', '')} — {violation.get('helpUrl', '')}",
                        "source": f"axe-core: {violation.get('id', '')} (WCAG)",
                        "needs_judgment": False,
                        "remediation": f"See {violation.get('helpUrl', 'axe-core documentation')} for fix guidance",
                        "pages_affected": [url],
                        "affected_nodes": violation.get("nodes", [])[:5]  # Cap at 5 examples
                    })

            all_findings.extend(axe_findings)
            category_summaries[category] = {
                "status": "ok",
                "findings": axe_findings,
                "pass_count": len(data) if isinstance(data, list) else 0,
                "fail_count": len(axe_findings)
            }
        else:
            # Standard format from our Python scripts
            findings = data.get("findings", [])
            all_findings.extend(findings)
            pass_count = data.get("pass_count", 0)
            fail_count = data.get("fail_count", 0)
            category_summaries[category] = {
                "status": "ok",
                "findings": findings,
                "pass_count": pass_count,
                "fail_count": fail_count
            }

        total_pass += category_summaries[category].get("pass_count", 0)
        total_fail += category_summaries[category].get("fail_count", 0)

    # Build aggregate
    aggregate = {
        "total_findings": len(all_findings),
        "pass_count": total_pass,
        "fail_count": total_fail,
        "by_severity": {
            "critical": sum(1 for f in all_findings if f.get("severity") == "critical"),
            "major": sum(1 for f in all_findings if f.get("severity") == "major"),
            "minor": sum(1 for f in all_findings if f.get("severity") == "minor")
        },
        "by_band": {
            "ux": sum(1 for f in all_findings if f.get("band") == "ux"),
            "ui-risk": sum(1 for f in all_findings if f.get("band") == "ui-risk")
        },
        "by_category": category_summaries,
        "findings_needing_judgment": [f for f in all_findings if f.get("needs_judgment", False)],
        "findings_auto_confirmed": [f for f in all_findings if not f.get("needs_judgment", False)],
        "all_findings": all_findings
    }

    # Write aggregate
    output_path = os.path.join(checks_dir, "aggregate-results.json")
    with open(output_path, "w") as f:
        json.dump(aggregate, f, indent=2, default=str)

    # Print summary for node output
    nj = len(aggregate["findings_needing_judgment"])
    ac = len(aggregate["findings_auto_confirmed"])
    print(f"Aggregate: {aggregate['total_findings']} total findings ({ac} auto-confirmed, {nj} need AI judgment)")
    print(f"Severity: {aggregate['by_severity']['critical']} critical, {aggregate['by_severity']['major']} major, {aggregate['by_severity']['minor']} minor")


if __name__ == "__main__":
    artifacts_dir = os.environ.get("ARTIFACTS_DIR", sys.argv[1] if len(sys.argv) > 1 else "artifacts")
    aggregate_results(artifacts_dir)
