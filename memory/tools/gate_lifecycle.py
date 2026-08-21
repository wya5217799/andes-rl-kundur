"""Lifecycle manager for load-bearing governance gates (ADR-0020).

Motivation
----------
Many hard gates in ``CLAUDE.md`` are tombstones of specific agent
failures (R246 estimated baseline; CLM-0430 single-metric claims; R291
statement forks; pre-R339 context-compression duplicate rounds).  Some
gates encode scientific/reproducibility epistemology (``locked``) and
stay forever; others encode model-capability assumptions (``soft``) and
can over-freeze the process as models improve.  This tool implements
the per-gate lifecycle: evidence-based demotion hard -> warn ->
advisory, and automatic re-promotion to hard on a flagged recurrence.

Approval is kept off the long-task critical path: ``provisional`` takes
a one-step demotion with no approval and auto-expires after
``provisional_ttl_rounds``; ``grant`` pre-authorizes permanent
demotions for one gate; ``ratify`` turns a provisional demotion
permanent afterwards.  A recorded demotion is authority for ONE
relaxation edit of the prose rule (and its detector) in the same
governance change; it is not itself an enforcement change.  Provisional
authority lapses on expiry, so a file edit made under it must be
ratified or reverted before the TTL ends.

Usage
-----
::

    # List every gate with class / effective state / clean clock / grant
    $ python memory/tools/gate_lifecycle.py list

    # Propose demotions (soft gates whose clean clock passed the threshold)
    $ python memory/tools/gate_lifecycle.py audit

    # Show one gate's registry entry + events
    $ python memory/tools/gate_lifecycle.py show statement-byte-cap

    # No-approval one-step demotion, auto-expiring (soft + provisional_allowed)
    $ python memory/tools/gate_lifecycle.py provisional statement-byte-cap \\
        --evidence "cap blocks this round; 10 clean rounds support a try"

    # Operator turns an active provisional demotion permanent afterwards
    $ python memory/tools/gate_lifecycle.py ratify statement-byte-cap

    # Operator pre-authorizes permanent demotions for one gate
    $ python memory/tools/gate_lifecycle.py grant verdict-line-cap \\
        --evidence "trusted for long mission autonomy"
    $ python memory/tools/gate_lifecycle.py revoke verdict-line-cap

    # Permanent demotion: eligible, pre-granted, or --override (recorded)
    $ python memory/tools/gate_lifecycle.py demote caveman-ai-compactness \\
        --evidence "contract budgets already bound always-loaded files"

    # Record a recurrence of the guarded failure mode; a non-hard soft gate
    # jumps straight back to hard and any provisional is cleared
    # (safety direction, no approval, no expiry)
    $ python memory/tools/gate_lifecycle.py flag statement-byte-cap \\
        --round R420 --evidence "CLM-1234 statement exceeds budget"

    # Record a clean attestation at a round (advances the clean clock)
    $ python memory/tools/gate_lifecycle.py attest plan-first-nontrivial \\
        --round R415 --note "all R415 cross-layer edits went plan-first"

    # Manual re-tightening without a flagged recurrence
    $ python memory/tools/gate_lifecycle.py promote cold-start-budget \\
        --evidence "token budget policy cut again"

Failure modes
-------------
- Missing or malformed registry: read commands exit 0 with a warning
  (robustness rule: return empty, do not crash); write commands exit 2.
- Demoting a ``locked`` gate, an ineligible soft gate without
  ``--override``/grant, or a gate with an active provisional exits 2
  with guidance.
- Round IDs are compared numerically (R420 > R99), never lexically.
- Registry writes go through a temp file + ``os.replace`` so a crashed
  write never leaves a truncated registry.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs" / "repo-hygiene" / "gate-registry.json"
ROUNDS_DIR = ROOT / "memory" / "rounds"

_DEMOTE = {"hard": "warn", "warn": "advisory"}
_ROUND_RE = re.compile(r"^R(\d+)$")


def _round_num(text):
    m = _ROUND_RE.match(str(text).strip())
    return int(m.group(1)) if m else None


def _current_round(reg):
    best = None
    if ROUNDS_DIR.is_dir():
        for p in ROUNDS_DIR.iterdir():
            if p.is_dir():
                n = _round_num(p.name)
                if n is not None and (best is None or n > best):
                    best = n
    if best is None:
        best = _round_num(reg.get("bootstrap_round"))
    return best


def _load():
    if not REGISTRY.is_file():
        return None
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _save(reg):
    tmp = REGISTRY.with_name(REGISTRY.name + ".tmp")
    try:
        tmp.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        os.replace(str(tmp), str(REGISTRY))
        return True
    except OSError:
        return False


def _find(reg, gate_id):
    for g in reg.get("gates", []):
        if g.get("id") == gate_id:
            return g
    return None


def _threshold(reg, g):
    return int(g.get("threshold_rounds",
                     reg.get("default_threshold_rounds", 10)))


def _clean_delta(reg, g):
    cur = _current_round(reg)
    clean = _round_num(g.get("clean_since_round"))
    if cur is None or clean is None:
        return None
    return cur - clean


def _eligible(reg, g):
    if g.get("class") != "soft":
        return False
    if g.get("state") not in ("hard", "warn"):
        return False
    delta = _clean_delta(reg, g)
    return delta is not None and delta >= _threshold(reg, g)


def _round_str(reg):
    cur = _current_round(reg)
    return "R%s" % cur if cur is not None else "R?"


def _active_provisional(reg, g):
    """Return the provisional block if it exists and has not expired."""
    prov = g.get("provisional")
    if not prov:
        return None
    cur = _current_round(reg)
    until = _round_num(prov.get("until_round"))
    if cur is not None and until is not None and cur <= until:
        return prov
    return None


def _effective_state(reg, g):
    prov = _active_provisional(reg, g)
    if prov and g.get("class") == "soft":
        return prov.get("to", g.get("state", "hard"))
    return g.get("state", "hard")


def cmd_list(reg, args):
    if reg is None:
        print("WARN: registry missing or malformed: %s" % REGISTRY)
        return 0
    print("%-26s %-7s %-12s %-6s %-6s %-6s %s" %
          ("id", "class", "state", "grant", "clean", "thresh", "anchor"))
    for g in reg.get("gates", []):
        state = _effective_state(reg, g)
        prov = g.get("provisional")
        if prov is not None:
            if _active_provisional(reg, g):
                state += "(prov)"
            else:
                state += "(prov-exp)"
        grant = "pi" if g.get("grant") else "-"
        thresh = str(_threshold(reg, g)) if g.get("class") == "soft" else "-"
        eligible = _eligible(reg, g)
        print("%-26s %-7s %-12s %-6s %-6s %-6s %s%s" % (
            g.get("id", "?"),
            g.get("class", "?"),
            state,
            grant,
            str(g.get("clean_since_round", "?")),
            thresh,
            g.get("anchor", ""),
            "  [ELIGIBLE]" if eligible else "",
        ))
    return 0


def cmd_audit(reg, args):
    if reg is None:
        print("WARN: registry missing or malformed: %s" % REGISTRY)
        return 0
    print("current round: %s" % _round_str(reg))
    props = []
    provs = []
    for g in reg.get("gates", []):
        if not _eligible(reg, g):
            continue
        delta = _clean_delta(reg, g)
        props.append(
            "PROPOSAL: demote %-26s %s -> %s (clean %d rounds >= threshold %d; detector: %s)"
            % (g.get("id", "?"), g["state"], _DEMOTE[g["state"]], delta,
               _threshold(reg, g), g.get("detector", "?")))
        if g.get("provisional_allowed") and g["state"] == "hard" \
                and _active_provisional(reg, g) is None:
            provs.append(
                "PROVISIONAL-CANDIDATE: %-26s (no approval; TTL %d rounds)"
                % (g.get("id", "?"),
                   int(reg.get("provisional_ttl_rounds", 10))))
    if props:
        for line in props:
            print(line)
    if provs:
        for line in provs:
            print(line)
    if not props and not provs:
        print("NO ELIGIBLE DEMOTIONS (soft hard/warn gates below clean threshold)")
    return 0


def cmd_show(reg, args):
    if reg is None:
        print("WARN: registry missing or malformed: %s" % REGISTRY)
        return 0
    g = _find(reg, args.gate_id)
    if g is None:
        print("ERROR: unknown gate id %r (run list)" % args.gate_id,
              file=sys.stderr)
        return 2
    print("id: %s  class: %s  state: %s  effective: %s  clean_since_round: %s" % (
        g.get("id", "?"), g.get("class", "?"), g.get("state", "?"),
        _effective_state(reg, g), g.get("clean_since_round", "?")))
    print("anchor: %s" % g.get("anchor", ""))
    print("detector: %s" % g.get("detector", ""))
    print("motivating_incidents: %s"
          % ", ".join(g.get("motivating_incidents", [])))
    if g.get("why_locked"):
        print("why_locked: %s" % g["why_locked"])
    if g.get("failure_mode"):
        print("failure_mode: %s" % g["failure_mode"])
    if g.get("provisional_allowed") is not None:
        print("provisional_allowed: %s" % g["provisional_allowed"])
    if g.get("provisional"):
        print("provisional: %s (until %s, active=%s)" % (
            g["provisional"].get("to", "?"),
            g["provisional"].get("until_round", "?"),
            _active_provisional(reg, g) is not None))
    if g.get("grant"):
        print("grant: by %s at %s" % (g["grant"].get("by", "?"),
                                      g["grant"].get("at", "?")))
    print("events:")
    for e in g.get("events", []):
        move = ("  %s->%s" % (e["from"], e["to"])) if "to" in e else ""
        extra = "  cleared-provisional" if e.get("cleared_provisional") else ""
        print("  - [%s] %s%s%s  at %s" % (
            e.get("round", "?"), e.get("type", "?"), move, extra,
            e.get("at", "?")))
        if e.get("evidence"):
            print("      evidence: %s" % e["evidence"])
        if e.get("note"):
            print("      note: %s" % e["note"])
    return 0


def cmd_demote(reg, args):
    if reg is None:
        print("ERROR: registry missing or malformed: %s" % REGISTRY,
              file=sys.stderr)
        return 2
    g = _find(reg, args.gate_id)
    if g is None:
        print("ERROR: unknown gate id %r (run list)" % args.gate_id,
              file=sys.stderr)
        return 2
    if g.get("class") != "soft":
        print("ERROR: gate %r is locked (science/reproducibility/human-facing); never demotable"
              % args.gate_id, file=sys.stderr)
        return 2
    if g.get("state") not in ("hard", "warn"):
        print("ERROR: gate %r state=%s; nothing to demote"
              % (args.gate_id, g.get("state")), file=sys.stderr)
        return 2
    if _active_provisional(reg, g) is not None:
        print("ERROR: gate %r has an active provisional until %s; ratify it or wait for expiry"
              % (args.gate_id, g["provisional"].get("until_round", "?")),
              file=sys.stderr)
        return 2
    via = None
    if args.override:
        via = "override"
    elif g.get("grant"):
        via = "grant"
    elif _eligible(reg, g):
        via = "eligible"
    else:
        print("ERROR: gate %r not eligible (run audit); options: grant, provisional (if allowed), or --override with recorded evidence"
              % args.gate_id, file=sys.stderr)
        return 2
    old, new = g["state"], _DEMOTE[g["state"]]
    g["state"] = new
    g.setdefault("events", []).append({
        "type": "demote", "round": _round_str(reg), "from": old, "to": new,
        "evidence": args.evidence, "via": via,
        "at": _dt.date.today().isoformat(),
    })
    if not _save(reg):
        print("ERROR: failed to write registry", file=sys.stderr)
        return 2
    print("DEMOTED %s: %s -> %s via %s (recorded; authorizes ONE relaxation edit of the prose rule + detector)"
          % (args.gate_id, old, new, via))
    return 0


def cmd_promote(reg, args):
    if reg is None:
        print("ERROR: registry missing or malformed: %s" % REGISTRY,
              file=sys.stderr)
        return 2
    g = _find(reg, args.gate_id)
    if g is None:
        print("ERROR: unknown gate id %r (run list)" % args.gate_id,
              file=sys.stderr)
        return 2
    old = g.get("state", "hard")
    cleared = g.get("provisional") is not None
    g["state"] = "hard"
    g["provisional"] = None
    g.setdefault("events", []).append({
        "type": "promote", "round": _round_str(reg), "from": old, "to": "hard",
        "evidence": args.evidence, "cleared_provisional": cleared,
        "at": _dt.date.today().isoformat(),
    })
    if not _save(reg):
        print("ERROR: failed to write registry", file=sys.stderr)
        return 2
    print("PROMOTED %s: %s -> hard%s" % (
        args.gate_id, old, " (provisional cleared)" if cleared else ""))
    return 0


def cmd_flag(reg, args):
    if reg is None:
        print("ERROR: registry missing or malformed: %s" % REGISTRY,
              file=sys.stderr)
        return 2
    g = _find(reg, args.gate_id)
    if g is None:
        print("ERROR: unknown gate id %r (run list)" % args.gate_id,
              file=sys.stderr)
        return 2
    if _round_num(args.round) is None:
        print("ERROR: --round must look like R<digits>", file=sys.stderr)
        return 2
    old = g.get("state", "hard")
    cleared = g.get("provisional") is not None
    g["clean_since_round"] = args.round
    g["provisional"] = None
    if g.get("class") == "soft" and old != "hard":
        g["state"] = "hard"
    g.setdefault("events", []).append({
        "type": "flag", "round": args.round, "from": old, "to": g["state"],
        "evidence": args.evidence, "cleared_provisional": cleared,
        "at": _dt.date.today().isoformat(),
    })
    if not _save(reg):
        print("ERROR: failed to write registry", file=sys.stderr)
        return 2
    suffix = ""
    if old != g["state"]:
        suffix = "; auto re-promoted %s -> %s (recurrence observed)" % (old, g["state"])
    if cleared:
        suffix += "; provisional cleared"
    print("FLAGGED %s at %s: recurrence recorded%s" % (args.gate_id, args.round, suffix))
    return 0


def cmd_attest(reg, args):
    if reg is None:
        print("ERROR: registry missing or malformed: %s" % REGISTRY,
              file=sys.stderr)
        return 2
    g = _find(reg, args.gate_id)
    if g is None:
        print("ERROR: unknown gate id %r (run list)" % args.gate_id,
              file=sys.stderr)
        return 2
    if g.get("class") != "soft":
        print("ERROR: gate %r is locked; locked gates need no clean clock"
              % args.gate_id, file=sys.stderr)
        return 2
    if _round_num(args.round) is None:
        print("ERROR: --round must look like R<digits>", file=sys.stderr)
        return 2
    g["clean_since_round"] = args.round
    g.setdefault("events", []).append({
        "type": "attest", "round": args.round,
        "note": args.note, "at": _dt.date.today().isoformat(),
    })
    if not _save(reg):
        print("ERROR: failed to write registry", file=sys.stderr)
        return 2
    print("ATTESTED %s clean at %s" % (args.gate_id, args.round))
    return 0


def cmd_provisional(reg, args):
    if reg is None:
        print("ERROR: registry missing or malformed: %s" % REGISTRY,
              file=sys.stderr)
        return 2
    g = _find(reg, args.gate_id)
    if g is None:
        print("ERROR: unknown gate id %r (run list)" % args.gate_id,
              file=sys.stderr)
        return 2
    if g.get("class") != "soft":
        print("ERROR: gate %r is locked; never demotable" % args.gate_id,
              file=sys.stderr)
        return 2
    if g.get("provisional_allowed") is False:
        print("ERROR: gate %r has provisional_allowed=false (resource/safety guard); permanent path only"
              % args.gate_id, file=sys.stderr)
        return 2
    if g.get("state") != "hard":
        print("ERROR: gate %r state=%s; provisional only applies from hard"
              % (args.gate_id, g.get("state")), file=sys.stderr)
        return 2
    if _active_provisional(reg, g) is not None:
        print("ERROR: gate %r already has an active provisional until %s"
              % (args.gate_id, g["provisional"].get("until_round", "?")),
              file=sys.stderr)
        return 2
    if not _eligible(reg, g):
        print("ERROR: gate %r not eligible (run audit); provisional still needs the clean-clock evidence"
              % args.gate_id, file=sys.stderr)
        return 2
    cur = _current_round(reg)
    ttl = int(reg.get("provisional_ttl_rounds", 10))
    if cur is None:
        print("ERROR: cannot resolve current round", file=sys.stderr)
        return 2
    until = "R%d" % (cur + ttl)
    g["provisional"] = {
        "to": "warn", "from": "hard", "until_round": until,
        "evidence": args.evidence, "at": _dt.date.today().isoformat(),
    }
    g.setdefault("events", []).append({
        "type": "provisional", "round": _round_str(reg), "from": "hard",
        "to": "warn", "until_round": until, "evidence": args.evidence,
        "at": _dt.date.today().isoformat(),
    })
    if not _save(reg):
        print("ERROR: failed to write registry", file=sys.stderr)
        return 2
    print("PROVISIONAL %s: hard -> warn until %s (no approval; expires automatically; ratify to make permanent)"
          % (args.gate_id, until))
    return 0


def cmd_ratify(reg, args):
    if reg is None:
        print("ERROR: registry missing or malformed: %s" % REGISTRY,
              file=sys.stderr)
        return 2
    g = _find(reg, args.gate_id)
    if g is None:
        print("ERROR: unknown gate id %r (run list)" % args.gate_id,
              file=sys.stderr)
        return 2
    prov = _active_provisional(reg, g)
    if prov is None:
        if g.get("provisional") is not None:
            print("ERROR: gate %r provisional expired at %s; it has already lapsed"
                  % (args.gate_id, g["provisional"].get("until_round", "?")),
                  file=sys.stderr)
        else:
            print("ERROR: gate %r has no provisional to ratify" % args.gate_id,
                  file=sys.stderr)
        return 2
    g["state"] = prov.get("to", "warn")
    g["provisional"] = None
    g.setdefault("events", []).append({
        "type": "ratify", "round": _round_str(reg),
        "from": prov.get("from", "hard"), "to": prov.get("to", "warn"),
        "at": _dt.date.today().isoformat(),
    })
    if not _save(reg):
        print("ERROR: failed to write registry", file=sys.stderr)
        return 2
    print("RATIFIED %s: provisional -> permanent %s" % (args.gate_id, g["state"]))
    return 0


def cmd_grant(reg, args):
    if reg is None:
        print("ERROR: registry missing or malformed: %s" % REGISTRY,
              file=sys.stderr)
        return 2
    g = _find(reg, args.gate_id)
    if g is None:
        print("ERROR: unknown gate id %r (run list)" % args.gate_id,
              file=sys.stderr)
        return 2
    if g.get("class") != "soft":
        print("ERROR: gate %r is locked; grants apply to soft gates only"
              % args.gate_id, file=sys.stderr)
        return 2
    g["grant"] = {"by": "pi", "evidence": args.evidence,
                  "at": _dt.date.today().isoformat()}
    g.setdefault("events", []).append({
        "type": "grant", "round": _round_str(reg), "evidence": args.evidence,
        "at": _dt.date.today().isoformat(),
    })
    if not _save(reg):
        print("ERROR: failed to write registry", file=sys.stderr)
        return 2
    print("GRANTED %s: eligible permanent demotions no longer stop for approval"
          % args.gate_id)
    return 0


def cmd_revoke(reg, args):
    if reg is None:
        print("ERROR: registry missing or malformed: %s" % REGISTRY,
              file=sys.stderr)
        return 2
    g = _find(reg, args.gate_id)
    if g is None:
        print("ERROR: unknown gate id %r (run list)" % args.gate_id,
              file=sys.stderr)
        return 2
    if not g.get("grant"):
        print("ERROR: gate %r has no active grant" % args.gate_id,
              file=sys.stderr)
        return 2
    g["grant"] = None
    g.setdefault("events", []).append({
        "type": "revoke", "round": _round_str(reg),
        "at": _dt.date.today().isoformat(),
    })
    if not _save(reg):
        print("ERROR: failed to write registry", file=sys.stderr)
        return 2
    print("REVOKED grant on %s" % args.gate_id)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="gate_lifecycle.py",
        description="Governance gate lifecycle (ADR-0020): evidence-based "
                    "demotion of soft model-capability gates, automatic "
                    "re-promotion on recurrence, approval-free provisional "
                    "and grant paths for long tasks.")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list all gates with class/effective state/grant/clean clock")
    sub.add_parser("audit", help="propose demotions and provisional candidates")

    s = sub.add_parser("show", help="show one gate's registry entry + events")
    s.add_argument("gate_id")

    d = sub.add_parser("demote", help="permanent demotion (eligible/grant/override)")
    d.add_argument("gate_id")
    d.add_argument("--evidence", required=True,
                   help="recorded reason this demotion is justified")
    d.add_argument("--override", action="store_true",
                   help="demote before eligibility; recorded and visible")

    pr = sub.add_parser("promote", help="manual re-tightening to hard")
    pr.add_argument("gate_id")
    pr.add_argument("--evidence", default="manual re-tightening")

    f = sub.add_parser("flag", help="record a recurrence of the failure mode")
    f.add_argument("gate_id")
    f.add_argument("--round", required=True, help="round id, e.g. R420")
    f.add_argument("--evidence", required=True)

    a = sub.add_parser("attest", help="record a clean round (advances clock)")
    a.add_argument("gate_id")
    a.add_argument("--round", required=True, help="round id, e.g. R415")
    a.add_argument("--note", default="clean attestation")

    pv = sub.add_parser("provisional", help="no-approval one-step demotion with TTL")
    pv.add_argument("gate_id")
    pv.add_argument("--evidence", required=True)

    rt = sub.add_parser("ratify", help="turn an active provisional into permanent")
    rt.add_argument("gate_id")

    gr = sub.add_parser("grant", help="pre-authorize permanent demotions for one gate")
    gr.add_argument("gate_id")
    gr.add_argument("--evidence", required=True)

    rv = sub.add_parser("revoke", help="remove a gate's grant")
    rv.add_argument("gate_id")

    args = p.parse_args(argv)
    reg = _load()
    handlers = {
        "list": cmd_list, "audit": cmd_audit, "show": cmd_show,
        "demote": cmd_demote, "promote": cmd_promote,
        "flag": cmd_flag, "attest": cmd_attest,
        "provisional": cmd_provisional, "ratify": cmd_ratify,
        "grant": cmd_grant, "revoke": cmd_revoke,
    }
    return handlers[args.command](reg, args)


if __name__ == "__main__":
    sys.exit(main())
