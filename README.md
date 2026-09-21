# itch-cicd

Push-to-main CI/CD from a GitHub game repo to itch.io: render PDFs with
WeasyPrint, impose print-ready booklet signatures, cut semver GitHub releases,
and publish to itch.io via butler — plus the itch.io page setup playbook and
every production gotcha, encoded as an executable gate.

## Use

Read `SKILL.md` for the full playbook, then:

```bash
bin/render.py --config project.json --out .github/workflows/build-release-pdfs.yml
```

`project.json`:

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

Then set the repo variable `ITCH_TARGET` (`itch-username/game-slug`) and the
repo secret `BUTLER_API_KEY` (from itch.io/user/settings/api-keys), and verify
the itch.io account's email address — butler refuses uploads until you do.

Validate any workflow any time with `bin/check.py <workflow.yml>`.
