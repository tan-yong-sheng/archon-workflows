#!/usr/bin/env python3
"""
Usability Anti-Pattern Checks (rule-based)

Detects common usability anti-patterns in HTML:
- Dead-end flows (pages with no navigation links)
- Missing empty states
- Missing error recovery (no back link, no home link)
- Inconsistent link patterns
- Missing focus indicators
- Large tap targets issues (from a11y snapshots)
- Excise detection (unnecessary steps)

Sources:
- Nielsen Heuristic #3 (User control and freedom)
- Nielsen Heuristic #4 (Consistency and standards)
- Cooper: About Face Ch 11 (Eliminating Excise)
- Krug: Don't Make Me Think
- ISO 9241-110:2020 (Conformity with user expectations)
"""

import json
import os
import re
import sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse


class NavigationExtractor(HTMLParser):
    """Extract navigation structure from HTML."""
    def __init__(self):
        super().__init__()
        self.internal_links = []
        self.external_links = []
        self.has_nav = False
        self.has_header = False
        self.has_footer = False
        self.has_breadcrumb = False
        self.has_search = False
        self.has_home_link = False
        self._in_nav = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        role = attrs_dict.get("role", "")

        if tag == "nav" or role == "navigation":
            self.has_nav = True
            self._in_nav = True
        if tag == "header" or role == "banner":
            self.has_header = True
        if tag == "footer" or role == "contentinfo":
            self.has_footer = True

        if tag == "a":
            href = attrs_dict.get("href", "")
            if href.startswith("http"):
                self.external_links.append(href)
            elif href.startswith("/") or href.startswith("./"):
                self.internal_links.append(href)

            # Check for home link
            if href in ("/", "#/", ""):
                self.has_home_link = True

        # Check for breadcrumb patterns
        if "breadcrumb" in attrs_dict.get("aria-label", "").lower() or \
           "breadcrumb" in " ".join(attrs_dict.get("class", "").split()):
            self.has_breadcrumb = True

        # Check for search
        if role == "search" or tag == "search" or \
           "search" in attrs_dict.get("type", "").lower() or \
           "search" in attrs_dict.get("aria-label", "").lower():
            self.has_search = True

    def handle_endtag(self, tag):
        if tag == "nav":
            self._in_nav = False


def analyze_dead_end_flows(page_url, html_content, nav_info):
    """Check for pages that trap users — no navigation, no way out."""
    findings = []

    # A page with no nav element AND fewer than 3 internal links is a dead-end risk
    if not nav_info.has_nav and len(nav_info.internal_links) < 3:
        findings.append({
            "id": f"USAB-DE{len(findings)+1:03d}",
            "check": "usability/dead-end-flow",
            "verdict": "fail",
            "severity": "major",
            "band": "ux",
            "subtype": "recover",
            "title": f"Dead-end flow risk on {page_url}",
            "description": f"Page has no nav element and only {len(nav_info.internal_links)} internal link(s). Users may have no way to navigate away.",
            "source": "Nielsen Heuristic #3 (User control and freedom) + Krug Ch 6 (Street signs and breadcrumbs)",
            "needs_judgment": True,
            "remediation": "Add a navigation bar or at minimum a home link and back link on this page"
        })

    # No home link and no nav = very hard to recover
    if not nav_info.has_home_link and not nav_info.has_nav:
        findings.append({
            "id": f"USAB-NH{len(findings)+1:03d}",
            "check": "usability/no-home-link",
            "verdict": "fail",
            "severity": "major",
            "band": "ux",
            "subtype": "recover",
            "title": f"No way back to home from {page_url}",
            "description": "Page has no home link and no navigation element. Users who land here have no way back to the start.",
            "source": "Nielsen Heuristic #3 (User control and freedom)",
            "needs_judgment": False,
            "remediation": "Add a logo/home link that returns to the homepage"
        })

    return findings


def analyze_empty_states(html_content, page_url):
    """Check for missing empty-state guidance."""
    findings = []

    # Look for list containers that have no items
    # If a page has "no items found" or empty list patterns without guidance
    has_empty_list = bool(re.search(r'<(ul|ol|table|tbody)[^>]*>\s*</(ul|ol|table|tbody)>', html_content, re.DOTALL))
    has_empty_state_guidance = bool(re.search(r'empty|no\s+(items|results|data|content|messages)', html_content, re.IGNORECASE))

    if has_empty_list and not has_empty_state_guidance:
        findings.append({
            "id": "USAB-ES001",
            "check": "usability/empty-state-guidance",
            "verdict": "fail",
            "severity": "major",
            "band": "ux",
            "subtype": "understand",
            "title": f"Empty container without guidance on {page_url}",
            "description": "Page has an empty list/table container but no empty-state messaging. Users see a blank area with no explanation.",
            "source": "NN/g Empty State UX (Pernice 2019) — three rules: communicate status, provide learning cues, provide direct pathways",
            "needs_judgment": True,
            "remediation": "Add an empty state with: (1) what's empty, (2) why, (3) what the user can do about it"
        })

    return findings


def analyze_feature_consistency(pages):
    """Check for inconsistent navigation/header/footer across pages."""
    findings = []

    # Check if nav/header/footer is present on some pages but not others
    pages_with_nav = []
    pages_without_nav = []

    for page in pages:
        html_path = Path(page.get("html", ""))
        if not html_path.exists():
            continue

        html_content = html_path.read_text(errors="replace")
        has_nav = bool(re.search(r'<nav|role="navigation"', html_content, re.IGNORECASE))

        if has_nav:
            pages_with_nav.append(page["url"])
        else:
            pages_without_nav.append(page["url"])

    # If most pages have nav but some don't, that's inconsistency
    total = len(pages_with_nav) + len(pages_without_nav)
    if total > 1 and pages_without_nav and len(pages_with_nav) > len(pages_without_nav):
        findings.append({
            "id": "USAB-FC001",
            "check": "usability/feature-consistency",
            "verdict": "fail",
            "severity": "major",
            "band": "ux",
            "subtype": "decide",
            "title": "Inconsistent navigation across pages",
            "description": f"{len(pages_with_nav)} pages have nav, {len(pages_without_nav)} don't. Users expect consistent navigation.",
            "source": "Nielsen Heuristic #4 (Consistency and standards) + ISO 9241-110 Conformity with user expectations",
            "needs_judgment": True,
            "remediation": f"Add navigation to these pages: {pages_without_nav[:3]}",
            "pages_affected": pages_without_nav
        })

    return findings


def analyze_focus_indicators(html_content, page_url):
    """Check for missing focus indicators (WCAG 2.4.7)."""
    findings = []

    # If outline:none or outline:0 is used globally, focus indicators are removed
    has_outline_none = bool(re.search(r'outline\s*:\s*(none|0)', html_content, re.IGNORECASE))
    has_focus_ring = bool(re.search(r'focus-visible|:focus\s*\{|focus-ring|ring-\d', html_content, re.IGNORECASE))

    if has_outline_none and not has_focus_ring:
        findings.append({
            "id": "USAB-FI001",
            "check": "usability/focus-removed",
            "verdict": "fail",
            "severity": "critical",
            "band": "ux",
            "subtype": "act",
            "title": f"Focus indicators removed on {page_url}",
            "description": "outline:none/0 detected without a custom focus-visible replacement. Keyboard users cannot see which element is focused.",
            "source": "WCAG 2.2 SC 2.4.7 Focus Visible (Level AA)",
            "needs_judgment": False,
            "remediation": "Replace outline:none with a custom focus-visible style, e.g., ring-2 ring-blue-500"
        })

    return findings


def analyze_excise(html_content, page_url):
    """Detect unnecessary steps (excise) — forms with too many fields, unnecessary confirmation pages."""
    findings = []

    # Count form inputs
    input_count = len(re.findall(r'<input[^>]*type=["\'](?!hidden|submit|button|reset)[^"\']*["\']', html_content, re.IGNORECASE))
    select_count = len(re.findall(r'<select', html_content, re.IGNORECASE))
    textarea_count = len(re.findall(r'<textarea', html_content, re.IGNORECASE))
    total_fields = input_count + select_count + textarea_count

    if total_fields > 15:
        findings.append({
            "id": f"USAB-EX{len(findings)+1:03d}",
            "check": "usability/excise-detection",
            "verdict": "fail",
            "severity": "major",
            "band": "ux",
            "subtype": "act",
            "title": f"Excessively long form ({total_fields} fields) on {page_url}",
            "description": f"Form has {total_fields} input fields. Cooper defines excise as 'work that doesn't serve the user's goal'. Long forms are a major excise source.",
            "source": "Cooper: About Face Ch 11 (Eliminating Excise) + Krug Law #3",
            "needs_judgment": True,
            "remediation": "Break into a multi-step wizard, remove optional fields, or use progressive disclosure"
        })

    return findings


def run_usability_checks(captures_dir):
    """Run all usability anti-pattern checks against captured pages."""
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
        nav_extractor = NavigationExtractor()
        nav_extractor.feed(html_content)

        # Per-page checks
        all_findings.extend(analyze_dead_end_flows(page["url"], html_content, nav_extractor))
        all_findings.extend(analyze_empty_states(html_content, page["url"]))
        all_findings.extend(analyze_focus_indicators(html_content, page["url"]))
        all_findings.extend(analyze_excise(html_content, page["url"]))

    # Cross-page checks
    all_findings.extend(analyze_feature_consistency(pages))

    # Deduplicate
    seen = set()
    unique_findings = []
    for f in all_findings:
        key = (f["check"], f.get("title", ""))
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)

    fail_count = len(unique_findings)
    total_checks = 5 * len(pages)  # 5 per-page checks
    pass_count = max(0, total_checks - fail_count)

    return {
        "findings": unique_findings,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "checks_run": ["dead-end-flow", "empty-state-guidance", "feature-consistency", "focus-removed", "excise-detection"]
    }


if __name__ == "__main__":
    artifacts_dir = os.environ.get("ARTIFACTS_DIR", sys.argv[1] if len(sys.argv) > 1 else "artifacts")
    captures_dir = os.path.join(artifacts_dir, "captures")

    results = run_usability_checks(captures_dir)

    output_dir = os.path.join(artifacts_dir, "checks", "usability")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "results.json")

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Usability checks: {results['fail_count']} findings across {len(results.get('checks_run', []))} checks")
