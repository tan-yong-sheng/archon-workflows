---
description: Crawl a web application, discover pages, capture screenshots + DOM + accessibility snapshots
argument-hint: (no arguments - reads target URL from workflow artifacts)
---

# QA/UX Audit — Page Crawler

**Workflow ID**: $WORKFLOW_ID

## Phase 1: LOAD

Read the run metadata from `$ARTIFACTS_DIR/run-metadata.json` to get the target URL.

If the metadata file doesn't exist or has no `target_url`, use `$ARGUMENTS` to extract the first URL (http:// or https://). If neither source provides a URL, abort with an error.

## Phase 2: SETUP

Check if Playwright is installed. If not, install it:

```bash
npx --yes playwright install chromium
```

## Phase 3: CRAWL

Write and execute a Playwright script that:

1. **Launches Chromium** in headless mode
2. **Navigates to the target URL** and waits for networkidle
3. **Discovers all internal links** on the page (same origin, not fragment-only, not mailto/tel)
4. **Visits each discovered page** (max 30 pages, BFS order, skip external domains)
5. **For each page**, captures:
   - **Full-page screenshot** (PNG, saved to `$ARTIFACTS_DIR/captures/screenshots/{slug}.png`)
   - **Accessibility snapshot** (saved to `$ARTIFACTS_DIR/captures/a11y-snapshots/{slug}.json`)
   - **HTML source** (saved to `$ARTIFACTS_DIR/captures/html/{slug}.html`)
   - **Page metadata** (URL, title, meta description, viewport, status code)

Where `{slug}` is a URL-safe slug derived from the page path (e.g., `/about/team` → `about-team`).

6. **Writes a pages manifest** to `$ARTIFACTS_DIR/captures/pages.json`:
```json
[
  {
    "url": "https://example.com/",
    "title": "Home",
    "slug": "index",
    "status": 200,
    "screenshot": "screenshots/index.png",
    "a11y_snapshot": "a11y-snapshots/index.json",
    "html": "html/index.html"
  }
]
```

**Crawl limits:**
- Max 30 pages
- Max 15 seconds per page navigation
- Skip URLs with file extensions (`.pdf`, `.zip`, `.png`, etc.)
- Skip `#fragment`-only links
- Skip `mailto:` and `tel:` links
- Deduplicate by normalized URL (strip trailing slash, strip fragment)

## Phase 4: MULTI-VIEWPORT CAPTURE (optional)

If the crawl succeeds, also capture the 3 most important pages (home, primary action page, and one interior page) at mobile (390×844) and tablet (820×1180) viewports for responsive checks. Save as `{slug}-mobile.png` and `{slug}-tablet.png`.

## Phase 5: REPORT

Write a crawl summary to `$ARTIFACTS_DIR/captures/crawl-summary.md`:
- Total pages discovered
- Pages successfully captured
- Pages that failed to load
- List of all captured page URLs with their slugs

### PHASE_5_CHECKPOINT
- [ ] `pages.json` written to `$ARTIFACTS_DIR/captures/`
- [ ] Screenshots saved to `$ARTIFACTS_DIR/captures/screenshots/`
- [ ] A11y snapshots saved to `$ARTIFACTS_DIR/captures/a11y-snapshots/`
- [ ] HTML sources saved to `$ARTIFACTS_DIR/captures/html/`
- [ ] Crawl summary written to `$ARTIFACTS_DIR/captures/crawl-summary.md`
