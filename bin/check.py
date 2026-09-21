#!/usr/bin/env python3
"""Executable gate for itch-cicd workflows.

Validates a build-release-pdfs.yml against every rule we learned the hard way.
Exits 0 when the workflow is sound, 1 with a list of violations otherwise.

Usage: bin/check.py <workflow.yml>
"""
import re
import sys

BUTLER_URL = "https://broth.itch.zone/butler/linux-amd64/LATEST/archive/default"

RULES = []


def rule(fn):
    RULES.append(fn)
    return fn


@rule
def no_secrets_in_if(text):
    """GitHub Actions rejects secrets.* inside if: conditions."""
    bad = [l.strip() for l in text.splitlines()
           if re.match(r'\s*if:\s*.*secrets\.', l)]
    if bad:
        return ("secrets.* used in if: condition (invalid; gate on "
                "vars.ITCH_TARGET and guard the secret in shell):\n  " +
                "\n  ".join(bad))


@rule
def itch_target_var_gate(text):
    """Butler steps must be inert until ITCH_TARGET is configured."""
    if "vars.ITCH_TARGET" not in text:
        return "no vars.ITCH_TARGET gate: butler steps would fail on unconfigured repos"


@rule
def shell_guard_for_api_key(text):
    """Even with the var gate, the secret may be absent: exit cleanly."""
    if not re.search(r'if\s+\[\s+-z\s+"\$BUTLER_API_KEY"\s+\]', text):
        return 'missing shell guard: if [ -z "$BUTLER_API_KEY" ]; then ... exit 0; fi'


@rule
def butler_from_broth(text):
    if BUTLER_URL not in text:
        return f"butler not installed from the permanent broth URL: {BUTLER_URL}"


@rule
def userversion_on_push(text):
    pushes = [l.strip() for l in text.splitlines() if "butler push" in l]
    if not pushes:
        return "no butler push commands found"
    missing = [p for p in pushes if "--userversion" not in p]
    if missing:
        return ("butler push without --userversion (builds show no version on itch.io):\n  " +
                "\n  ".join(missing))


@rule
def no_unreplaced_tokens(text):
    leftover = sorted(set(re.findall(r'%%[A-Z_]+%%', text)))
    if leftover:
        return "unreplaced template tokens: " + ", ".join(leftover)


@rule
def contents_write_permission(text):
    if not re.search(r'permissions:\s*\n\s+contents:\s*write', text):
        return "missing permissions: contents: write (gh release create needs it)"


@rule
def concurrency_group(text):
    if "concurrency:" not in text:
        return "missing concurrency group (overlapping runs can cut duplicate releases)"


def main():
    path = sys.argv[1]
    text = open(path).read()
    failures = [r(text) for r in RULES]
    failures = [f for f in failures if f]
    if failures:
        print(f"FAIL {path}: {len(failures)} violation(s)")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print(f"OK {path}: all {len(RULES)} rules pass")


if __name__ == "__main__":
    main()
