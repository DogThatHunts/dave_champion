"""Shared inter-Treasury-Decision relationship data (curated in td_relations.json).

Both build_register.py and build_td_markdown.py import this so the register and
the per-TD detail pages state the same "supersedes / superseded by / amends /
amended by" relationships. Reverse direction is derived here, not hand-maintained.
"""
import json
import os

_DIR = os.path.dirname(os.path.abspath(__file__))
REVERSE = {
    "supersedes": "superseded by",
    "amends": "amended by",
}
VERB_LABEL = {"supersedes": "Supersedes", "superseded by": "Superseded by",
              "amends": "Amends", "amended by": "Amended by"}


def load_relations():
    """Return {num: [ {verb, to, basis}, ... ]} covering both directions."""
    with open(os.path.join(_DIR, "td_relations.json"), encoding="utf-8") as f:
        rels = json.load(f).get("relations", [])
    out = {}
    for r in rels:
        out.setdefault(r["from"], []).append(
            {"verb": r["verb"], "to": r["to"], "basis": r.get("basis", "")})
        out.setdefault(r["to"], []).append(
            {"verb": REVERSE[r["verb"]], "to": r["from"], "basis": r.get("basis", "")})
    return out
