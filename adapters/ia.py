"""Iowa adapter (Iowa Secretary of State, Clarity ENR hosted at results.enr.clarityelections.com/IA).

Feeds:
  https://results.enr.clarityelections.com/IA/elections.json        -> [{EID, ElectionName, Date}] (statewide election id;
                                                                        2026 General = 127077)
  https://results.enr.clarityelections.com/IA/<EID>/current_ver.txt  -> current version number
  https://results.enr.clarityelections.com/IA/<EID>/<ver>/json/en/summary.json
      -> list of contests: C=name, CH=candidates, P=parties, V=votes, PR/TP=units reporting/total (counties), W=winner flags
Human page: https://results.enr.clarityelections.com/IA/<EID>/  (also electionresults.iowa.gov)
Note: sos.iowa.gov itself is behind a Cloudflare challenge; not used.
"""
import json
import urllib.request

UA = "ballot-night-tracker/1.0 (personal results dashboard)"
BASE = "https://results.enr.clarityelections.com/IA"
RACES = {"sen-ia": "United States Senator"}


def _get(url, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        b = r.read().decode("utf-8-sig")
    return b if raw else json.loads(b)


def fetch():
    els = _get(f"{BASE}/elections.json")
    eid = next(e["EID"] for e in els if e.get("Date", "").startswith("11/3/2026"))
    ver = _get(f"{BASE}/{eid}/current_ver.txt", raw=True).strip()
    summary = _get(f"{BASE}/{eid}/{ver}/json/en/summary.json")
    out = {}
    for rid, cname in RACES.items():
        c = next((x for x in summary if x.get("C") == cname), None)
        if not c:
            continue
        total = sum(c["V"]) or 1
        cands = sorted(({"name": n, "party": p or None, "votes": v, "pct": round(100.0 * v / total, 2)}
                        for n, p, v in zip(c["CH"], c["P"], c["V"])), key=lambda x: -x["votes"])
        winners = [n for n, w in zip(c["CH"], c.get("W") or []) if w]
        out[rid] = {
            "type": "cand",
            "contest": cname,
            "candidates": cands,
            "reporting": f"{c['PR']} of {c['TP']} counties reporting",
            "source": "IA SOS (Clarity)",
            "sourceUrl": f"{BASE}/{eid}/",
            "winnerDeclared": winners[0] if winners else None,
        }
    return out


if __name__ == "__main__":
    print(json.dumps(fetch(), indent=1))
