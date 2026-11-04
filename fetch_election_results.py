#!/usr/bin/env python3
"""
fetch_election_results.py - pulls REAL, official, unofficial-count returns.

Local tab  (results.json):
  * Colorado Secretary of State election-night reporting (Clarity ENR)
      https://results.enr.clarityelections.com/CO/127407/
  * Arapahoe County Clerk election-night reporting (Clarity ENR, discovered
    from the state feed's participating-county list)
National tab (national_results.json):
  * Colorado contests from the same CO SOS feed
  * Every other state from its own official election-office feed, via the
    per-state modules in ./adapters/ (each documents its URLs)

Nothing here is simulated. If a feed is unreachable the previous value for
those contests is kept and marked stale. Files are only rewritten when the
underlying numbers change, so "as of" reflects the last real update.

Usage:  python3 fetch_election_results.py            # run once
        python3 fetch_election_results.py --loop 300 # poll every 5 min
"""

import argparse
import gzip
import io
import importlib
import json
import os
import sys
import time
import urllib.request
import urllib.response
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL_PATH = os.path.join(HERE, "results.json")
NAT_PATH = os.path.join(HERE, "national_results.json")
UA = "ballot-night-tracker/1.0 (personal results dashboard)"
CLARITY = "https://results.enr.clarityelections.com"
CO_ELECTION_ID = "127407"          # CO 2026 General (linked from sos.state.co.us results page)
CO_COUNTY = "Arapahoe"
CO_SOURCE_URL = f"{CLARITY}/CO/{CO_ELECTION_ID}/"
# States whose official feeds are reachable by an automated client. TX, AZ, NV, KS, MO,
# MI, OH, PA, NY and ME official sites sit behind bot challenges (or publish no live feed),
# so those races link out to the official page instead.
NATIONAL_STATES = ["ca", "nc", "ga", "ia", "ak", "wa"]
ADAPTER_TIMEOUT = 75  # seconds per state

PARTY_LETTER = {"DEM": "D", "REP": "R", "LBR": "L", "LIB": "L", "GRN": "G",
                "UAF": "U", "UNA": "U", "IND": "I", "NPA": "I", "NP": "NP"}


# --------------------------------------------------------------------------
# HTTP / Clarity helpers
# --------------------------------------------------------------------------
class _GunzipProcessor(urllib.request.BaseHandler):
    """Clarity's CDN sometimes returns gzip bodies even when none was requested.
    Installed globally so the per-state adapters get the same treatment."""
    handler_order = 1000

    def http_response(self, req, resp):
        body = resp.read()
        if body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
        new = urllib.response.addinfourl(io.BytesIO(body), resp.headers, resp.url, resp.code)
        new.msg = resp.msg
        return new

    https_response = http_response


urllib.request.install_opener(urllib.request.build_opener(_GunzipProcessor()))


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_json(url):
    raw = http_get(url)
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except ValueError:
        raise RuntimeError(f"non-JSON response from {url}: {raw[:200]!r}")


def clarity_summary(path):
    """path like 'CO/127407' or 'CO/Arapahoe/127409' -> (contests_by_name, settings)."""
    ver = http_get(f"{CLARITY}/{path}/current_ver.txt").decode().strip()
    if not ver.isdigit():
        raise RuntimeError(f"unexpected Clarity version response for {path}: {ver[:200]!r}")
    summary = get_json(f"{CLARITY}/{path}/{ver}/json/en/summary.json")
    settings = get_json(f"{CLARITY}/{path}/{ver}/json/en/electionsettings.json")["settings"]
    return {c["C"].strip(): c for c in summary}, settings, ver


def parse_clarity_time(s):
    # e.g. "11/3/2026 11:29:33 PM MST"
    parts = s.rsplit(" ", 1)
    tz = timezone(timedelta(hours=-6)) if parts[-1] == "MDT" else timezone(timedelta(hours=-7))
    return datetime.strptime(parts[0], "%m/%d/%Y %I:%M:%S %p").replace(tzinfo=tz)


def candidates_of(c):
    out = []
    for i, name in enumerate(c["CH"]):
        out.append({"name": name.strip(), "party": (c["P"][i] if c.get("P") else "") or "",
                    "votes": c["V"][i], "pct": round(c["PCT"][i], 2)})
    out.sort(key=lambda x: -x["votes"])
    return out


def with_party(name, party):
    letter = PARTY_LETTER.get((party or "").upper(), (party or "")[:3])
    return f"{name} ({letter})" if letter else name


def reporting_text(c, unit):
    total = c["T"][0] if c.get("T") else sum(c["V"])
    return f"{c['PR']} of {c['TP']} {unit} fully reported · {total:,} votes"


# --------------------------------------------------------------------------
# LOCAL TAB: Ben's ballot -> official contest names
#   cand:    (feed, contest, pick-substring)
#   yes/no:  (feed, contest, threshold %)
# feed "state" = CO SOS statewide feed, "county" = Arapahoe County feed
# --------------------------------------------------------------------------
LOCAL_CAND = {
    "senate":   ("state", "United States Senator", "Hickenlooper"),
    "cd6":      ("state", "Representative to the 120th United States Congress - District 6", "Crow"),
    "gov":      ("state", "Governor / Lieutenant Governor", "Weiser"),
    "sos":      ("state", "Secretary of State", "Gonzalez"),
    "treas":    ("state", "State Treasurer", "Bridges"),
    "ag":       ("state", "Attorney General", "Griswold"),
    "regent":   ("state", "Regent of the University of Colorado - Congressional District 6", "Spiegel"),
    "hd38":     ("state", "State Representative - District 38", "Rydin"),
    "clerk":    ("county", "Arapahoe County Clerk and Recorder", "Lopez"),
    "ctreas":   ("county", "Arapahoe County Treasurer", "Westerberg"),
    "assessor": ("county", "Arapahoe County Assessor", "Kaiser"),
    "sheriff":  ("county", "Arapahoe County Sheriff", "Brown"),
    "coroner":  ("county", "Arapahoe County Coroner", "Bitting"),
}
_J = "Judicial Retention"
LOCAL_YESNO = {
    "j-hood":      ("state", "Colorado Supreme Court Justice - Hood", 50),
    "j-freyre":    ("state", "Colorado Court of Appeals Judge - Freyre", 50),
    "j-harris":    ("state", "Colorado Court of Appeals Judge - Harris", 50),
    "j-lum":       ("state", "Colorado Court of Appeals Judge - Lum", 50),
    "j-moultrie":  ("state", "Colorado Court of Appeals Judge - Moultrie", 50),
    "j-schock":    ("state", "Colorado Court of Appeals Judge - Schock", 50),
    "j-sullivan":  ("state", "Colorado Court of Appeals Judge - Sullivan", 50),
    "j-amico":     ("state", "District Court Judge - 18th Judicial District - Amico", 50),
    "j-baker":     ("state", "District Court Judge - 18th Judicial District - Baker-McKay", 50),
    "j-edson":     ("state", "District Court Judge - 18th Judicial District - Edson", 50),
    "j-henderson": ("state", "District Court Judge - 18th Judicial District - Henderson", 50),
    "j-jones":     ("state", "District Court Judge - 18th Judicial District - Jones", 50),
    "j-karpel":    ("state", "District Court Judge - 18th Judicial District - Karpel", 50),
    "j-stricklin": ("state", "District Court Judge - 18th Judicial District - Stricklin", 50),
    "j-vahle":     ("state", "District Court Judge - 18th Judicial District - Vahle", 50),
    "j-washburn":  ("state", "District Court Judge - 18th Judicial District - Washburn", 50),
    "j-apostoli":  ("state", "County Court Judge - Arapahoe - Apostoli", 50),
    "j-clark":     ("state", "County Court Judge - Arapahoe - Clark", 50),
    "j-rowles":    ("state", "County Court Judge - Arapahoe - Rowles-Stokes", 50),
    # Constitutional amendments need 55% (Colo. Const. art. V, sec. 1(4)(b))
    "a81":  ("state", "Amendment 81 (CONSTITUTIONAL)", 55),
    "a82":  ("state", "Amendment 82 (CONSTITUTIONAL)", 55),
    "a83":  ("state", "Amendment 83 (CONSTITUTIONAL)", 55),
    "a84":  ("state", "Amendment 84 (CONSTITUTIONAL)", 55),
    "a85":  ("state", "Amendment 85 (CONSTITUTIONAL)", 55),
    "a86":  ("state", "Amendment 86 (CONSTITUTIONAL)", 55),
    "a87":  ("state", "Amendment 87 (CONSTITUTIONAL)", 55),
    "pnn":  ("state", "Proposition NN (STATUTORY)", 50),
    "p132": ("state", "Proposition 132 (STATUTORY)", 50),
    "p133": ("state", "Proposition 133 (STATUTORY)", 50),
    "p134": ("state", "Proposition 134 (STATUTORY)", 50),
    "p135": ("state", "Proposition 135 (STATUTORY)", 50),
    "p136": ("state", "Proposition 136 (STATUTORY)", 50),
    "p137": ("state", "Proposition 137 (STATUTORY)", 50),
    "i4a":  ("county", "Arapahoe County School District #6 Littleton Public Schools Ballot Issue 4A", 50),
    "i7a":  ("state", "Front Range Passenger Rail District Ballot Issue 7A", 50),
}

# Colorado items on the National tab come from the same CO SOS feed
NAT_CO_CAND = {
    "hse-co08": "Representative to the 120th United States Congress - District 8",
}
NAT_CO_MEAS = {
    "meas-co87": ("Amendment 87 (CONSTITUTIONAL)", 55),
    "meas-co136": ("Proposition 136 (STATUTORY)", 50),
    "meas-co134": ("Proposition 134 (STATUTORY)", 50),
    "meas-co135": ("Proposition 135 (STATUTORY)", 50),
    "meas-co84": ("Amendment 84 (CONSTITUTIONAL)", 55),
    "meas-co86": ("Amendment 86 (CONSTITUTIONAL)", 55),
}


def yes_no(c):
    yes = no = None
    for i, n in enumerate(c["CH"]):
        if n.lower().startswith("yes"):
            yes = (c["PCT"][i], c["V"][i])
        elif n.lower().startswith("no"):
            no = (c["PCT"][i], c["V"][i])
    return yes, no


def build_local(state, county, state_url, county_url):
    feeds = {"state": (state, "counties", "CO SOS", state_url),
             "county": (county, "precincts", "Arapahoe Votes", county_url)}
    items, missing = {}, []
    for rid, (feed, name, pick) in LOCAL_CAND.items():
        contests, unit, src, url = feeds[feed]
        c = contests.get(name)
        if not c:
            missing.append(rid)
            continue
        cands = candidates_of(c)
        mine = next((x for x in cands if pick.lower() in x["name"].lower()), None)
        top = cands[0]
        unopposed = len(cands) == 1
        winner_flag = any(c.get("W") or [])
        items[rid] = {
            "outcome": "yes" if mine and mine is top and top["votes"] > 0 else "no",
            "final": bool(unopposed or winner_flag),
            "pct": mine["pct"] if mine else 0.0,
            "leader": with_party(top["name"], top["party"]),
            "leaderPct": top["pct"],
            "reporting": "Unopposed" if unopposed else reporting_text(c, unit),
            "source": src, "sourceUrl": url,
            "candidates": cands[:4],
        }
    for rid, (feed, name, threshold) in LOCAL_YESNO.items():
        contests, unit, src, url = feeds[feed]
        c = contests.get(name)
        if not c:
            missing.append(rid)
            continue
        yes, no = yes_no(c)
        if yes is None:
            missing.append(rid)
            continue
        rep = reporting_text(c, unit)
        if threshold != 50:
            rep += f" · needs {threshold}% Yes"
        items[rid] = {
            "outcome": "yes" if yes[0] >= threshold and yes[1] > 0 else "no",
            "final": False,
            "pct": round(yes[0], 2),
            "reporting": rep,
            "source": src, "sourceUrl": url,
            "yesVotes": yes[1], "noVotes": no[1] if no else None,
        }
    return items, missing


def nat_from_adapter(rid, r):
    """Convert an adapter result to the page's national item schema."""
    out = {"source": r.get("source"), "sourceUrl": r.get("sourceUrl"),
           "reporting": r.get("reporting"), "contest": r.get("contest")}
    if r.get("type") == "measure":
        thr = r.get("threshold") or 50
        yes = r.get("yesPct")
        out.update({"outcome": "yes" if yes is not None and yes >= thr else "no",
                    "pct": yes, "threshold": thr, "final": False})
        if thr != 50 and out["reporting"]:
            out["reporting"] += f" · needs {thr}% Yes"
    else:
        cands = r.get("candidates") or []
        if cands:
            top = cands[0]
            out.update({"leader": with_party(top["name"], top.get("party")),
                        "leaderPct": top.get("pct")})
        out["candidates"] = cands[:4]
        out["final"] = bool(r.get("winnerDeclared"))
    return out


def run_adapter(st):
    mod = importlib.import_module(f"adapters.{st}")
    return mod.fetch()


def build_national(state, state_url, previous):
    items, errors = {}, {}
    for rid, name in NAT_CO_CAND.items():
        c = state.get(name)
        if c:
            cands = candidates_of(c)
            items[rid] = nat_from_adapter(rid, {"type": "cand", "contest": name, "candidates": cands,
                                                "reporting": reporting_text(c, "counties"),
                                                "source": "CO SOS", "sourceUrl": state_url})
    for rid, (name, thr) in NAT_CO_MEAS.items():
        c = state.get(name)
        if c:
            yes, no = yes_no(c)
            items[rid] = nat_from_adapter(rid, {"type": "measure", "contest": name, "yesPct": round(yes[0], 2),
                                                "threshold": thr, "reporting": reporting_text(c, "counties"),
                                                "source": "CO SOS", "sourceUrl": state_url})

    sys.path.insert(0, HERE)
    pool = ThreadPoolExecutor(max_workers=8)
    futs = {pool.submit(run_adapter, st): st for st in NATIONAL_STATES
            if os.path.exists(os.path.join(HERE, "adapters", f"{st}.py"))}
    done, not_done = wait(futs, timeout=ADAPTER_TIMEOUT)
    for f in done:
        st = futs[f]
        try:
            for rid, r in (f.result() or {}).items():
                items[rid] = nat_from_adapter(rid, r)
        except Exception as e:  # keep going; old values are reused below
            errors[st] = f"{type(e).__name__}: {e}"[:200]
    for f in not_done:
        errors[futs[f]] = "timed out"
    pool.shutdown(wait=False, cancel_futures=True)

    # keep last-known values for anything we failed to fetch this round
    # (only values that came from a real feed — they carry "contest")
    for rid, old in (previous.get("items") or {}).items():
        if rid not in items and old.get("contest"):
            items[rid] = {**old, "stale": True}
    return items, errors


# --------------------------------------------------------------------------
def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def write_if_changed(path, data, volatile=("asOf", "checkedAt")):
    old = load_json(path)
    strip = lambda d: {k: v for k, v in d.items() if k not in volatile}
    if strip(old) == strip(data):
        print(f"  no change: {os.path.basename(path)}")
        return False
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"  wrote {os.path.basename(path)} ({len(data.get('items', {}))} items)")
    return True


def run_once():
    now = datetime.now(timezone.utc)
    prev_local, prev_nat = load_json(LOCAL_PATH), load_json(NAT_PATH)

    state, settings, _ = clarity_summary(f"CO/{CO_ELECTION_ID}")
    counties = settings["electiondetails"].get("participatingcounties") or []
    updates = [parse_clarity_time(x.split("|")[3]) for x in counties if x.count("|") >= 3]
    co_asof = max(updates).isoformat() if updates else now.isoformat()

    arap = next((x.split("|") for x in counties if x.startswith(CO_COUNTY + "|")), None)
    county, county_url, county_err = {}, CO_SOURCE_URL, None
    if arap:
        county_url = f"{CLARITY}/CO/{CO_COUNTY}/{arap[1]}/"
        try:
            county, _, _ = clarity_summary(f"CO/{CO_COUNTY}/{arap[1]}")
        except Exception as e:
            county_err = str(e)

    local_items, missing = build_local(state, county, CO_SOURCE_URL, county_url)
    for rid in missing:  # reuse last-known value if a contest temporarily vanished
        if (prev_local.get("items") or {}).get(rid, {}).get("sourceUrl"):
            local_items[rid] = {**prev_local["items"][rid], "stale": True}

    local = {
        "asOf": co_asof,
        "status": "Unofficial results from official election offices (not yet certified)",
        "source": "CO Secretary of State & Arapahoe County Clarity ENR",
        "sourceUrl": CO_SOURCE_URL,
        "items": dict(sorted(local_items.items())),
    }
    if missing:
        local["missing"] = sorted(missing)
    if county_err:
        local["errors"] = {"Arapahoe": county_err[:200]}

    nat_items, nat_errors = build_national(state, CO_SOURCE_URL, prev_nat)
    nat = {
        "asOf": now.isoformat(),
        "status": "Unofficial results from each state's official election office",
        "source": "State election offices (see each race)",
        "items": dict(sorted(nat_items.items())),
    }
    if nat_errors:
        nat["errors"] = dict(sorted(nat_errors.items()))

    changed = write_if_changed(LOCAL_PATH, local)
    changed |= write_if_changed(NAT_PATH, nat)
    if missing:
        print("  WARNING missing local contests:", ", ".join(missing))
    for st, err in nat_errors.items():
        print(f"  WARNING {st.upper()}: {err}")
    return changed


def main():
    ap = argparse.ArgumentParser(description="Fetch official election results")
    ap.add_argument("--loop", type=int, default=0, help="poll every N seconds (0 = once)")
    args = ap.parse_args()
    while True:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] fetching official results…")
        try:
            run_once()
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            if not args.loop:
                sys.exit(1)
        if not args.loop:
            break
        time.sleep(args.loop)


if __name__ == "__main__":
    main()
