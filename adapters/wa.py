"""Washington (WA) adapter - 2026-11-03 general election.

Official source: WA Secretary of State results site (Enhanced Voting platform),
https://results.vote.wa.gov  -> redirects to https://results.votewa.gov/results/public/washington

Feeds (JSON, discovered from the site's Angular bundle):
  1. https://results.votewa.gov/results/public/api/jurisdictions/washington
       -> "elections": [{"publicElectionId": "20261103", "electionDate": "2026-11-03", ...}, ...]
       used to discover the election id for 2026-11-03 (falls back to "20261103").
  2. https://results.votewa.gov/results/public/api/elections/washington/<id>/data
       -> "ballotItems": every contest with summaryResults.ballotOptions[].voteCount,
          reportingStatus.{reportingUnits,totalUnits} (units = counties).
Human-viewable page: https://results.votewa.gov/results/public/washington/elections/<id>

Race ids:
  hse-wa03     "Congressional District 3 - U.S. Representative"
  meas-wa2124  The app's "Initiative 2124" label is wrong. The real 2026 state measure on
               income/wealth taxation is "Initiative Measure No. IP26-645" (repeal 9.9% tax on
               individual income over $1M; prohibit income taxes). Matched by name, then by
               ballot text ("individual income").
  meas-walgw   The real Let's Go Washington parental-rights measure is
               "Initiative Measure No. IL26-001" (re-enacts parents' rights law I-2081 as
               originally enacted). Matched by name, then by ballot text ("parental rights").
WA has no supermajority requirement for these initiatives (threshold 50).
WA does not flag winners in the feed before certification (isWinner is null), so
winnerDeclared is only set if isWinner is true.
"""
import json
import re
import urllib.request

UA = "ballot-night-tracker/1.0 (personal results dashboard)"
API = "https://results.votewa.gov/results/public/api"
PAGE = "https://results.votewa.gov/results/public/washington/elections/{eid}"
ELECTION_DATE = "2026-11-03"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))


def _t(lst):
    if not lst:
        return ""
    for x in lst:
        if x.get("languageId") == "en":
            return x.get("text") or ""
    return lst[0].get("text") or ""


def _election_id():
    try:
        j = _get(f"{API}/jurisdictions/washington")
        for e in j.get("elections") or []:
            if e.get("electionDate") == ELECTION_DATE:
                return e["publicElectionId"]
    except Exception:
        pass
    return ELECTION_DATE.replace("-", "")


def _reporting(b):
    rs = b.get("reportingStatus") or {}
    if rs.get("totalUnits"):
        return f"{rs.get('reportingUnits', 0)} of {rs['totalUnits']} counties reporting (unofficial)"
    return "unofficial"


def _cand(b, eid):
    opts = b["summaryResults"]["ballotOptions"]
    total = sum(o.get("voteCount") or 0 for o in opts)
    cands = []
    winner = None
    for o in opts:
        v = o.get("voteCount") or 0
        cands.append({
            "name": _t(o.get("name")),
            "party": (o.get("party") or {}).get("abbreviation") or ("W/I" if o.get("isWriteIn") else ""),
            "votes": v,
            "pct": round(100.0 * v / total, 1) if total else 0.0,
        })
        if o.get("isWinner") is True:
            winner = _t(o.get("name"))
    cands.sort(key=lambda c: -c["votes"])
    return {
        "type": "cand",
        "contest": _t(b.get("name")),
        "candidates": cands,
        "reporting": _reporting(b),
        "source": "WA SOS",
        "sourceUrl": PAGE.format(eid=eid),
        "winnerDeclared": winner,
    }


def _measure(b, eid):
    yes = no = 0
    for o in b["summaryResults"]["ballotOptions"]:
        n = _t(o.get("name")).strip().lower()
        if n.endswith("yes") or n.startswith("approved"):
            yes += o.get("voteCount") or 0
        elif n.endswith("no") or n.startswith("rejected"):
            no += o.get("voteCount") or 0
    tot = yes + no
    desc = re.sub(r"<[^>]+>", " ", _t(b.get("referendum")))
    m = re.search(r"\bconcerns ([^.]+)\.", re.sub(r"\s+", " ", desc))
    name = _t(b.get("name"))
    return {
        "type": "measure",
        "contest": f"{name} ({m.group(1).strip()})" if m else name,
        "yesPct": round(100.0 * yes / tot, 1) if tot else 0.0,
        "noPct": round(100.0 * no / tot, 1) if tot else 0.0,
        "yesVotes": yes,
        "noVotes": no,
        "threshold": 50,
        "reporting": _reporting(b),
        "source": "WA SOS",
        "sourceUrl": PAGE.format(eid=eid),
    }


def _find_measure(items, number, text_re):
    state = [b for b in items if b.get("contestType") == "BallotMeasure"
             and _t(b.get("name")).startswith("Initiative Measure No.")]
    for b in state:
        if number in _t(b.get("name")):
            return b
    for b in state:
        if re.search(text_re, _t(b.get("referendum")), re.I):
            return b
    return None


def fetch():
    eid = _election_id()
    data = _get(f"{API}/elections/washington/{eid}/data")
    items = [b for b in data.get("ballotItems") or [] if not b.get("parentId")]
    out = {}
    for b in items:
        if b.get("contestType") == "Candidate" and re.match(
                r"Congressional District 3 - U\.S\. Representative$", _t(b.get("name")).strip()):
            out["hse-wa03"] = _cand(b, eid)
            break
    m = _find_measure(items, "IP26-645", r"individual income")
    if m:
        out["meas-wa2124"] = _measure(m, eid)
    m = _find_measure(items, "IL26-001", r"parental rights|rights of parents")
    if m:
        out["meas-walgw"] = _measure(m, eid)
    return out


if __name__ == "__main__":
    print(json.dumps(fetch(), indent=1))
