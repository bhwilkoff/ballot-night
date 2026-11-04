"""Alaska (AK) adapter - 2026-11-03 general election.

Official source: Alaska Division of Elections election-night results (ENR) map.
  Human page:  https://www.elections.alaska.gov/enr/26GENR/
  Data feed:   https://www.elections.alaska.gov/enr/26GENR/results/statewide.js
               (served as application/javascript but the body is plain JSON; it is what
               the page's includes/map.js loads)
    - contestNames[i] / candidateNames[j]: lookup tables
    - totals[]: {n: contest idx, b: ballots cast, t: contest total votes, v: registered,
                 p: precincts, r: precincts reporting, c: [{n: candidate idx, t: votes}]}
    - certified: bool, updated: "MM/DD/YYYY h:mm AM" (Alaska time)
  Also published (not used): results/ElectionSummaryReportRPT.pdf,
  results/GA_ENR_Precinct_State_of_Alaska.csv
The election code ("26GENR") is fixed for this election.

Race ids:
  sen-ak    contest "U.S. Senator". Alaska uses ranked-choice general elections; the ENR feed
            contains first-choice (round 1) totals only. RCV tabulation is published separately
            after all ballots are in.
  meas-ak2  contest "BM#2 24ESEG" = Ballot Measure No. 2, petition 24ESEG,
            "Repeal the open primary and ranked choice general elections" (app label is right).
            (Also on the ballot, not tracked: "BM#3 25USCV", initiative to require that only
            U.S. citizens may be qualified voters in Alaska elections.)

TLS note: www.elections.alaska.gov does not send its intermediate certificate
(GlobalSign GCC R46 OV TLS CA 2025), so default verification fails with
"unable to get local issuer certificate". We do NOT disable verification: the module
completes the chain by downloading that intermediate from the issuer URL named in the
leaf certificate's AIA extension (http://secure.globalsign.com/cacert/gsgccr46ovtlsca2025.crt)
and adding it to the default trust context; the full chain is still verified against
the system root store (GlobalSign Root R46).
"""
import json
import re
import ssl
import urllib.request

UA = "ballot-night-tracker/1.0 (personal results dashboard)"
BASE = "https://www.elections.alaska.gov/enr/26GENR/"
FEED = BASE + "results/statewide.js"
INTERMEDIATE_URL = "https://secure.globalsign.com/cacert/gsgccr46ovtlsca2025.crt"


def _open(url, ctx=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=40, context=ctx)


def _ctx_with_intermediate():
    ctx = ssl.create_default_context()
    with _open(INTERMEDIATE_URL) as r:
        der = r.read()
    ctx.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(der))
    return ctx


def _load():
    try:
        with _open(FEED) as r:
            return json.loads(r.read().decode("utf-8-sig"))
    except urllib.error.URLError as e:
        if not isinstance(getattr(e, "reason", None), ssl.SSLCertVerificationError):
            raise
    with _open(FEED, _ctx_with_intermediate()) as r:
        return json.loads(r.read().decode("utf-8-sig"))


def _split(name):
    m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", name)
    if m:
        return m.group(1), m.group(2)
    return name, ""


def _pretty(name):
    # "Sullivan, Dan S." -> "Dan S. Sullivan"; leave "A/B" tickets alone
    if "," in name and "/" not in name:
        last, first = name.split(",", 1)
        first = first.strip()
        sfx = ""
        m = re.match(r"^(.*?)\s+(Jr\.?|Sr\.?|II|III|IV)$", first)
        if m:
            first, sfx = m.group(1), " " + m.group(2)
        return f"{first} {last.strip()}{sfx}".strip()
    return name


def _contest(d, name_re):
    names = d["contestNames"]
    for t in d["totals"]:
        if re.search(name_re, names[t["n"]]):
            return t
    return None


def _reporting(t, d):
    s = f"{t['r']} of {t['p']} precincts reporting"
    s += " (certified)" if d.get("certified") else f" (unofficial, updated {d.get('updated')} AKT)"
    return s


def fetch():
    d = _load()
    cn = d["candidateNames"]
    out = {}

    t = _contest(d, r"^U\.S\. Senator$")
    if t:
        tot = sum(c["t"] for c in t["c"]) or 1
        cands = []
        for c in t["c"]:
            nm, party = _split(cn[c["n"]])
            cands.append({"name": _pretty(nm), "party": party, "votes": c["t"],
                          "pct": round(100.0 * c["t"] / tot, 1)})
        cands.sort(key=lambda x: -x["votes"])
        out["sen-ak"] = {
            "type": "cand",
            "contest": "U.S. Senator (first-choice votes, ranked-choice round 1)",
            "candidates": cands,
            "reporting": _reporting(t, d),
            "source": "AK Division of Elections",
            "sourceUrl": BASE,
            "winnerDeclared": None,  # feed carries no winner flag
        }

    t = _contest(d, r"^BM#2\b") or _contest(d, r"24ESEG")
    if t:
        yes = sum(c["t"] for c in t["c"] if cn[c["n"]].strip().upper() == "YES")
        no = sum(c["t"] for c in t["c"] if cn[c["n"]].strip().upper() == "NO")
        tot = (yes + no) or 1
        out["meas-ak2"] = {
            "type": "measure",
            "contest": "Ballot Measure No. 2 (24ESEG): Repeal the open primary and ranked choice general elections",
            "yesPct": round(100.0 * yes / tot, 1),
            "noPct": round(100.0 * no / tot, 1),
            "yesVotes": yes,
            "noVotes": no,
            "threshold": 50,
            "reporting": _reporting(t, d),
            "source": "AK Division of Elections",
            "sourceUrl": BASE,
        }
    return out


if __name__ == "__main__":
    print(json.dumps(fetch(), indent=1, ensure_ascii=False))
