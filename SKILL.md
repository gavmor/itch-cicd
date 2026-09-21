---
name: "itch-cicd"
description: "Ship a tabletop game's PDFs from GitHub to itch.io on every push: render with WeasyPrint, impose print-ready booklet signatures, cut semver GitHub releases, and publish to itch.io via butler. Covers repo configuration, the itch.io page setup, and every gotcha found in production."
metadata: { "includeInPrompt": false }
---

# itch-cicd

A push-to-main pipeline: **render PDFs → cut a GitHub release → publish to
itch.io**. Built for tabletop game repos whose source is HTML rendered with
WeasyPrint, and proven on two live projects.

## What the pipeline does

Every push to `main` (and every manual dispatch with a `patch`/`minor`/`major`
bump choice):

1. **Render** — WeasyPrint renders the reading PDF from HTML source; pypdf
   imposes it into 2-up print-ready booklet signatures on US Letter landscape
   (printer's spreads, page count padded to a multiple of four).
2. **Release** — computes the next semver tag from existing `v*` tags, creates
   the GitHub release, attaches every PDF.
3. **Publish** — installs butler and pushes each PDF to its own itch.io
   channel (`$ITCH_TARGET:pdf`, `$ITCH_TARGET:print-pdf`, plus one channel per
   extra deliverable), with `--userversion` set to the release tag so builds
   show their version on itch.io.

## Files

- `files/build-release-pdfs.yml` — the workflow template. Do not hand-edit
  per project; instantiate it.
- `bin/render.py --config <project.json> --out <workflow.yml>` — fills the
  template from a small JSON config and runs the gate. Fails loudly on any
  violation.
- `bin/check.py <workflow.yml>` — the executable gate. Run it on any workflow
  before pushing; it encodes every rule below.

Config schema for `render.py`:

```json
{
  "project": "girlville",
  "reading_source": "manuscript.html",
  "reading_pdf": "dist/girlville-halfletter.pdf",
  "print_pdf": "dist/girlville-signatures.pdf",
  "extras": [
    {"name": "mockups",
     "source": "mockups/girlville-option-mockups.html",
     "pdf": "dist/girlville-option-mockups.pdf"}
  ]
}
```

Each extra gets a render step, a non-empty check, a release asset, and its own
butler channel.

## Repo configuration (two settings, both required for publish)

The butler steps are **inert until configured** — unconfigured repos still
build and release on GitHub, they just skip itch.io:

- Repo **variable** `ITCH_TARGET` = `itch-username/game-slug`
  (e.g. `storysatchel/the-high-winter-elves-of-girlville`).
- Repo **secret** `BUTLER_API_KEY` — from
  `https://itch.io/user/settings/api-keys`.

Butler itself is installed from the permanent broth URL inside the workflow:
`https://broth.itch.zone/butler/linux-amd64/LATEST/archive/default`.

## Rules the gate enforces (learned the hard way)

1. **Never put `secrets.*` in an `if:` condition.** GitHub Actions rejects it
   at runtime. Gate butler steps on `if: ${{ vars.ITCH_TARGET != '' }}` and
   guard the secret in shell:
   `if [ -z "$BUTLER_API_KEY" ]; then echo ...; exit 0; fi`.
2. **Verify the itch.io account's email before anything else.** Butler fails
   with `itch.io API error (400): /wharf/builds: Please verify your account's
   email address before uploading a build`. The API key and target can be
   perfect and uploads still fail until this is done. This was the single
   production blocker.
3. **`--userversion` on every `butler push`.** Otherwise itch.io builds carry
   no version.
4. **`permissions: contents: write`** — `gh release create` needs it.
5. **A `concurrency` group** — overlapping runs cut duplicate releases.

## itch.io page setup

Create the project page as a **draft** and leave it a draft until explicitly
told to publish. Known-good settings for a pay-what-you-want tabletop game:

- Kind: `Physical games`, Pricing: `$0 or donate`, Release status as
  appropriate (`In development` / `Released`).

Do the page work in a live browser session (the account's saved login), then
**verify on the public page after every save**:

- **Cover image + screenshots** — upload, save, confirm they render. Note: some
  themes don't render a cover banner in the page body; the cover still appears
  in listings and embeds. Screenshots appear in the sidebar.
- **Description edits** — the rich-text editor silently drops edits unless a
  visual-editor input event fires before saving. Trigger an edit in the visual
  editor, then save, then reload and re-read the page to confirm the text
  stuck.

For page imagery, rasterized pages from the release PDFs (title page as cover,
character sheet as screenshot) beat generated art: `pdftoppm -png -r 200`.

## Running and monitoring

- `workflow_dispatch` with `bump: patch|minor|major`, or just push to main.
- Watch the run to `success`; then check the release has every asset and the
  butler push lines in the log show all channels pushing without API errors.
- If the run is green on GitHub but itch.io shows no new build, re-check rule
  2 first.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Invalid workflow file` / step skipped: secrets in `if:` | Rule 1 | Gate on `vars.ITCH_TARGET`, guard secret in shell |
| `Please verify your account's email address before uploading a build` | Rule 2 | Verify the itch.io account email, re-run |
| itch.io builds show no version | Missing `--userversion` | Rule 3 |
| Description reverts after save | Rich-text editor quirk | Input event in visual editor, save, reload-verify |
| Page has no downloads | Butler steps inert or failed | Check `ITCH_TARGET` var, `BUTLER_API_KEY` secret, run logs |
| Donations can't be collected | No payout method on itch.io | Configure payments in itch.io account settings |
