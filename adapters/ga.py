"""Georgia adapter (GA Secretary of State, Enhanced Voting results platform at results.sos.ga.gov).

Feeds:
  https://results.sos.ga.gov/results/public/api/jurisdictions/Georgia
      -> 'elections' list; the 2026-11-03 entry gives publicElectionId
         (currently "11032026GeneralAndSpecialElection").
  https://results.sos.ga.gov/results/public/api/elections/Georgia/<publicElectionId>/data
      -> 'ballotItems': name[en], voteTotal, reportingStatus{reportingUnits,totalUnits} (units = counties),
         summaryResults.ballotOptions[] {name[en] e.g. "Jon Ossoff (I) (Dem)", voteCount, party.abbreviation, isWinner}
Human page: https://results.sos.ga.gov/results/public/Georgia/elections/<publicElectionId>
Notes: GA no longer uses Clarity for statewide results (results.enr.clarityelections.com/GA/ returns 403).
       Party / "(I)" incumbent suffixes are stripped from names. winnerDeclared only from isWinner flag.
"""
import json
import re
import urllib.request

UA = "ballot-night-tracker/1.0 (personal results dashboard)"
BASE = "https://results.sos.ga.gov/results/public"
ELECTION_DATE = "2026-11-03"
RACES = {"sen-ga": "US Senate"}


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def _en(v):
    if isinstance(v, list):
        for x in v:
            if x.get("languageId") == "en":
                return x.get("text")
        return v[0].get("text") if v else None
    return v


def _clean(name):
    return re.sub(r"(\s*\((I|Rep|Dem|Lib|Ind|Grn|NP)\))+\s*$", "", name, flags=re.I).strip()


def fetch():
    j = _get(f"{BASE}/api/jurisdictions/Georgia")
    eid = next(e["publicElectionId"] for e in j["elections"] if e.get("electionDate") == ELECTION_DATE
               and "general" in (_en(e.get("name")) or "").lower())
    data = _get(f"{BASE}/api/elections/Georgia/{eid}/data")
    out = {}
    for rid, cname in RACES.items():
        item = next((b for b in data["ballotItems"] if (_en(b.get("name")) or "").strip() == cname), None)
        if not item:
            continue
        opts = item["summaryResults"]["ballotOptions"]
        total = sum(o.get("voteCount") or 0 for o in opts) or 1
        cands = sorted(({"name": _clean(_en(o["name"])),
                         "party": ((o.get("party") or {}).get("abbreviation") or "").upper() or None,
                         "votes": o.get("voteCount") or 0,
                         "pct": round(100.0 * (o.get("voteCount") or 0) / total, 2)} for o in opts),
                       key=lambda c: -c["votes"])
        winners = [_clean(_en(o["name"])) for o in opts if o.get("isWinner")]
        rs = item.get("reportingStatus") or {}
        out[rid] = {
            "type": "cand",
            "contest": cname,
            "candidates": cands,
            "reporting": f"{rs.get('reportingUnits')} of {rs.get('totalUnits')} counties reporting"
                         + (" (official)" if data["election"].get("isOfficialResults") else " (unofficial)"),
            "source": "GA SOS",
            "sourceUrl": f"{BASE}/Georgia/elections/{eid}",
            "winnerDeclared": winners[0] if winners else None,
        }
    return out


if __name__ == "__main__":
    print(json.dumps(fetch(), indent=1))
