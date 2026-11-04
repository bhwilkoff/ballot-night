"""North Carolina adapter (NC State Board of Elections ENR).

Feed: https://er.ncsbe.gov/enr/20261103/data/results_0.txt
  JSON array, one row per candidate statewide (county 0). Fields: cnm=contest name, bnm=ballot name,
  pty=party, vct=votes, pct=fraction, prt/ptl=precincts reported/total.
Human page: https://er.ncsbe.gov/?election_dt=11/03/2026&county_id=0&office=FED&contest=0
Notes: feed has no winner flag -> winnerDeclared is always None.
"""
import json
import urllib.request

UA = "ballot-night-tracker/1.0 (personal results dashboard)"
FEED = "https://er.ncsbe.gov/enr/20261103/data/results_0.txt"
PAGE = "https://er.ncsbe.gov/?election_dt=11/03/2026&county_id=0&office=FED&contest=0"
RACES = {"sen-nc": "US SENATE (VOTE FOR 1)"}


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8-sig"))


def fetch():
    rows = _get(FEED)
    out = {}
    for rid, cnm in RACES.items():
        rs = [r for r in rows if r.get("cnm") == cnm]
        if not rs:
            continue
        total = sum(int(r["vct"]) for r in rs) or 1
        cands = sorted(
            ({"name": r["bnm"], "party": r.get("pty") or None, "votes": int(r["vct"]),
              "pct": round(100.0 * int(r["vct"]) / total, 2)} for r in rs),
            key=lambda c: -c["votes"])
        prt, ptl = int(rs[0]["prt"]), int(rs[0]["ptl"])
        out[rid] = {
            "type": "cand",
            "contest": cnm.split(" (")[0],
            "candidates": cands,
            "reporting": f"{prt} of {ptl} precincts reporting",
            "source": "NC SBE",
            "sourceUrl": PAGE,
            "winnerDeclared": None,
        }
    return out


if __name__ == "__main__":
    print(json.dumps(fetch(), indent=1))
