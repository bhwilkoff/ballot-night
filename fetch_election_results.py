#!/usr/bin/env python3
"""
fetch_election_results.py - Election Night Live Scraper & Updater
Pulls returns for Arapahoe County & National 2026 battlegrounds.
Writes to both results.json and national_results.json.
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone, timedelta

DEFAULT_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")
DEFAULT_NAT_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "national_results.json")
MT_TZ = timezone(timedelta(hours=-7))

SIMULATED_LOCAL = {
    "pre": {
        "asOf": "2026-11-03T15:00:00-07:00",
        "status": "Polls open until 7:00 PM MT. No official returns released yet.",
        "source": "Official Feeds: CO Secretary of State & Arapahoe County Elections",
        "totalBallotsCast": 0,
        "items": {}
    },
    "early": {
        "asOf": "2026-11-03T19:22:00-07:00",
        "status": "7:15 PM Initial Mail-In Ballot Drop (~54% estimated vote counted)",
        "source": "CO SOS Clarity Feed / Arapahoe Clerk Batch 1",
        "items": {
            "senate": { "outcome": "yes", "final": False, "pct": 57.4, "leader": "John Hickenlooper (D)", "leaderPct": 57.4, "reporting": "54% counted", "source": "CO SOS" },
            "cd6": { "outcome": "yes", "final": False, "pct": 63.8, "leader": "Jason Crow (D)", "leaderPct": 63.8, "reporting": "52% counted", "source": "CO SOS" },
            "gov": { "outcome": "yes", "final": False, "pct": 55.2, "leader": "Phil Weiser (D)", "leaderPct": 55.2, "reporting": "54% counted", "source": "CO SOS" },
            "sos": { "outcome": "yes", "final": False, "pct": 53.9, "leader": "Amanda Gonzalez (D)", "leaderPct": 53.9, "reporting": "53% counted", "source": "CO SOS" },
            "treas": { "outcome": "yes", "final": False, "pct": 54.1, "leader": "Jeff Bridges (D)", "leaderPct": 54.1, "reporting": "53% counted", "source": "CO SOS" },
            "ag": { "outcome": "yes", "final": False, "pct": 52.8, "leader": "Jena Griswold (D)", "leaderPct": 52.8, "reporting": "54% counted", "source": "CO SOS" },
            "regent": { "outcome": "yes", "final": False, "pct": 56.4, "leader": "Ilana Spiegel (D)", "leaderPct": 56.4, "reporting": "51% counted", "source": "CO SOS" },
            "hd38": { "outcome": "yes", "final": False, "pct": 54.3, "leader": "Gretchen Rydin (D)", "leaderPct": 54.3, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "clerk": { "outcome": "yes", "final": False, "pct": 56.1, "leader": "Joan Lopez (D)", "leaderPct": 56.1, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "ctreas": { "outcome": "yes", "final": False, "pct": 61.2, "leader": "Michael Westerberg (D)", "leaderPct": 61.2, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "assessor": { "outcome": "yes", "final": False, "pct": 55.7, "leader": "PK Kaiser (D)", "leaderPct": 55.7, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "sheriff": { "outcome": "yes", "final": False, "pct": 53.4, "leader": "Tyler Scott Brown (D)", "leaderPct": 53.4, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "coroner": { "outcome": "yes", "final": True, "pct": 100.0, "leader": "Casey Bitting (D)", "leaderPct": 100.0, "reporting": "Called (Unopposed)", "source": "Arapahoe Votes" },
            "j-hood": { "outcome": "yes", "final": False, "pct": 74.2, "reporting": "52% counted", "source": "CO Judicial" },
            "j-freyre": { "outcome": "yes", "final": False, "pct": 71.5, "reporting": "52% counted", "source": "CO Judicial" },
            "j-harris": { "outcome": "yes", "final": False, "pct": 68.1, "reporting": "52% counted", "source": "CO Judicial" },
            "j-lum": { "outcome": "yes", "final": False, "pct": 72.8, "reporting": "52% counted", "source": "CO Judicial" },
            "j-moultrie": { "outcome": "yes", "final": False, "pct": 73.1, "reporting": "52% counted", "source": "CO Judicial" },
            "j-schock": { "outcome": "yes", "final": False, "pct": 70.4, "reporting": "52% counted", "source": "CO Judicial" },
            "j-sullivan": { "outcome": "yes", "final": False, "pct": 71.9, "reporting": "52% counted", "source": "CO Judicial" },
            "j-amico": { "outcome": "yes", "final": False, "pct": 69.8, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "j-baker": { "outcome": "yes", "final": False, "pct": 68.5, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "j-edson": { "outcome": "yes", "final": False, "pct": 70.1, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "j-henderson": { "outcome": "yes", "final": False, "pct": 69.0, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "j-jones": { "outcome": "yes", "final": False, "pct": 72.3, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "j-karpel": { "outcome": "yes", "final": False, "pct": 67.9, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "j-stricklin": { "outcome": "yes", "final": False, "pct": 70.8, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "j-vahle": { "outcome": "yes", "final": False, "pct": 64.2, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "j-washburn": { "outcome": "yes", "final": False, "pct": 71.4, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "j-apostoli": { "outcome": "yes", "final": False, "pct": 71.8, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "j-clark": { "outcome": "yes", "final": False, "pct": 65.5, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "j-rowles": { "outcome": "yes", "final": False, "pct": 73.0, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "a81": { "outcome": "no", "final": False, "pct": 46.2, "reporting": "53% counted (needs 55%)", "source": "CO SOS" },
            "a82": { "outcome": "no", "final": False, "pct": 44.8, "reporting": "53% counted (needs 55%)", "source": "CO SOS" },
            "a83": { "outcome": "no", "final": False, "pct": 48.1, "reporting": "53% counted (needs 55%)", "source": "CO SOS" },
            "a84": { "outcome": "no", "final": False, "pct": 41.5, "reporting": "53% counted (needs 55%)", "source": "CO SOS" },
            "a85": { "outcome": "no", "final": False, "pct": 52.3, "reporting": "53% counted (under 55% threshold)", "source": "CO SOS" },
            "a86": { "outcome": "no", "final": False, "pct": 43.7, "reporting": "53% counted (needs 55%)", "source": "CO SOS" },
            "a87": { "outcome": "yes", "final": False, "pct": 56.4, "reporting": "53% counted (above 55% threshold)", "source": "CO SOS" },
            "pnn": { "outcome": "yes", "final": False, "pct": 54.6, "reporting": "53% counted", "source": "CO SOS" },
            "p132": { "outcome": "no", "final": False, "pct": 48.9, "reporting": "53% counted", "source": "CO SOS" },
            "p133": { "outcome": "no", "final": False, "pct": 47.3, "reporting": "53% counted", "source": "CO SOS" },
            "p134": { "outcome": "no", "final": False, "pct": 42.1, "reporting": "53% counted", "source": "CO SOS" },
            "p135": { "outcome": "no", "final": False, "pct": 40.8, "reporting": "53% counted", "source": "CO SOS" },
            "p136": { "outcome": "no", "final": False, "pct": 46.5, "reporting": "53% counted", "source": "CO SOS" },
            "p137": { "outcome": "no", "final": False, "pct": 45.2, "reporting": "53% counted", "source": "CO SOS" },
            "i4a": { "outcome": "yes", "final": False, "pct": 58.7, "reporting": "58% counted", "source": "Arapahoe Votes" },
            "i7a": { "outcome": "yes", "final": False, "pct": 57.3, "reporting": "51% counted (Districtwide)", "source": "Front Range Rail Dist." }
        }
    },
    "mid": {
        "asOf": "2026-11-03T21:45:00-07:00",
        "status": "Late Evening Batch (~82% counted - AP & Decision Desks calling major races)",
        "source": "CO SOS / Arapahoe Elections / AP Decision Desk",
        "items": {
            "senate": { "outcome": "yes", "final": True, "pct": 58.1, "leader": "John Hickenlooper (D)", "leaderPct": 58.1, "reporting": "AP Called (84% counted)", "source": "AP / CO SOS" },
            "cd6": { "outcome": "yes", "final": True, "pct": 64.5, "leader": "Jason Crow (D)", "leaderPct": 64.5, "reporting": "AP Called (81% counted)", "source": "AP / CO SOS" },
            "gov": { "outcome": "yes", "final": True, "pct": 56.0, "leader": "Phil Weiser (D)", "leaderPct": 56.0, "reporting": "AP Called (83% counted)", "source": "AP / CO SOS" },
            "sos": { "outcome": "yes", "final": False, "pct": 54.4, "leader": "Amanda Gonzalez (D)", "leaderPct": 54.4, "reporting": "82% counted", "source": "CO SOS" },
            "treas": { "outcome": "yes", "final": True, "pct": 54.9, "leader": "Jeff Bridges (D)", "leaderPct": 54.9, "reporting": "AP Called (82% counted)", "source": "AP / CO SOS" },
            "ag": { "outcome": "yes", "final": False, "pct": 53.2, "leader": "Jena Griswold (D)", "leaderPct": 53.2, "reporting": "82% counted", "source": "CO SOS" },
            "regent": { "outcome": "yes", "final": True, "pct": 57.1, "leader": "Ilana Spiegel (D)", "leaderPct": 57.1, "reporting": "Called (80% counted)", "source": "CO SOS" },
            "hd38": { "outcome": "yes", "final": False, "pct": 55.0, "leader": "Gretchen Rydin (D)", "leaderPct": 55.0, "reporting": "84% counted", "source": "Arapahoe Votes" },
            "clerk": { "outcome": "yes", "final": True, "pct": 56.8, "leader": "Joan Lopez (D)", "leaderPct": 56.8, "reporting": "Called (84% counted)", "source": "Arapahoe Votes" },
            "ctreas": { "outcome": "yes", "final": True, "pct": 62.0, "leader": "Michael Westerberg (D)", "leaderPct": 62.0, "reporting": "Called (84% counted)", "source": "Arapahoe Votes" },
            "assessor": { "outcome": "yes", "final": False, "pct": 56.2, "leader": "PK Kaiser (D)", "leaderPct": 56.2, "reporting": "84% counted", "source": "Arapahoe Votes" },
            "sheriff": { "outcome": "yes", "final": False, "pct": 53.9, "leader": "Tyler Scott Brown (D)", "leaderPct": 53.9, "reporting": "84% counted", "source": "Arapahoe Votes" },
            "coroner": { "outcome": "yes", "final": True, "pct": 100.0, "leader": "Casey Bitting (D)", "leaderPct": 100.0, "reporting": "Called", "source": "Arapahoe Votes" },
            "j-hood": { "outcome": "yes", "final": True, "pct": 74.8, "reporting": "Called (82% counted)", "source": "CO Judicial" },
            "j-freyre": { "outcome": "yes", "final": True, "pct": 72.1, "reporting": "Called (82% counted)", "source": "CO Judicial" },
            "j-harris": { "outcome": "yes", "final": False, "pct": 68.7, "reporting": "82% counted", "source": "CO Judicial" },
            "j-lum": { "outcome": "yes", "final": True, "pct": 73.4, "reporting": "Called (82% counted)", "source": "CO Judicial" },
            "j-moultrie": { "outcome": "yes", "final": True, "pct": 73.8, "reporting": "Called (82% counted)", "source": "CO Judicial" },
            "j-schock": { "outcome": "yes", "final": True, "pct": 71.0, "reporting": "Called (82% counted)", "source": "CO Judicial" },
            "j-sullivan": { "outcome": "yes", "final": True, "pct": 72.5, "reporting": "Called (82% counted)", "source": "CO Judicial" },
            "j-amico": { "outcome": "yes", "final": True, "pct": 70.4, "reporting": "Called (84% counted)", "source": "Arapahoe Votes" },
            "j-baker": { "outcome": "yes", "final": True, "pct": 69.1, "reporting": "Called (84% counted)", "source": "Arapahoe Votes" },
            "j-edson": { "outcome": "yes", "final": True, "pct": 70.8, "reporting": "Called (84% counted)", "source": "Arapahoe Votes" },
            "j-henderson": { "outcome": "yes", "final": True, "pct": 69.6, "reporting": "Called (84% counted)", "source": "Arapahoe Votes" },
            "j-jones": { "outcome": "yes", "final": True, "pct": 72.9, "reporting": "Called (84% counted)", "source": "Arapahoe Votes" },
            "j-karpel": { "outcome": "yes", "final": True, "pct": 68.4, "reporting": "Called (84% counted)", "source": "Arapahoe Votes" },
            "j-stricklin": { "outcome": "yes", "final": True, "pct": 71.3, "reporting": "Called (84% counted)", "source": "Arapahoe Votes" },
            "j-vahle": { "outcome": "yes", "final": False, "pct": 63.8, "reporting": "84% counted", "source": "Arapahoe Votes" },
            "j-washburn": { "outcome": "yes", "final": True, "pct": 72.0, "reporting": "Called (84% counted)", "source": "Arapahoe Votes" },
            "j-apostoli": { "outcome": "yes", "final": True, "pct": 72.4, "reporting": "Called (84% counted)", "source": "Arapahoe Votes" },
            "j-clark": { "outcome": "yes", "final": False, "pct": 65.1, "reporting": "84% counted", "source": "Arapahoe Votes" },
            "j-rowles": { "outcome": "yes", "final": True, "pct": 73.6, "reporting": "Called (84% counted)", "source": "Arapahoe Votes" },
            "a81": { "outcome": "no", "final": True, "pct": 44.5, "reporting": "Projected Failed (under 55%)", "source": "CO SOS" },
            "a82": { "outcome": "no", "final": True, "pct": 43.9, "reporting": "Projected Failed (under 55%)", "source": "CO SOS" },
            "a83": { "outcome": "no", "final": False, "pct": 49.0, "reporting": "82% counted (needs 55%)", "source": "CO SOS" },
            "a84": { "outcome": "no", "final": True, "pct": 39.8, "reporting": "Projected Failed", "source": "CO SOS" },
            "a85": { "outcome": "no", "final": True, "pct": 51.4, "reporting": "Projected Failed (fails 55% rule)", "source": "CO SOS" },
            "a86": { "outcome": "no", "final": True, "pct": 42.1, "reporting": "Projected Failed", "source": "CO SOS" },
            "a87": { "outcome": "yes", "final": False, "pct": 56.8, "reporting": "82% counted (leading >55%)", "source": "CO SOS" },
            "pnn": { "outcome": "yes", "final": True, "pct": 55.4, "reporting": "Projected Passed", "source": "CO SOS" },
            "p132": { "outcome": "no", "final": False, "pct": 48.1, "reporting": "82% counted", "source": "CO SOS" },
            "p133": { "outcome": "no", "final": False, "pct": 46.8, "reporting": "82% counted", "source": "CO SOS" },
            "p134": { "outcome": "no", "final": True, "pct": 41.3, "reporting": "Projected Failed", "source": "CO SOS" },
            "p135": { "outcome": "no", "final": True, "pct": 39.9, "reporting": "Projected Failed", "source": "CO SOS" },
            "p136": { "outcome": "no", "final": True, "pct": 45.8, "reporting": "Projected Failed", "source": "CO SOS" },
            "p137": { "outcome": "no", "final": True, "pct": 44.2, "reporting": "Projected Failed", "source": "CO SOS" },
            "i4a": { "outcome": "yes", "final": True, "pct": 59.8, "reporting": "Called Passed (84% counted)", "source": "Arapahoe Votes" },
            "i7a": { "outcome": "yes", "final": False, "pct": 58.1, "reporting": "80% counted (Districtwide)", "source": "Front Range Rail Dist." }
        }
    }
}

SIMULATED_NAT = {
    "pre": {
        "asOf": "2026-11-03T15:00:00-07:00",
        "status": "Polls open nationwide. Pre-election state.",
        "source": "AP / Decision Desk HQ / State SOS Feeds",
        "senateBalance": { "dem": 47, "gop": 53, "calledDem": 0, "calledGop": 0, "needed": 51 },
        "houseBalance": { "dem": 213, "gop": 220, "calledDem": 0, "calledGop": 0, "needed": 218 },
        "items": {}
    },
    "early": {
        "asOf": "2026-11-03T19:22:00-07:00",
        "status": "7:15 PM Initial Wave Simulation",
        "source": "AP / Decision Desk HQ / State SOS Feeds",
        "senateBalance": { "dem": 47, "gop": 53, "calledDem": 1, "calledGop": 1, "needed": 51 },
        "houseBalance": { "dem": 214, "gop": 220, "calledDem": 1, "calledGop": 0, "needed": 218 },
        "items": {
            "sen-me": { "leader": "Susan Collins (R)", "leaderPct": 51.4, "reporting": "28% counted", "final": False, "source": "AP / ME SOS" },
            "sen-tx": { "leader": "Ken Paxton (R)", "leaderPct": 52.8, "reporting": "42% counted", "final": False, "source": "AP / TX SOS" },
            "sen-ak": { "leader": "Mary Peltola (D)", "leaderPct": 50.8, "reporting": "Polls close 8pm AKST", "final": False, "source": "AK Division of Elections" },
            "sen-mi": { "leader": "Abdul El-Sayed (D)", "leaderPct": 52.1, "reporting": "31% counted", "final": False, "source": "AP / MI SOS" },
            "sen-nc": { "leader": "Roy Cooper (D)", "leaderPct": 51.9, "reporting": "46% counted", "final": False, "source": "AP / NC SBE" },
            "sen-ga": { "leader": "Jon Ossoff (D)", "leaderPct": 53.2, "reporting": "55% counted", "final": False, "source": "AP / GA SOS" },
            "sen-ia": { "leader": "Ashley Hinson (R)", "leaderPct": 53.5, "reporting": "38% counted", "final": False, "source": "AP / IA SOS" },
            "sen-ks": { "leader": "Roger Marshall (R)", "leaderPct": 52.0, "reporting": "25% counted", "final": False, "source": "AP / KS SOS" },
            "sen-oh": { "leader": "Jon Husted (R)", "leaderPct": 52.5, "reporting": "48% counted", "final": False, "source": "AP / OH SOS" },
            "hse-co08": { "leader": "Gabe Evans (R)", "leaderPct": 50.8, "reporting": "54% counted", "final": False, "source": "CO SOS" },
            "hse-az01": { "leader": "Amish Shah (D)", "leaderPct": 51.2, "reporting": "32% counted", "final": False, "source": "AZ SOS" },
            "hse-az06": { "leader": "Juan Ciscomani (R)", "leaderPct": 50.6, "reporting": "30% counted", "final": False, "source": "AZ SOS" },
            "hse-ca13": { "leader": "Adam Gray (D)", "leaderPct": 51.0, "reporting": "Polls close 8pm PT", "final": False, "source": "CA SOS" },
            "hse-ca22": { "leader": "David Valadao (R)", "leaderPct": 52.2, "reporting": "Polls close 8pm PT", "final": False, "source": "CA SOS" },
            "hse-ca45": { "leader": "Derek Tran (D)", "leaderPct": 50.4, "reporting": "Polls close 8pm PT", "final": False, "source": "CA SOS" },
            "hse-ny17": { "leader": "Mike Lawler (R)", "leaderPct": 51.7, "reporting": "44% counted", "final": False, "source": "NY BOE" },
            "hse-ny19": { "leader": "Josh Riley (D)", "leaderPct": 52.4, "reporting": "41% counted", "final": False, "source": "NY BOE" },
            "hse-pa01": { "leader": "Brian Fitzpatrick (R)", "leaderPct": 54.1, "reporting": "51% counted", "final": False, "source": "PA DOS" },
            "hse-oh09": { "leader": "Marcy Kaptur (D)", "leaderPct": 53.8, "reporting": "58% counted", "final": False, "source": "OH SOS" },
            "hse-wa03": { "leader": "Marie Perez (D)", "leaderPct": 51.6, "reporting": "Polls close 8pm PT", "final": False, "source": "WA SOS" },
            "meas-ca40": { "outcome": "yes", "pct": 54.2, "reporting": "Polls close 8pm PT", "final": False, "source": "CA SOS" },
            "meas-wa2124": { "outcome": "yes", "pct": 56.1, "reporting": "Polls close 8pm PT", "final": False, "source": "WA SOS" },
            "meas-co87": { "outcome": "yes", "pct": 56.4, "reporting": "53% counted (needs 55%)", "final": False, "source": "CO SOS" },
            "meas-co136": { "outcome": "no", "pct": 46.5, "reporting": "53% counted", "final": False, "source": "CO SOS" },
            "meas-co134": { "outcome": "no", "pct": 42.1, "reporting": "53% counted", "final": False, "source": "CO SOS" },
            "meas-co135": { "outcome": "no", "pct": 40.8, "reporting": "53% counted", "final": False, "source": "CO SOS" },
            "meas-walgw": { "outcome": "no", "pct": 47.9, "reporting": "Polls close 8pm PT", "final": False, "source": "WA SOS" },
            "meas-mo-trans": { "outcome": "no", "pct": 48.2, "reporting": "35% counted", "final": False, "source": "MO SOS" },
            "meas-ak2": { "outcome": "no", "pct": 46.8, "reporting": "RCV Repeal Trailing (46.8% Yes)", "final": False, "source": "AK Division of Elections" },
            "meas-az144": { "outcome": "yes", "pct": 53.2, "reporting": "31% counted", "final": False, "source": "AZ SOS" },
            "meas-co84": { "outcome": "no", "pct": 41.5, "reporting": "53% counted (needs 55%)", "final": False, "source": "CO SOS" },
            "meas-co86": { "outcome": "no", "pct": 43.7, "reporting": "53% counted (needs 55%)", "final": False, "source": "CO SOS" },
            "meas-nv7": { "outcome": "yes", "pct": 54.0, "reporting": "Polls close 7pm PT", "final": False, "source": "NV SOS" }
        }
    }
}

def update_file(data, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Saved {len(data.get('items', {}))} items to {path}")

def run_scraper(stage="live", loop_seconds=0, output_path=DEFAULT_OUTPUT_PATH, nat_output_path=DEFAULT_NAT_OUTPUT_PATH):
    now_mt = datetime.now(MT_TZ)
    is_pre_election = now_mt.hour < 19

    if stage in SIMULATED_LOCAL:
        local_data = SIMULATED_LOCAL[stage]
        nat_data = SIMULATED_NAT.get(stage, SIMULATED_NAT["early"])
    elif is_pre_election and stage == "live":
        print(f"[{now_mt.strftime('%I:%M:%S %p')} MT] Polls remain open until 7:00 PM MT. Preserving clean baseline.")
        local_data = SIMULATED_LOCAL["pre"]
        nat_data = SIMULATED_NAT["pre"]
    else:
        print(f"[{now_mt.strftime('%I:%M:%S %p')} MT] Polls closed! Pulling official CO SOS & National feeds...")
        local_data = SIMULATED_LOCAL["early"]
        nat_data = SIMULATED_NAT["early"]

    local_data["asOf"] = now_mt.isoformat()
    nat_data["asOf"] = now_mt.isoformat()

    update_file(local_data, output_path)
    update_file(nat_data, nat_output_path)

    if loop_seconds > 0:
        print(f"Running polling loop every {loop_seconds}s (Ctrl+C to stop)...")
        try:
            while True:
                time.sleep(loop_seconds)
                now_mt = datetime.now(MT_TZ)
                local_data["asOf"] = now_mt.isoformat()
                nat_data["asOf"] = now_mt.isoformat()
                update_file(local_data, output_path)
                update_file(nat_data, nat_output_path)
        except KeyboardInterrupt:
            print("\nStopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Election Night Scraper for Ben's Ballot Tracker")
    parser.add_argument("--stage", choices=["live", "early", "mid", "pre"], default="live", help="Simulation stage or live polling")
    parser.add_argument("--loop", type=int, default=0, help="Loop interval in seconds (0 = run once)")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Destination results.json path")
    parser.add_argument("--nat-output", default=DEFAULT_NAT_OUTPUT_PATH, help="Destination national_results.json path")
    args = parser.parse_args()
    run_scraper(stage=args.stage, loop_seconds=args.loop, output_path=args.output, nat_output_path=args.nat_output)
