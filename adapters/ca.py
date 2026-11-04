"""California adapter (CA Secretary of State, Nov 3 2026 general).

Feeds (public JSON API behind electionresults.sos.ca.gov):
  https://api.sos.ca.gov/returns/us-rep/district/{N}   -> U.S. House district N (post-Prop 50 lines)
  https://api.sos.ca.gov/returns/ballot-measures       -> all statewide propositions
Human page: https://electionresults.sos.ca.gov/returns/us-rep/district/{N}, .../returns/ballot-measures
Notes: votes are strings with commas in candidate feeds; measures use plain digits.
  meas-ca40 = Prop 40 "Imposes One-Time Tax On Certain Taxpayers" (the billionaire wealth tax).
  The feed does not flag winners, so winnerDeclared is always None.
"""
import json
import urllib.request

UA = "ballot-night-tracker/1.0 (personal results dashboard)"
API = "https://api.sos.ca.gov/returns/"
WEB = "https://electionresults.sos.ca.gov/returns/"
HOUSE = {"hse-ca13": 13, "hse-ca22": 22, "hse-ca45": 45}
MEASURES = {"meas-ca40": "40"}


def _get(path):
    req = urllib.request.Request(API + path, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def _num(s):
    return int(str(s).replace(",", "").strip() or 0)


def fetch():
    out = {}
    for rid, dist in HOUSE.items():
        path = f"us-rep/district/{dist}"
        d = _get(path)
        cands = [{"name": c["Name"], "party": (c.get("Party") or "").upper()[:3],
                  "votes": _num(c["Votes"])} for c in d.get("candidates", [])]
        total = sum(c["votes"] for c in cands) or 1
        for c in cands:
            c["pct"] = round(100.0 * c["votes"] / total, 1)
        cands.sort(key=lambda c: -c["votes"])
        out[rid] = {"type": "cand", "contest": d.get("raceTitle", f"U.S. House District {dist}").split(" - ")[0],
                    "candidates": cands, "reporting": d.get("Reporting", ""),
                    "source": "CA SOS", "sourceUrl": WEB + path, "winnerDeclared": None}
    d = _get("ballot-measures")
    by_num = {m["Number"].lstrip("0"): m for m in d.get("ballot-measures", [])}
    for rid, num in MEASURES.items():
        m = by_num.get(num)
        if not m:
            continue
        y, n = _num(m["yesVotes"]), _num(m["noVotes"])
        tot = (y + n) or 1
        out[rid] = {"type": "measure", "contest": f"Proposition {num}: {m['Name']}",
                    "yesPct": round(100.0 * y / tot, 1), "noPct": round(100.0 * n / tot, 1),
                    "yesVotes": y, "noVotes": n, "threshold": 50,
                    "reporting": d.get("Reporting", ""), "source": "CA SOS",
                    "sourceUrl": WEB + "ballot-measures"}
    return out


if __name__ == "__main__":
    print(json.dumps(fetch(), indent=1))
