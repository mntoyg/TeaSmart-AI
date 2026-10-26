"""Emit the parity fixtures the browser's leaf gate is checked against.

The browser has to apply the same rule as `segment.vegetation_fraction`, and
the last time a rule was implemented twice the two copies disagreed: the
quality gates diverged until the browser refused frames the server
deliberately accepted. So the rule is not described to the client, it is
pinned.

Most cases are a single synthetic pixel. Two of them sit either side of the
index floor, a thousandth apart, chosen by search so that a port which rounds
differently or gets the strictness of the comparison wrong fails a named case
rather than being quietly a little bit off on photographs where nobody would
notice. The rest are the colours the gate exists to tell apart, each with its
measured index in the note.

    ./backend/.venv/Scripts/python.exe scripts/make_leaf_fixtures.py

Every expected value is computed by the code production runs, and each one is
checked against what the case claims before anything is written, so this file
cannot drift from the implementation it pins.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from app.core.config import Settings  # noqa: E402
from app.services.segment import vegetation_fraction  # noqa: E402

OUT = REPO / "frontend" / "src" / "test" / "fixtures" / "leaf-fraction.json"

# (name, why it is here, expected fraction, rows of RGB triples)
CASES: list[tuple[str, str, float, list[list[tuple[int, int, int]]]]] = [
    ("sunlit leaf", "an ordinary leaf pixel; index 0.562", 1.0, [[(54, 122, 58)]]),
    (
        "dark leaf on lilac",
        "measured from a Mendeley photograph. Index 0.152, so it counts - "
        "while stage 2's absolute rule scores this same real labelled leaf at "
        "zero. This case is why the gate normalises and why a floor could be "
        "set above zero at all",
        1.0,
        [[(31, 40, 33)]],
    ),
    ("lilac backdrop", "what those leaves are photographed on; index -0.130", 0.0, [[(199, 176, 232)]]),
    ("bare soil", "index -0.026", 0.0, [[(92, 74, 62)]]),
    ("human skin", "a hand in frame, the commonest non-leaf photograph; index -0.038", 0.0, [[(198, 152, 124)]]),
    (
        "white paper",
        "index 0.0055: faintly green and nowhere near the floor. A leaf "
        "photographed on paper counts for the leaf, not for the paper",
        0.0,
        [[(244, 244, 240)]],
    ),
    ("index just under the floor", "0.049931, and the test is strict", 0.0, [[(234, 252, 234)]]),
    ("index just over the floor", "0.051389", 1.0, [[(233, 252, 234)]]),
    (
        "one passing pixel in four",
        "the ratio itself, not the index",
        0.25,
        [[(54, 122, 58), (92, 74, 62)], [(92, 74, 62), (92, 74, 62)]],
    ),
]


def main() -> int:
    settings = Settings()
    cases = []
    for name, why, expected, rows in CASES:
        rgb = numpy.array(rows, dtype=numpy.uint8)
        height, width = rgb.shape[:2]
        measured = round(vegetation_fraction(rgb, settings), 6)
        if measured != expected:
            raise SystemExit(
                f"{name!r} claims {expected} but measures {measured}. A boundary case "
                "that does not sit where its name says teaches a port nothing; fix the "
                "colour or the claim before writing the fixture."
            )
        cases.append(
            {
                "name": name,
                "why": why,
                "width": width,
                "height": height,
                "rgb": [int(value) for value in rgb.reshape(-1)],
                "fraction": measured,
            }
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "generated_by": "scripts/make_leaf_fixtures.py",
                "settings": {"veg_index_min": settings.veg_index_min},
                "cases": cases,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    for case in cases:
        print(f"{case['name']:<30}{case['fraction']:>10.4f}")
    print(f"\n{len(cases)} cases written to {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
