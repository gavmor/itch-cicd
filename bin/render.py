#!/usr/bin/env python3
"""Instantiate the itch-cicd workflow template for a project.

Reads a JSON config, substitutes tokens in files/build-release-pdfs.yml,
writes the result, then runs bin/check.py on it as a gate.

Usage: bin/render.py --config project.json --out .github/workflows/build-release-pdfs.yml

Config schema:
{
  "project": "girlville",                        # artifact name prefix
  "reading_source": "manuscript.html",           # HTML WeasyPrint renders
  "reading_pdf": "dist/girlville-halfletter.pdf",
  "print_pdf": "dist/girlville-signatures.pdf",
  "extras": [                                    # optional extra deliverables
    {"name": "mockups",
     "source": "mockups/girlville-option-mockups.html",
     "pdf": "dist/girlville-option-mockups.pdf"}
  ]
}

Each extra gets: a render step, a non-empty check, a release asset, an
uploaded artifact (via dist/*.pdf), and its own butler channel
($ITCH_TARGET:<name>).
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "files", "build-release-pdfs.yml")
CHECK = os.path.join(HERE, "check.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cfg = json.load(open(args.config))
    extras = cfg.get("extras", [])

    render_steps = []
    check_lines = []
    release_files = [cfg["reading_pdf"], cfg["print_pdf"]]
    publish = [
        "          mkdir -p /tmp/itch/reading /tmp/itch/print",
        f"          cp {cfg['reading_pdf']} /tmp/itch/reading/",
        f"          cp {cfg['print_pdf']} /tmp/itch/print/",
        '          /tmp/butler/butler push /tmp/itch/reading "$ITCH_TARGET:pdf" --userversion "$RELEASE_TAG"',
        '          /tmp/butler/butler push /tmp/itch/print "$ITCH_TARGET:print-pdf" --userversion "$RELEASE_TAG"',
    ]
    for e in extras:
        name, source, pdf = e["name"], e["source"], e["pdf"]
        render_steps.append(
            f"      - name: Render {name} PDF\n"
            f"        run: |\n"
            f"          test -f {source}\n"
            f"          weasyprint {source} {pdf}\n"
        )
        check_lines.append(f"          test -s {pdf}")
        release_files.append(pdf)
        publish += [
            f"          mkdir -p /tmp/itch/{name}",
            f"          cp {pdf} /tmp/itch/{name}/",
            f'          /tmp/butler/butler push /tmp/itch/{name} "$ITCH_TARGET:{name}" --userversion "$RELEASE_TAG"',
        ]

    tokens = {
        "%%PROJECT%%": cfg["project"],
        "%%READING_SOURCE%%": cfg["reading_source"],
        "%%READING_PDF%%": cfg["reading_pdf"],
        "%%PRINT_PDF%%": cfg["print_pdf"],
        "%%EXTRA_RENDER_STEPS%%": "".join(render_steps),
        "%%EXTRA_CHECK_LINES%%": "\n".join(check_lines) + ("\n" if check_lines else ""),
        "%%RELEASE_FILES%%": " \\\n            ".join(release_files),
        "%%PUBLISH_BODY%%": "\n".join(publish) + "\n",
    }

    text = open(TEMPLATE).read()
    for token, value in tokens.items():
        text = text.replace(token, value)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(text)
    print(f"wrote {args.out}")

    r = subprocess.run([sys.executable, CHECK, args.out])
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
