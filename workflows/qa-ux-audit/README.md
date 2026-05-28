# qa-ux-audit

Deterministic UX/UI/accessibility audit workflow for Archon.

## What It Does

Crawls a running web application, captures screenshots + DOM, runs rule-based catalog checks, AI-judges ambiguous findings, and produces a ranked fix plan with published-source citations.

**Deterministic**: same URL + same app version → same catalog results every run. The only non-deterministic step is the AI judge, which only evaluates findings the rules couldn't conclusively resolve.

## Architecture

```
┌──────────────┐
│  init-audit  │ bash: parse URL, create workspace
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ crawl-pages  │ command: Playwright crawl, capture screenshots/DOM/a11y
└──────┬───────┘
       │
       ├────────────────┬────────────────┬──────────────────┐
       ▼                ▼                ▼                  ▼
┌────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ run-axe-   │  │ run-heuristic│  │ run-ai-slop  │  │ run-usability│
│ core       │  │ -checks      │  │ -checks      │  │ -checks      │
│ (bash)     │  │ (script/uv)  │  │ (script/uv)  │  │ (script/uv)  │
└──────┬─────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │               │                │                  │
       └───────────┬───┴────────────────┴──────────────────┘
                   │ (parallel layer, trigger_rule: none_failed_min_one_success)
                   ▼
          ┌──────────────┐
          │ aggregate-   │ script/uv: merge all results
          │ checks       │
          └──────┬───────┘
                 │
                 ▼
          ┌──────────────┐
          │ judge-       │ command (AI, sonnet): review ambiguous
          │ findings     │ findings, cite published sources
          └──────┬───────┘
                 │
                 ▼
          ┌──────────────┐
          │ synthesize-  │ command (AI, sonnet): cluster by root
          │ report       │ cause, rank by impact, write report
          └──────┬───────┘
                 │
                 ▼
          ┌──────────────┐
          │ validate-    │ bash: count artifacts, update metadata
          │ audit        │
          └──────────────┘
```

## Check Categories

| Category | Checks | Deterministic? | Source |
|----------|--------|---------------|--------|
| **Accessibility** | WCAG 2.2 via axe-core (color contrast, focus, ARIA, semantics) | ✅ Fully deterministic | WCAG 2.2, axe-core |
| **Heuristics** | Heading hierarchy, vague buttons, system status, visual hierarchy, font hierarchy, error prevention | ✅ Rule-based | Nielsen's 10, ISO 9241-110, Krug |
| **AI-Slop** | Purple gradients, Tailwind defaults, Shadcn signatures, lorem ipsum, placeholder names, "Coming soon", emoji-as-icon, vague taglines, cliché CTAs | ✅ Pattern matching | NN/g AI Prototyping |
| **Usability** | Dead-end flows, empty states, feature consistency, focus indicators, excise (long forms) | ✅ Rule-based | Nielsen #3/#4, Cooper, Krug |

## Sources (Don't Invent Rule)

Every judgment-call finding cites a published, publicly-verifiable source:

- **NN/g** — Nielsen Norman Group research
- **WCAG 2.2** — W3C accessibility guidelines
- **ISO 9241-11/110** — Usability and interaction principles
- **Nielsen's 10 Usability Heuristics** (1994/2020)
- **Krug: Don't Make Me Think** (3rd ed., 2014)
- **Cooper: About Face** (4th ed., 2014)
- **Norman: Emotional Design** (2004)
- **Lindgaard et al. 2006** — 50ms first impressions
- **Christensen: Jobs To Be Done**
- **Apple HIG** (icons section only)
- **axe-core** (Deque)

Self-evident anti-patterns (lorem ipsum, "Coming soon", placeholder names) don't need citations.

## Usage

```bash
archon workflow run qa-ux-audit "Audit https://my-app.example.com"
```

The argument MUST contain the target URL (http:// or https://).

## Output

Artifacts are written to the workflow's `$ARTIFACTS_DIR`:

```
artifacts/
├── run-metadata.json          # Run context
├── captures/
│   ├── pages.json             # Pages manifest
│   ├── screenshots/           # Full-page PNGs
│   ├── a11y-snapshots/        # Playwright accessibility tree JSONs
│   ├── html/                  # Raw HTML sources
│   └── crawl-summary.md       # Crawl stats
├── checks/
│   ├── axe-core/results.json  # WCAG violations
│   ├── heuristic/results.json # Nielsen heuristic findings
│   ├── ai-slop/results.json   # AI-slop pattern findings
│   ├── usability/results.json # Usability anti-pattern findings
│   └── aggregate-results.json # Merged + categorized
├── judge/
│   └── judged-results.json    # AI-judged ambiguous findings
└── report/
    ├── ux-audit-report.md     # Human-readable ranked fix plan
    └── audit-summary.json     # Machine-readable summary
```

## Requirements

- **Playwright** (Chromium) — for page crawling and axe-core execution
- **Python 3.10+** — for rule-based check scripts
- **Node.js 18+** — for axe-core runner

## What This Does NOT Do

- Functional testing (that's Playwright E2E)
- Performance benchmarking (that's Lighthouse)
- Security review (that's archon-security-review)
- Exploratory/adversarial testing (that's agentic-test-explorer)
- Predict retention or market fit

Inspired by [uxaudit](https://github.com/gotalab/uxaudit) and [Murphy](https://github.com/ProsusAI/Murphy). Replicated as an Archon workflow for CI-integrated, unattended, deterministic UX auditing.
