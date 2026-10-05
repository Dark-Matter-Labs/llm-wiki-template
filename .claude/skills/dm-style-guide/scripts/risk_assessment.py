#!/usr/bin/env python3
"""
risk_assessment.py — compute the required peer-review level for a Dm output
from the Publishing Guide's three tests (irreversibility, exposure, sensitivity).

The mapping is defined by the guide, so this is deterministic and reliable —
it is not a judgment call about *your* answers, only about the consequence of
them. Classifying irreversibility/exposure/sensitivity is still your judgment.

Interactive:
    python risk_assessment.py

Non-interactive (for scripting / re-runs):
    python risk_assessment.py \
        --irreversibility high \
        --exposure moderate \
        --sensitivity misrepresent unseen-partner-work \
        --json

Sensitivity flags (pass any that apply):
    politically-sensitive | misrepresent   -> could be politically sensitive or
                                              misrepresent Dm's position
    unseen-partner-work                    -> draws on a colleague's/partner's
                                              work they have not yet seen
    lived-experience | icip                -> lived experience, sensitive data,
                                              community voices, or Indigenous CIP
    confidential-disclosure                -> info under explicit/implicit
                                              confidentiality (NDA, Chatham House,
                                              private conversation)
    contested-stance                       -> new/contested stance wildly
                                              different from prior Dm publishing
"""

import argparse
import json
import sys

IRREVERSIBILITY = ("low", "medium", "high")
EXPOSURE = ("contained", "moderate", "high")
SENSITIVITY_FLAGS = {
    "politically-sensitive": "Could be politically sensitive or misrepresent Dm's position",
    "misrepresent": "Could be politically sensitive or misrepresent Dm's position",
    "unseen-partner-work": "Draws on a colleague's/partner's work they have not yet seen",
    "lived-experience": "Lived experience, sensitive data, community voices, or Indigenous CIP",
    "icip": "Lived experience, sensitive data, community voices, or Indigenous CIP",
    "confidential-disclosure": "Reveals info disclosed under confidentiality (NDA/Chatham House/private)",
    "contested-stance": "New/contested stance wildly different from prior Dm publishing",
}


def decide(irreversibility, exposure, sensitivity_flags):
    """Return (level, reason) per the Publishing Guide Step 1 table."""
    flags = sorted(set(sensitivity_flags))
    if irreversibility == "high" or exposure == "high" or flags:
        drivers = []
        if irreversibility == "high":
            drivers.append("high irreversibility")
        if exposure == "high":
            drivers.append("high exposure")
        if flags:
            drivers.append("sensitivity flag(s): " + ", ".join(flags))
        return (
            "structured",
            "Structured peer review — identify 1–2 reviewers (one domain expert, "
            "one with Dm brand/positioning knowledge) AT THE START of the work, "
            "not the end. Triggered by: " + "; ".join(drivers) + ".",
        )
    if irreversibility == "medium" or exposure == "moderate":
        driver = "medium irreversibility" if irreversibility == "medium" else "moderate exposure"
        return (
            "one_peer",
            f"Ask at least one informed peer to review. One is enough. "
            f"Triggered by: {driver}.",
        )
    return (
        "proceed",
        "Proceed. No peer review required by risk level — still complete the "
        "pre-publication checklist (Step 3).",
    )


def ask_choice(prompt, options):
    opts = "/".join(options)
    while True:
        val = input(f"{prompt} [{opts}]: ").strip().lower()
        if val in options:
            return val
        print(f"  Please answer one of: {opts}")


def ask_yes(prompt):
    while True:
        val = input(f"{prompt} (y/n): ").strip().lower()
        if val in ("y", "yes"):
            return True
        if val in ("n", "no"):
            return False
        print("  Please answer y or n.")


def interactive():
    print("\nDm publishing risk assessment (Publishing Guide, Step 1)\n")
    irr = ask_choice(
        "Irreversibility — if wrong, how easy to correct after publication?\n"
        "  low = internal doc, easy to edit | medium = article, already circulated |"
        " high = grant/policy paper, cannot recall",
        IRREVERSIBILITY,
    )
    exp = ask_choice(
        "Exposure — who sees it, how far does it travel?\n"
        "  contained = single funder, no public | moderate = Dm social channel |"
        " high = major launch/keynote/media",
        EXPOSURE,
    )
    print("\nSensitivity — answer each:")
    unique_questions = [
        ("politically-sensitive", "Could it be politically sensitive or misrepresent Dm's position?"),
        ("unseen-partner-work", "Does it draw on a colleague's/partner's work they have not yet seen?"),
        ("lived-experience", "Does it touch lived experience, sensitive data, community voices, or Indigenous CIP?"),
        ("confidential-disclosure", "Does it reveal info disclosed under confidentiality (NDA/Chatham House/private)?"),
        ("contested-stance", "Is it a new/contested stance wildly different from prior Dm publishing?"),
    ]
    flags = [key for key, q in unique_questions if ask_yes("  " + q)]
    level, reason = decide(irr, exp, flags)
    print("\n" + "=" * 60)
    print(f"REVIEW LEVEL: {level.upper()}")
    print(reason)
    print("=" * 60)
    return level, reason, irr, exp, flags


def main():
    ap = argparse.ArgumentParser(description="Dm publishing review-level calculator")
    ap.add_argument("--irreversibility", choices=IRREVERSIBILITY)
    ap.add_argument("--exposure", choices=EXPOSURE)
    ap.add_argument("--sensitivity", nargs="*", default=[],
                    help="space-separated flags; see module docstring")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.irreversibility and args.exposure:
        bad = [f for f in args.sensitivity if f not in SENSITIVITY_FLAGS]
        if bad:
            sys.exit(f"Unknown sensitivity flag(s): {', '.join(bad)}")
        level, reason = decide(args.irreversibility, args.exposure, args.sensitivity)
        if args.json:
            print(json.dumps({
                "irreversibility": args.irreversibility,
                "exposure": args.exposure,
                "sensitivity_flags": sorted(set(args.sensitivity)),
                "review_level": level,
                "reason": reason,
            }, indent=2))
        else:
            print(f"REVIEW LEVEL: {level.upper()}\n{reason}")
    else:
        interactive()


if __name__ == "__main__":
    main()
