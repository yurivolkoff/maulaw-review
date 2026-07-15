"""Build the MauLaw digest-review static site into site/docs/ from
site/cases.json.

Idempotent full regeneration: every run wipes and rebuilds docs/ from the
manifest, so there is no accumulation of stale case pages when a slug is
removed or renamed.

Reuses m3/tools/render-digest.py's line-numbering and two-pane HTML renderer
in-process (imported by file path, since its module name contains a hyphen)
rather than reimplementing them, so the "original judgment" line numbering
(mode 1) and the "digested judgment, rendered" two-pane page (mode 2) are
guaranteed to use the exact same numbering logic the digests' pinpoints were
built against.

Usage:
    python build-site.py
"""

import html
import importlib.util
import json
import shutil
import sys
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SITE_DIR.parent
DOCS_DIR = SITE_DIR / "docs"
CASES_JSON_PATH = SITE_DIR / "cases.json"
RENDER_DIGEST_PATH = PROJECT_ROOT / "m3" / "tools" / "render-digest.py"

REPO_NAME = "maulaw-review"  # used only in on-screen messages, not in links


# --------------------------------------------------------------------------
# Import render-digest.py by file path (its filename is not a valid Python
# module identifier because of the hyphen).
# --------------------------------------------------------------------------

def load_render_digest():
    if not RENDER_DIGEST_PATH.is_file():
        sys.exit(f"ERROR: renderer not found: {RENDER_DIGEST_PATH}")
    spec = importlib.util.spec_from_file_location("render_digest", RENDER_DIGEST_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def esc(s) -> str:
    if s is None:
        return ""
    return html.escape(str(s), quote=True)


def resolve(rel_or_abs: str) -> Path:
    p = Path(rel_or_abs)
    if p.is_absolute():
        return p
    return (PROJECT_ROOT / rel_or_abs).resolve()


# --------------------------------------------------------------------------
# Page shells
# --------------------------------------------------------------------------

SITE_CSS = """
:root {
  --bg: #ffffff; --fg: #1a1a1a; --muted: #6b6b6b; --border: #d8d8d8;
  --code-bg: #f2f2f2; --link: #1a56db; --accent: #1a56db;
  --header-bg: #f7f7f8; --warn-bg: #fff8e1; --warn-fg: #7a5b00;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #14171a; --fg: #e6e6e6; --muted: #9a9a9a; --border: #33383d;
    --code-bg: #1f2327; --link: #7aa2ff; --accent: #7aa2ff;
    --header-bg: #1b1e21; --warn-bg: #3a2f0a; --warn-fg: #e0c46a;
  }
}
:root[data-theme="dark"] {
  --bg: #14171a; --fg: #e6e6e6; --muted: #9a9a9a; --border: #33383d;
  --code-bg: #1f2327; --link: #7aa2ff; --accent: #7aa2ff;
  --header-bg: #1b1e21; --warn-bg: #3a2f0a; --warn-fg: #e0c46a;
}
:root[data-theme="light"] {
  --bg: #ffffff; --fg: #1a1a1a; --muted: #6b6b6b; --border: #d8d8d8;
  --code-bg: #f2f2f2; --link: #1a56db; --accent: #1a56db;
  --header-bg: #f7f7f8; --warn-bg: #fff8e1; --warn-fg: #7a5b00;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--fg);
  font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
a { color: var(--link); }
.wrap { max-width: 1100px; margin: 0 auto; padding: 1.25rem 1.5rem 3rem; }
header.site-header { background: var(--header-bg); border-bottom: 1px solid var(--border); }
header.site-header .wrap { padding-top: 1.5rem; padding-bottom: 1.5rem; }
h1 { font-size: 1.4rem; margin: 0 0 .5rem; }
.lede { color: var(--muted); max-width: 70ch; line-height: 1.5; margin: 0; }
.disclaimer { margin-top: .75rem; padding: .6rem .9rem; background: var(--warn-bg); color: var(--warn-fg);
  border-radius: 6px; font-size: .85rem; max-width: 70ch; line-height: 1.4; }
table.cases { border-collapse: collapse; width: 100%; margin-top: 1.5rem; font-size: .9rem; }
table.cases th, table.cases td { border-top: 1px solid var(--border); padding: .55rem .6rem; text-align: left; vertical-align: top; }
table.cases thead th { border-top: none; border-bottom: 2px solid var(--border); color: var(--muted); font-weight: 600; font-size: .8rem; text-transform: uppercase; letter-spacing: .02em; }
table.cases tbody tr:hover { background: var(--code-bg); }
code { background: var(--code-bg); padding: .05rem .3rem; border-radius: 3px; font-size: .9em; }
.muted { color: var(--muted); }
.back-link { display: inline-block; margin-bottom: 1rem; font-size: .9rem; }
.case-meta { display: flex; flex-wrap: wrap; gap: .4rem .9rem; font-size: .85rem; color: var(--muted); margin: .4rem 0 1rem; }
.case-meta span strong { color: var(--fg); font-weight: 600; }
.tabs { display: flex; gap: .25rem; border-bottom: 1px solid var(--border); margin-bottom: 1rem; }
.tab-btn { appearance: none; background: none; border: none; border-bottom: 2px solid transparent; color: var(--muted);
  padding: .55rem .9rem; font-size: .9rem; cursor: pointer; font-family: inherit; }
.tab-btn:hover { color: var(--fg); }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
.tab-panel { display: none; }
.tab-panel.active { display: block; }
.tab-panel iframe { width: 100%; height: 82vh; border: 1px solid var(--border); border-radius: 6px; }
pre.raw-json { background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px; padding: 1rem;
  overflow: auto; max-height: 82vh; font-family: Consolas, "Courier New", monospace; font-size: .8rem; line-height: 1.45; white-space: pre-wrap; word-break: break-word; }
.pane-original { border: 1px solid var(--border); border-radius: 6px; max-height: 82vh; overflow: auto; }
.pane-original .pane-header { position: sticky; top: 0; background: var(--code-bg); border-bottom: 1px solid var(--border);
  padding: .5rem .75rem; font-size: .8rem; color: var(--muted); }
.pane-original pre.lines { margin: 0; padding: .25rem 0 1.5rem; font-family: Consolas, "Courier New", monospace; font-size: .82rem; line-height: 1.5; }
.pane-original .line { display: block; white-space: pre; padding: 0 .75rem; }
.pane-original .line:hover { background: rgba(127,127,127,.08); }
.pane-original .line.hl { background: #fff3a3; }
.pane-original .ln { display: inline-block; width: 3.4em; color: var(--muted); user-select: none; text-align: right; margin-right: .75em; }
footer.site-footer { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border); color: var(--muted); font-size: .8rem; }
"""

TABS_JS = """
(function () {
  var validTabs = ['original', 'rendered', 'raw'];
  function tabFromHash() {
    var h = (location.hash || '').replace('#', '');
    return validTabs.indexOf(h) !== -1 ? h : validTabs[0];
  }
  function showTab(name) {
    validTabs.forEach(function (t) {
      var btn = document.getElementById('tab-btn-' + t);
      var panel = document.getElementById('tab-panel-' + t);
      var active = t === name;
      if (btn) btn.classList.toggle('active', active);
      if (panel) panel.classList.toggle('active', active);
    });
  }
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.tab-btn');
    if (!btn) return;
    var name = btn.id.replace('tab-btn-', '');
    if (validTabs.indexOf(name) === -1) return;
    history.replaceState(null, '', '#' + name);
    showTab(name);
  });
  window.addEventListener('hashchange', function () { showTab(tabFromHash()); });
  showTab(tabFromHash());
})();
"""


def page_shell(title: str, body: str, extra_css: str = "", extra_js: str = "") -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{esc(title)}</title>"
        f"<style>{SITE_CSS}{extra_css}</style>"
        "</head><body>"
        f"{body}"
        f"<script>{extra_js}</script>"
        "</body></html>"
    )


def render_original_pane(rd, lines) -> str:
    """Standalone version of render_digest.render_left_pane, restyled for the
    .pane-original wrapper used on this site (same line numbering + anchors,
    different container class so it doesn't fight render-digest's own
    two-pane layout CSS when both are on the same case page)."""
    out = ['<div class="pane-original" id="judgment-pane">']
    out.append(f'<div class="pane-header">Judgment text &middot; {len(lines)} lines</div>')
    out.append('<pre class="lines">')
    for i, l in enumerate(lines, 1):
        out.append(f'<span class="line" id="L{i}"><span class="ln">{i}</span><span class="txt">{rd.esc(l)}</span></span>\n')
    out.append("</pre>")
    out.append("</div>")
    return "".join(out)


# --------------------------------------------------------------------------
# Index page
# --------------------------------------------------------------------------

def build_index(cases: list[dict]) -> str:
    rows = []
    for c in cases:
        rows.append(
            "<tr>"
            f"<td><a href='cases/{esc(c['slug'])}/index.html'>{esc(c['title'])}</a></td>"
            f"<td><code>{esc(c['citation'])}</code></td>"
            f"<td>{esc(c['digested_date'])}</td>"
            f"<td>{esc(c['model'])}</td>"
            f"<td>{esc(c['prompt_version'])}</td>"
            f"<td>{esc(c['schema_version'])}</td>"
            "</tr>"
        )
    body = f"""
<header class="site-header"><div class="wrap">
  <h1>MauLaw digest review</h1>
  <p class="lede">AI-extracted headnotes and citation digests of Mauritian judgments, generated by an
  automated pipeline and currently under human review. Each case below links to the original judgment
  text, the rendered digest, and the model's raw output.</p>
  <div class="disclaimer"><strong>Not legal advice.</strong> These digests are AI-generated drafts for
  internal review and have not been verified by a legal practitioner. Do not rely on them as a substitute
  for reading the original judgment or for professional legal advice.</div>
</div></header>
<div class="wrap">
  <table class="cases">
    <thead><tr><th>Case</th><th>Citation</th><th>Digested</th><th>Model</th><th>Prompt</th><th>Schema</th></tr></thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  <footer class="site-footer">{len(cases)} case(s) &middot; generated by site/build-site.py</footer>
</div>
"""
    return page_shell("MauLaw digest review", body)


# --------------------------------------------------------------------------
# Case page
# --------------------------------------------------------------------------

def build_case(rd, case: dict, case_out_dir: Path) -> None:
    slug = case["slug"]
    judgment_path = resolve(case["judgment_txt"])
    digest_clean_path = resolve(case["digest_clean"])
    digest_raw_path = resolve(case["digest_raw"])

    for label, p in (("judgment_txt", judgment_path), ("digest_clean", digest_clean_path), ("digest_raw", digest_raw_path)):
        if not p.is_file():
            sys.exit(f"ERROR: case '{slug}': {label} not found: {p}")

    lines = rd.read_lines(judgment_path)
    digest_clean_text = digest_clean_path.read_text(encoding="utf-8")
    j = json.loads(digest_clean_text)

    case_out_dir.mkdir(parents=True, exist_ok=True)

    # Mode 2: reuse render-digest.py's full two-pane HTML page verbatim,
    # written alongside the case index.html and embedded via iframe.
    digest_html = rd.render_html_page(j, lines, slug)
    (case_out_dir / "digest.html").write_text(digest_html, encoding="utf-8")

    # Mode 1: reuse render-digest.py's line-numbering (rd.read_lines) so the
    # numbering is byte-identical to what mode 2 and the digest pinpoints use;
    # only the wrapping container is site-styled instead of render-digest's
    # own two-pane layout.
    original_pane_html = render_original_pane(rd, lines)

    # Mode 3: verbatim raw model output (NOT the clean json), HTML-escaped.
    raw_text = digest_raw_path.read_text(encoding="utf-8")
    raw_escaped = esc(raw_text)

    meta = (
        '<div class="case-meta">'
        f"<span><strong>Digested:</strong> {esc(case['digested_date'])}</span>"
        f"<span><strong>Model:</strong> {esc(case['model'])}</span>"
        f"<span><strong>Prompt:</strong> {esc(case['prompt_version'])}</span>"
        f"<span><strong>Schema:</strong> {esc(case['schema_version'])}</span>"
        "</div>"
    )

    body = f"""
<header class="site-header"><div class="wrap">
  <a class="back-link" href="../../index.html">&larr; All cases</a>
  <h1>{esc(case['title'])}</h1>
  <p class="lede"><code>{esc(case['citation'])}</code></p>
  {meta}
</div></header>
<div class="wrap">
  <div class="tabs">
    <button class="tab-btn" id="tab-btn-original">Original judgment</button>
    <button class="tab-btn" id="tab-btn-rendered">Digested judgment (rendered)</button>
    <button class="tab-btn" id="tab-btn-raw">Original digest (raw)</button>
  </div>
  <div class="tab-panel" id="tab-panel-original">{original_pane_html}</div>
  <div class="tab-panel" id="tab-panel-rendered"><iframe src="digest.html" title="Rendered digest"></iframe></div>
  <div class="tab-panel" id="tab-panel-raw"><pre class="raw-json">{raw_escaped}</pre></div>
  <footer class="site-footer">slug: <code>{esc(slug)}</code></footer>
</div>
"""
    page = page_shell(f"{case['title']} · {case['citation']} · review", body, extra_js=TABS_JS)
    (case_out_dir / "index.html").write_text(page, encoding="utf-8")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> None:
    if not CASES_JSON_PATH.is_file():
        sys.exit(f"ERROR: manifest not found: {CASES_JSON_PATH}")
    cases = json.loads(CASES_JSON_PATH.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        sys.exit(f"ERROR: manifest is empty or not a list: {CASES_JSON_PATH}")

    slugs = [c.get("slug") for c in cases]
    if len(slugs) != len(set(slugs)):
        sys.exit(f"ERROR: duplicate slugs in manifest: {slugs}")

    rd = load_render_digest()

    # Full idempotent regeneration: wipe docs/ and rebuild from scratch so a
    # removed/renamed case never leaves an orphaned page behind.
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir(parents=True)
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")

    for case in cases:
        for req in ("slug", "title", "citation", "judgment_txt", "digest_raw", "digest_clean",
                     "model", "prompt_version", "schema_version", "digested_date"):
            if req not in case:
                sys.exit(f"ERROR: case missing required field '{req}': {case}")
        case_out_dir = DOCS_DIR / "cases" / case["slug"]
        build_case(rd, case, case_out_dir)
        print(f"  built: {case['slug']}")

    (DOCS_DIR / "index.html").write_text(build_index(cases), encoding="utf-8")
    print(f"Built {len(cases)} case page(s) -> {DOCS_DIR}")


if __name__ == "__main__":
    main()
