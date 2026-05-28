#!/usr/bin/env python3
"""
Heuristic Checks — Nielsen's 10 Usability Heuristics (rule-based)

Analyzes captured HTML and accessibility snapshots for violations of
Nielsen's usability heuristics that can be detected mechanically.

These are deterministic checks — no AI judgment needed. Findings that
require context or interpretation are flagged with needs_judgment=true
for the AI judge.

Sources:
- Nielsen's 10 Usability Heuristics (NN/g, 1994/2020)
- ISO 9241-110:2020 Interaction Principles
- Krug: Don't Make Me Think (3rd ed., 2014)
"""

import json
import os
import re
import sys
from pathlib import Path
from html.parser import HTMLParser


class HTMLAnalyzer(HTMLParser):
    """Parse HTML to extract structural elements for heuristic analysis."""
    def __init__(self):
        super().__init__()
        self.headings = []       # (level, text)
        self.buttons = []        # (text, has_aria_label, type)
        self.links = []          # (text, href, has_aria_label)
        self.images = []         # (alt, src, has_alt)
        self.forms = []          # (action, inputs_count, has_labels)
        self.meta_tags = {}      # name → content
        self.title = ""
        self._in_title = False
        self._current_tag = None
        self._current_attrs = {}
        self._heading_text = ""
        self._in_heading = False
        self._heading_level = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self._current_tag = tag
        self._current_attrs = attrs_dict

        if tag == "title":
            self._in_title = True
        elif tag.startswith("h") and tag[1:].isdigit():
            self._in_heading = True
            self._heading_level = int(tag[1:])
            self._heading_text = ""
        elif tag == "button":
            text = attrs_dict.get("aria-label", "")
            has_aria = "aria-label" in attrs_dict
            btype = attrs_dict.get("type", "button")
            self.buttons.append({"text": text, "has_aria_label": has_aria, "type": btype, "raw_attrs": attrs_dict})
        elif tag == "a":
            href = attrs_dict.get("href", "")
            aria = attrs_dict.get("aria-label", "")
            self.links.append({"text": "", "href": href, "aria_label": aria})
        elif tag == "img":
            alt = attrs_dict.get("alt", None)
            src = attrs_dict.get("src", "")
            self.images.append({"alt": alt, "src": src, "has_alt": alt is not None})
        elif tag == "form":
            self.forms.append({"action": attrs_dict.get("action", ""), "inputs": []})
        elif tag == "input" and self.forms:
            label = attrs_dict.get("aria-label", attrs_dict.get("placeholder", ""))
            itype = attrs_dict.get("type", "text")
            has_label = "aria-label" in attrs_dict or attrs_dict.get("id", "")
            self.forms[-1]["inputs"].append({"type": itype, "label": label, "has_label": has_label})
        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            content = attrs_dict.get("content", "")
            if name:
                self.meta_tags[name] = content

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag.startswith("h") and tag[1:].isdigit():
            text = self._heading_text.strip()
            self.headings.append({"level": self._heading_level, "text": text})
            self._in_heading = False
        self._current_tag = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._in_heading:
            self._heading_text += data
        # Capture button/link text
        if self._current_tag == "button":
            for b in self.buttons:
                if not b["text"] and not b["has_aria_label"]:
                    b["text"] = data.strip()
        if self._current_tag == "a":
            for l in reversed(self.links):
                if not l["text"]:
                    l["text"] = data.strip()
                    break


def analyze_heading_hierarchy(headings):
    """Heuristic #1 + ISO 9241-110 Self-descriptiveness: Check heading hierarchy."""
    findings = []
    if not headings:
        return findings

    prev_level = 0
    for h in headings:
        level = h["level"]
        if prev_level > 0 and level > prev_level + 1:
            findings.append({
                "id": f"HEURISTIC-H{len(findings)+1:03d}",
                "check": "heuristic/heading-skip-levels",
                "verdict": "fail",
                "severity": "minor",
                "band": "ux",
                "subtype": "understand",
                "title": f"Heading skips from h{prev_level} to h{level}",
                "description": f"Heading hierarchy jumps from h{prev_level} to h{level}: \"{h['text'][:60]}\"",
                "source": "WCAG 2.2 SC 1.3.1 Info and Relationships (Level A) + ISO 9241-110 Self-descriptiveness",
                "needs_judgment": False,
                "remediation": f"Use h{prev_level + 1} instead of h{level}, or add an intermediate h{prev_level + 1} heading"
            })
        prev_level = level
    return findings


def analyze_vague_buttons(buttons):
    """Heuristic #2 + Krug Law #1: Check for vague button labels."""
    findings = []
    vague_patterns = ["click here", "submit", "click", "here", "more", "go", "ok", "yes", "no", "continue", "next", ""]

    for btn in buttons:
        text = btn["text"].lower().strip()
        if text in vague_patterns and not btn["has_aria_label"]:
            findings.append({
                "id": f"HEURISTIC-B{len(findings)+1:03d}",
                "check": "heuristic/vague-button-labels",
                "verdict": "fail",
                "severity": "major",
                "band": "ux",
                "subtype": "decide",
                "title": f"Vague button label: '{btn['text'] or '(no label)'}'",
                "description": f"Button with text '{btn['text'] or '(no label)'}' does not describe its action. Users must guess what happens.",
                "source": "Nielsen Heuristic #2 (Match between system and real world) + Krug Law #1 (Don't make me think) + ISO 9241-110 Self-descriptiveness",
                "needs_judgment": True,
                "remediation": "Replace with a specific action label, e.g., 'Save changes', 'Delete item', 'Send invitation'"
            })
    return findings


def analyze_system_status(meta_tags, html_content):
    """Heuristic #1: Visibility of system status — check for loading/feedback patterns."""
    findings = []

    # Check for pages with forms but no visible feedback mechanism
    has_form = "<form" in html_content.lower()
    has_loading_state = any(p in html_content.lower() for p in ["loading", "spinner", "skeleton", "aria-busy", "role='status'", 'role="status"'])
    has_toast = any(p in html_content.lower() for p in ["toast", "notification", "alert", "snackbar", "role='alert'", 'role="alert"'])

    if has_form and not has_loading_state and not has_toast:
        findings.append({
            "id": "HEURISTIC-S001",
            "check": "heuristic/system-status-visibility",
            "verdict": "fail",
            "severity": "major",
            "band": "ux",
            "subtype": "recover",
            "title": "Form page lacks loading/success/error feedback",
            "description": "Page contains a form but no visible loading state, success, or error feedback mechanism detected in markup.",
            "source": "Nielsen Heuristic #1 (Visibility of system status) + NN/g Response Times (3 limits)",
            "needs_judgment": True,
            "remediation": "Add loading indicators for async form submission and success/error feedback after completion"
        })

    return findings


def analyze_visual_hierarchy(headings, html_content):
    """Check for visual hierarchy issues — too many same-level headings, or no headings at all."""
    findings = []

    if len(headings) == 0:
        # Page has no headings at all — likely a hierarchy problem
        if len(html_content) > 2000:  # Only flag for substantial pages
            findings.append({
                "id": "HEURISTIC-V001",
                "check": "heuristic/visual-hierarchy",
                "verdict": "fail",
                "severity": "major",
                "band": "ux",
                "subtype": "understand",
                "title": "Page has no heading structure",
                "description": "Substantial page content but no heading elements (h1-h6) found. Users cannot scan the page structure.",
                "source": "Krug Ch 3 (Billboard Design 101) + NN/g First Impressions (50ms)",
                "needs_judgment": True,
                "remediation": "Add a clear heading hierarchy starting with h1 for the page title"
            })

    # Check for too many h1s
    h1_count = sum(1 for h in headings if h["level"] == 1)
    if h1_count > 1:
        findings.append({
            "id": "HEURISTIC-V002",
            "check": "heuristic/multiple-h1",
            "verdict": "fail",
            "severity": "minor",
            "band": "ux",
            "subtype": "understand",
            "title": f"Page has {h1_count} h1 elements",
            "description": f"Found {h1_count} h1 headings. Best practice is one h1 per page to establish the primary topic.",
            "source": "WCAG 2.2 SC 1.3.1 Info and Relationships + Krug Ch 3",
            "needs_judgment": False,
            "remediation": "Use a single h1 for the page title; demote others to h2"
        })

    return findings


def analyze_font_hierarchy(html_content):
    """Check font usage for hierarchy issues."""
    findings = []

    # Count distinct font-family declarations
    font_matches = re.findall(r'font-family\s*:\s*([^;}{]+)', html_content, re.IGNORECASE)
    unique_fonts = set(f.strip().lower().strip('"\'') for f in font_matches)

    if len(unique_fonts) > 4:
        findings.append({
            "id": "HEURISTIC-F001",
            "check": "heuristic/font-hierarchy",
            "verdict": "fail",
            "severity": "minor",
            "band": "ui-risk",
            "subtype": None,
            "title": f"Too many font families: {len(unique_fonts)}",
            "description": f"Found {len(unique_fonts)} distinct font-family declarations. NN/g recommends max 2 fonts.",
            "source": "NN/g First Impressions (max ~2 fonts recommended) + WCAG 2.2 SC 1.4.4/2.4.6",
            "needs_judgment": True,
            "remediation": "Reduce to 1-2 font families: one for headings, one for body text"
        })

    return findings


def analyze_error_prevention(forms):
    """Heuristic #5: Error prevention — check form validation patterns."""
    findings = []

    for form in forms:
        inputs = form.get("inputs", [])
        if not inputs:
            continue

        # Check for inputs without labels/placeholders
        unlabeled = [i for i in inputs if not i["has_label"] and i["type"] not in ("hidden", "submit", "button", "reset")]
        if unlabeled:
            findings.append({
                "id": f"HEURISTIC-E{len(findings)+1:03d}",
                "check": "heuristic/error-prevention",
                "verdict": "fail",
                "severity": "major",
                "band": "ux",
                "subtype": "act",
                "title": f"Form has {len(unlabeled)} unlabeled input(s)",
                "description": f"Form inputs without labels or placeholders: {[i['type'] for i in unlabeled]}",
                "source": "Nielsen Heuristic #5 (Error prevention) + WCAG 2.2 SC 1.3.1",
                "needs_judgment": False,
                "remediation": "Add aria-label, <label>, or meaningful placeholder to each input"
            })

    return findings


def run_heuristic_checks(captures_dir):
    """Run all heuristic checks against captured pages."""
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
        analyzer = HTMLAnalyzer()
        analyzer.feed(html_content)

        # Run each heuristic check
        findings = []
        findings.extend(analyze_heading_hierarchy(analyzer.headings))
        findings.extend(analyze_vague_buttons(analyzer.buttons))
        findings.extend(analyze_system_status(analyzer.meta_tags, html_content))
        findings.extend(analyze_visual_hierarchy(analyzer.headings, html_content))
        findings.extend(analyze_font_hierarchy(html_content))
        findings.extend(analyze_error_prevention(analyzer.forms))

        # Tag each finding with the page URL
        for f in findings:
            f["page_url"] = page["url"]

        all_findings.extend(findings)

    # Deduplicate findings that appear on multiple pages (same check + same title)
    seen = set()
    unique_findings = []
    for f in all_findings:
        key = (f["check"], f["title"])
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)
        else:
            # Add this page to the existing finding's pages
            existing = next(x for x in unique_findings if (x["check"], x["title"]) == key)
            if "pages_affected" not in existing:
                existing["pages_affected"] = [existing["page_url"]]
            existing["pages_affected"].append(f["page_url"])

    # Set pages_affected for single-page findings
    for f in unique_findings:
        if "pages_affected" not in f:
            f["pages_affected"] = [f["page_url"]]
        f.pop("page_url", None)

    pass_count = sum(1 for _ in pages) * 6 - len(unique_findings)  # 6 checks per page
    fail_count = len(unique_findings)

    return {
        "findings": unique_findings,
        "pass_count": max(0, pass_count),
        "fail_count": fail_count,
        "checks_run": ["heading-skip-levels", "vague-button-labels", "system-status-visibility",
                       "visual-hierarchy", "font-hierarchy", "error-prevention"]
    }


if __name__ == "__main__":
    artifacts_dir = os.environ.get("ARTIFACTS_DIR", sys.argv[1] if len(sys.argv) > 1 else "artifacts")
    captures_dir = os.path.join(artifacts_dir, "captures")

    results = run_heuristic_checks(captures_dir)

    output_dir = os.path.join(artifacts_dir, "checks", "heuristic")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "results.json")

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary for node output
    print(f"Heuristic checks: {results['fail_count']} findings across {len(results.get('checks_run', []))} checks")
