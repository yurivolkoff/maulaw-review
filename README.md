# MauLaw digest review site

Static site for reviewing AI-extracted judgment digests: original judgment,
rendered digest, and the model's raw JSON output, side by side per case.
Published to GitHub Pages so case URLs can be handed to external reviewers.

Live at: `https://yurivolkoff.github.io/maulaw-review/`

## How it works

- `cases.json` is the manifest: one entry per case (paths, model, prompt
  version, schema version, digested date). This is the only file you edit by
  hand to add or update a case.
- `build-site.py` reads `cases.json` and regenerates everything under
  `docs/` from scratch (index page + one page per case). It reuses
  `m3/tools/render-digest.py`'s line-numbering and two-pane HTML renderer
  in-process, so numbering always matches the pipeline exactly.
- `publish.ps1` runs the build, then commits and pushes `docs/` (and the
  manifest/generator) to `main`. GitHub Pages serves the site from `main`
  branch, `/docs` folder.
- `docs/` is generated output, but it **is committed** — GitHub Pages needs
  it in the repo to serve from.

## Adding a new case

1. Run the extraction as usual:
   ```bash
   python3 m3/tools/run-case.py --case ".../txts/<case>.pdf.txt"   # Mac/Linux, from the project root
   # Windows: .\m3\tools\run-case.ps1 -Case "...\txts\<case>.pdf.txt"
   ```
   This now ends with a non-fatal "register-in-site" stage that
   adds/updates the case's entry in `cases.json` automatically. If it
   printed a warning instead (e.g. the site folder wasn't found), add the entry
   to `cases.json` by hand — copy an existing entry and update `slug`,
   `title`, `citation`, the three paths, and the four metadata fields.
2. Publish:
   ```bash
   ./publish.sh          # Mac/Linux (publish.ps1 on Windows)
   ```
   This regenerates `docs/`, commits, and pushes. Pages rebuilds
   automatically within a minute or two of the push.

## Re-running a case with a new prompt version

Re-run `run-case.ps1` against the same judgment — the register-in-site stage
**updates** the existing manifest entry for that slug in place (matched by
`slug`, not appended as a duplicate). To change `prompt_version` without a
full re-extraction, edit the field directly in `cases.json`, then run
`publish.ps1`.

## Manifest field reference (`cases.json`)

| Field | Meaning |
|---|---|
| `slug` | Unique case ID, also the URL path segment (`cases/<slug>/`) |
| `title` | Case name, from the digest's `case_name` |
| `citation` | Citation(s) shown on the index and case page |
| `judgment_txt` | Path to the source judgment `.txt`, relative to a project root (see «Path roots» below) or absolute |
| `digest_raw` | Path to the model's raw `out-<case>.json` (pre-fence-strip) |
| `digest_clean` | Path to `out-<case>.clean.json` (what the renderer consumes) |
| `model` | Extraction model ID |
| `prompt_version` | Extractor prompt version string (e.g. `extractor.v1`) |
| `schema_version` | Output schema version (e.g. `v1`) |
| `digested_date` | `YYYY-MM-DD` |

## Path roots

Relative manifest paths (`m3/runs/...`, `_temporary/...`) and the renderer
`m3/tools/render-digest.py` are looked up in these roots, first match wins:
the parent of this folder (legacy `<project>/site/` layout), its grandparent
(`<project>/code/maulaw-review/`, the Mac layout), then the read-only Windows
backup `~/Archive/win-claude-backup/MauLaw`. Override with `MAULAW_ROOTS`
(`:`-separated). New runs written into the project shadow the backup.

## Search engines

Every page carries `noindex, nofollow`, and every case page a short
«AI-generated research draft, not legal advice» notice with the corpus
snapshot date: the site is public but meant for invited reviewers.

## Where things live

- `site\cases.json` — manifest (hand-edited or auto-updated by run-case.ps1)
- `site\build-site.py` — generator, do not need to touch for routine updates
- `publish.sh` / `publish.ps1` — the only command you normally run
- `site\docs\` — generated output, committed, served by Pages
- Do **not** edit files under `docs\` directly — they're overwritten on
  every `publish.ps1` run.

## Local preview before publishing

```bash
python3 build-site.py
open docs/index.html
```

## Repo / Pages setup (one-time, already done)

- Repo: `yurivolkoff/maulaw-review` (public)
- Pages source: `main` branch, `/docs` folder
- No external resources (CDNs, fonts, etc.) — everything is self-contained
  so it works under the `/maulaw-review/` subpath with plain relative links.
