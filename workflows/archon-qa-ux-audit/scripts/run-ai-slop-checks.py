#!/usr/bin/env python3
"""
AI-Slop Detection — Fingerprints of AI-generated UI (rule-based)

Detects common patterns that indicate AI-generated UI code:
- Purple gradients / default Tailwind color palette
- Generic card shadows / border-radius
- "Coming soon" stubs / lorem ipsum / placeholder data
- Emoji as icons / sparkle + AI combo
- Default taglines / hero button clichés / marketing buzzwords
- Shadcn signature patterns
- Stock illustration hotlinks

Sources:
- NN/g "AI Prototyping in Real Design Contexts" (2025)
- Krug: Don't Make Me Think (Law #3 — omit needless words)

These are deterministic pattern-matching checks. Self-evident anti-patterns
(lorem ipsum, "Coming soon") don't need AI judgment. Aesthetic judgments
(purple gradients, generic shadows) are flagged needs_judgment=true.
"""

import json
import os
import re
import sys
from pathlib import Path


# ── Pattern Definitions ──────────────────────────────────────────────────

AI_SLOP_PATTERNS = {
    "lorem-ipsum-data": {
        "regex": [
            r"lorem\s+ipsum",
            r"Lorem\s+Ipsum",
            r"loremipsum",
            r"dolor\s+sit\s+amet",
        ],
        "severity": "critical",
        "band": "ui-risk",
        "subtype": None,
        "title": "Lorem ipsum placeholder text detected",
        "source": None,  # self-evident anti-pattern — no citation needed
        "needs_judgment": False,
        "remediation": "Replace all lorem ipsum text with real content relevant to the application"
    },
    "placeholder-names": {
        "regex": [
            r"\bJohn\s+Doe\b",
            r"\bJane\s+Doe\b",
            r"\bJohn\s+Smith\b",
            r"\bAlice\s+Johnson\b",
            r"\bBob\s+Smith\b",
            r"placeholder.*name",
            r"Test\s+User",
            r"Demo\s+User",
        ],
        "severity": "major",
        "band": "ui-risk",
        "subtype": None,
        "title": "Placeholder names detected",
        "source": None,  # self-evident anti-pattern
        "needs_judgment": False,
        "remediation": "Replace placeholder names with realistic example data"
    },
    "coming-soon-text": {
        "regex": [
            r"Coming\s+Soon",
            r"coming\s+soon",
            r"Stay\s+Tuned",
            r"Under\s+Construction",
            r"Work\s+in\s+Progress",
        ],
        "severity": "major",
        "band": "ui-risk",
        "subtype": None,
        "title": "'Coming Soon' stub text detected",
        "source": "Krug Law #3 (Omit needless words) — 'Coming soon' adds no value to users",
        "needs_judgment": False,
        "remediation": "Remove 'Coming Soon' text; either ship the feature or remove the UI element entirely"
    },
    "purple-gradient": {
        "regex": [
            r"background.*linear-gradient.*purple",
            r"bg-gradient.*purple",
            r"from-purple.*to-",
            r"from-violet.*to-",
            r"#7c3aed",      # Tailwind violet-600
            r"#8b5cf6",      # Tailwind violet-500
            r"#a855f7",      # Tailwind purple-500
            r"linear-gradient.*#[89abcdef][0-9a-f]{5}6",
        ],
        "severity": "minor",
        "band": "ui-risk",
        "subtype": None,
        "title": "Purple/violet gradient detected (AI default signature)",
        "source": "NN/g AI Prototyping — 'All outputs share a similar, generic look'",
        "needs_judgment": True,
        "remediation": "Replace with brand-appropriate colors. If purple is intentional, use a custom shade rather than Tailwind defaults"
    },
    "default-tailwind-palette": {
        "regex": [
            r"bg-blue-500",
            r"bg-indigo-500",
            r"bg-purple-500",
            r"bg-violet-500",
            r"text-gray-500",
            r"border-gray-200",
        ],
        "severity": "minor",
        "band": "ui-risk",
        "subtype": None,
        "title": "Default Tailwind color palette detected",
        "source": "NN/g AI Prototyping — 'AI tools default to Shadcn components and Tailwind CSS because those dominate their training data'",
        "needs_judgment": True,
        "remediation": "Customize the color palette to match the brand. Extend tailwind.config with brand colors"
    },
    "generic-card-shadow": {
        "regex": [
            r"shadow-lg",
            r"shadow-xl",
            r"shadow-2xl",
            r"rounded-xl",
            r"rounded-2xl",
        ],
        "severity": "minor",
        "band": "ui-risk",
        "subtype": None,
        "title": "Generic card shadow/border-radius pattern",
        "source": "NN/g AI Prototyping — documented 'inconsistent spacing and margins, no distinctive visual language'",
        "needs_judgment": True,
        "remediation": "Use intentional shadow/elevation system rather than default Tailwind shadow utilities"
    },
    "emoji-as-icon": {
        "regex": [
            r"<button[^>]*>[🚀🎯✨💡🎉🔍📊🛡️⚡🔥🌟💬📱🏠⚙️📝🎨🧪🛒💰📧🔒✅❌⚠️🎉🔔📋]",
            r"<span[^>]*>[🚀🎯✨💡🎉🔍📊]",
            r"aria-label=\"[^\"]*[🚀🎯✨💡🎉]",
        ],
        "severity": "minor",
        "band": "ui-risk",
        "subtype": None,
        "title": "Emoji used as UI icon",
        "source": "Apple HIG (Icons) + NN/g Icon Usability — 'emoji cannot be color-controlled, cannot scale crisply, and render differently across platforms'",
        "needs_judgment": True,
        "remediation": "Replace emoji icons with SVG icons (e.g., Heroicons, Lucide) that are color-controllable and render consistently"
    },
    "default-tagline": {
        "regex": [
            r"Empower\s+Your",
            r"Transform\s+Your",
            r"Revolutionize\s+Your",
            r"Streamline\s+Your",
            r"Unlock\s+Your",
            r"Elevate\s+Your",
            r"Next-Gen(?:eration)?\s",
            r"All-in-One\s+Platform",
            r"Build\s+Better\s+Faster",
            r"The\s+Future\s+of\s+\w+",
        ],
        "severity": "minor",
        "band": "ui-risk",
        "subtype": None,
        "title": "Generic AI-generated tagline detected",
        "source": "NN/g Microcontent (Nielsen 1998) + Krug Law #3",
        "needs_judgment": True,
        "remediation": "Replace with a specific, concrete description of what the product does for the user"
    },
    "hero-button-cliche": {
        "regex": [
            r"Get\s+Started\s*(?:Free|Today)?",
            r"Start\s+(?:Your\s+)?Free\s+Trial",
            r"Try\s+It\s+Free",
            r"Sign\s+Up\s+Free",
        ],
        "severity": "minor",
        "band": "ui-risk",
        "subtype": None,
        "title": "Cliché hero CTA text",
        "source": "NN/g Microcontent (Nielsen 1998) + Krug Law #2 (Mindless clicks)",
        "needs_judgment": True,
        "remediation": "Use a CTA that describes the first action, e.g., 'Create your first project' instead of 'Get Started'"
    },
    "shadcn-signature": {
        "regex": [
            r"shadcn",
            r"@/components/ui/",
            r"cmdk",
            r"class=\s*\"[^\"]*border-input[^\"]*bg-background",
        ],
        "severity": "minor",
        "band": "ui-risk",
        "subtype": None,
        "title": "Shadcn/UI signature pattern detected",
        "source": "NN/g AI Prototyping — 'AI tools default to Shadcn components'",
        "needs_judgment": True,
        "remediation": "Customize Shadcn theme with brand tokens; the default theme is recognizable as AI-generated"
    },
    "generic-font-stack": {
        "regex": [
            r"font-family.*Inter",
            r"font-family.*system-ui",
            r"font-sans\b",
        ],
        "severity": "minor",
        "band": "ui-risk",
        "subtype": None,
        "title": "Generic font stack (Inter/system-ui)",
        "source": "NN/g AI Prototyping — 'sans-serif typeface, minimalist styling, flat and interchangeable appearance'",
        "needs_judgment": True,
        "remediation": "Choose a distinctive typeface that reflects the brand personality"
    }
}


def run_ai_slop_checks(captures_dir):
    """Run all AI-slop pattern checks against captured pages."""
    pages_manifest = Path(captures_dir) / "pages.json"
    if not pages_manifest.exists():
        return {"error": "No pages.json found", "findings": [], "pass_count": 0, "fail_count": 0}

    pages = json.loads(pages_manifest.read_text())
    all_findings = []

    for page in pages:
        html_path = Path(captures_dir) / page.get("html", "")
        if not html_path.exists():
            continue

        html_content = html_path.read_text(errors="replace")

        for check_id, check_def in AI_SLOP_PATTERNS.items():
            matches = []
            for pattern in check_def["regex"]:
                found = re.findall(pattern, html_content, re.IGNORECASE)
                if found:
                    matches.extend(found)

            if matches:
                all_findings.append({
                    "id": f"AISLOP-{len(all_findings)+1:03d}",
                    "check": f"ai-slop/{check_id}",
                    "verdict": "fail",
                    "severity": check_def["severity"],
                    "band": check_def["band"],
                    "subtype": check_def["subtype"],
                    "title": check_def["title"],
                    "description": f"Pattern '{check_id}' detected {len(matches)} time(s) on {page['url']}. Matches: {matches[:3]}",
                    "source": check_def["source"] or "Self-evident anti-pattern (no citation needed)",
                    "needs_judgment": check_def["needs_judgment"],
                    "remediation": check_def["remediation"],
                    "pages_affected": [page["url"]]
                })

    # Deduplicate: merge same-check findings across pages
    merged = {}
    for f in all_findings:
        key = f["check"]
        if key in merged:
            merged[key]["pages_affected"].extend(f["pages_affected"])
            merged[key]["description"] = f"Pattern detected on {len(merged[key]['pages_affected'])} page(s)"
        else:
            merged[key] = f

    unique_findings = list(merged.values())
    total_checks = len(AI_SLOP_PATTERNS) * len(pages)
    fail_count = len(unique_findings)
    pass_count = total_checks - fail_count

    return {
        "findings": unique_findings,
        "pass_count": max(0, pass_count),
        "fail_count": fail_count,
        "checks_run": list(AI_SLOP_PATTERNS.keys())
    }


if __name__ == "__main__":
    artifacts_dir = os.environ.get("ARTIFACTS_DIR", sys.argv[1] if len(sys.argv) > 1 else "artifacts")
    captures_dir = os.path.join(artifacts_dir, "captures")

    results = run_ai_slop_checks(captures_dir)

    output_dir = os.path.join(artifacts_dir, "checks", "ai-slop")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "results.json")

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"AI-slop checks: {results['fail_count']} findings across {len(results.get('checks_run', []))} pattern checks")
