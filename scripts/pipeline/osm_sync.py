#!/usr/bin/env python3
"""
PlanO — OSM Building Data Sync Pipeline

Downloads fresh OpenStreetMap building data for target countries.
Runs on a schedule (weekly) to keep map overlays and building metadata current.

Usage:
    python3 osm_sync.py sync [--country MT|IT|ES|ALL]
    python3 osm_sync.py stats
    python3 osm_sync.py diff   # show changes since last sync

DEBUG: Set PLANO_DEBUG=1 for verbose logging
"""

import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Config ──

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "osm"
LOG_DIR = BASE_DIR / "logs"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_TIMEOUT = 120  # seconds

# Countries we sync (expand as we enter new markets)
COUNTRIES = {
    "MT": {"name": "Malta", "iso": "MT", "area_tag": "ISO3166-1", "priority": 1},
    "IT": {"name": "Italy", "iso": "IT", "area_tag": "ISO3166-1", "priority": 2},
    "ES": {"name": "Spain", "iso": "ES", "area_tag": "ISO3166-1", "priority": 3},
    "FR": {"name": "France", "iso": "FR", "area_tag": "ISO3166-1", "priority": 4},
    "DE": {"name": "Germany", "iso": "DE", "area_tag": "ISO3166-1", "priority": 5},
    "PT": {"name": "Portugal", "iso": "PT", "area_tag": "ISO3166-1", "priority": 6},
    "NL": {"name": "Netherlands", "iso": "NL", "area_tag": "ISO3166-1", "priority": 7},
    "GR": {"name": "Greece", "iso": "GR", "area_tag": "ISO3166-1", "priority": 8},
    "IE": {"name": "Ireland", "iso": "IE", "area_tag": "ISO3166-1", "priority": 9},
    "BE": {"name": "Belgium", "iso": "BE", "area_tag": "ISO3166-1", "priority": 10},
}

logging.basicConfig(
    level=logging.DEBUG if os.environ.get("PLANO_DEBUG") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("plano.osm_sync")


def _overpass_query(country_iso: str) -> str:
    """Build Overpass QL query for all buildings in a country."""
    return f"""
[out:json][timeout:{OVERPASS_TIMEOUT}];
area["{COUNTRIES[country_iso]['area_tag']}"="{country_iso}"]->.a;
(
  way["building"](area.a);
  relation["building"](area.a);
);
out body;
>;
out skel qt;
"""


def sync_country(country_iso: str) -> dict:
    """Download OSM building data for a single country.

    Returns:
        dict with keys: country, buildings, with_levels, with_address, file_size, duration
    """
    country = COUNTRIES[country_iso]
    out_dir = DATA_DIR / country_iso.lower()
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "buildings.json"
    prev_file = out_dir / "buildings_prev.json"
    meta_file = out_dir / "sync_meta.json"

    log.info("Syncing %s (%s)...", country["name"], country_iso)

    # Rotate previous
    if out_file.exists():
        if prev_file.exists():
            prev_file.unlink()
        out_file.rename(prev_file)

    # Download
    query = _overpass_query(country_iso)
    t0 = time.time()

    try:
        req = urllib.request.Request(
            OVERPASS_URL,
            data=f"data={urllib.parse.quote(query)}".encode(),
            method="POST",
        )
        req.add_header("User-Agent", "PlanO-Pipeline/1.0 (plano.hacking.eu)")

        with urllib.request.urlopen(req, timeout=OVERPASS_TIMEOUT + 30) as resp:
            raw = resp.read()
            out_file.write_bytes(raw)

    except (urllib.error.URLError, TimeoutError) as e:
        log.error("Failed to sync %s: %s", country_iso, e)
        # Restore previous if download failed
        if prev_file.exists():
            prev_file.rename(out_file)
        return {"country": country_iso, "error": str(e)}

    duration = round(time.time() - t0, 1)

    # Parse and count
    data = json.loads(raw)
    elements = data.get("elements", [])
    buildings = [
        e for e in elements
        if e["type"] == "way" and "building" in e.get("tags", {})
    ]
    with_levels = sum(1 for b in buildings if "building:levels" in b.get("tags", {}))
    with_addr = sum(1 for b in buildings if "addr:street" in b.get("tags", {}))
    with_height = sum(1 for b in buildings if "height" in b.get("tags", {}))

    # Compute diff against previous
    diff = {"added": 0, "removed": 0, "modified": 0}
    if prev_file.exists():
        try:
            prev_data = json.loads(prev_file.read_text())
            prev_ids = {e["id"] for e in prev_data.get("elements", []) if e["type"] == "way"}
            curr_ids = {e["id"] for e in elements if e["type"] == "way"}
            diff["added"] = len(curr_ids - prev_ids)
            diff["removed"] = len(prev_ids - curr_ids)
        except Exception:
            pass

    # Save metadata
    meta = {
        "country": country_iso,
        "name": country["name"],
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "buildings": len(buildings),
        "with_levels": with_levels,
        "with_address": with_addr,
        "with_height": with_height,
        "file_size_mb": round(out_file.stat().st_size / 1e6, 1),
        "duration_s": duration,
        "diff": diff,
    }
    meta_file.write_text(json.dumps(meta, indent=2))

    log.info(
        "  %s: %d buildings (%d with levels, %d with addr) in %.1fs (%.1f MB) [+%d -%d]",
        country_iso, len(buildings), with_levels, with_addr,
        duration, meta["file_size_mb"],
        diff["added"], diff["removed"],
    )

    return meta


def sync_all(country_filter: Optional[str] = None) -> list[dict]:
    """Sync all countries (or a single one)."""
    results = []

    if country_filter and country_filter != "ALL":
        if country_filter.upper() not in COUNTRIES:
            log.error("Unknown country: %s. Available: %s", country_filter, list(COUNTRIES.keys()))
            return []
        results.append(sync_country(country_filter.upper()))
    else:
        # Sync in priority order
        sorted_countries = sorted(COUNTRIES.items(), key=lambda x: x[1]["priority"])
        for code, _ in sorted_countries:
            results.append(sync_country(code))
            time.sleep(2)  # be nice to Overpass API

    # Save global summary
    summary_file = DATA_DIR / "sync_summary.json"
    summary = {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "countries": len(results),
        "total_buildings": sum(r.get("buildings", 0) for r in results),
        "results": results,
    }
    summary_file.write_text(json.dumps(summary, indent=2))

    log.info(
        "Sync complete: %d countries, %d total buildings",
        len(results), summary["total_buildings"],
    )
    return results


def show_stats():
    """Show current sync status for all countries."""
    print(f"{'Country':12} {'Buildings':>10} {'Levels':>8} {'Addr':>8} {'Size':>8} {'Synced':>20}")
    print("-" * 76)
    total = 0

    for code in sorted(COUNTRIES.keys()):
        meta_file = DATA_DIR / code.lower() / "sync_meta.json"
        if meta_file.exists():
            m = json.loads(meta_file.read_text())
            print(
                f"{m['name']:12} {m['buildings']:>10,} {m['with_levels']:>8,} "
                f"{m['with_address']:>8,} {m['file_size_mb']:>7.1f}M "
                f"{m['synced_at'][:16]:>20}"
            )
            total += m["buildings"]
        else:
            print(f"{COUNTRIES[code]['name']:12} {'not synced':>10}")

    print("-" * 76)
    print(f"{'TOTAL':12} {total:>10,}")


# ── CLI ──

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "sync":
        country = sys.argv[2] if len(sys.argv) > 2 else "MT"
        sync_all(country.replace("--country", "").strip())

    elif cmd == "stats":
        show_stats()

    elif cmd == "diff":
        for code in sorted(COUNTRIES.keys()):
            meta_file = DATA_DIR / code.lower() / "sync_meta.json"
            if meta_file.exists():
                m = json.loads(meta_file.read_text())
                d = m.get("diff", {})
                if d.get("added") or d.get("removed"):
                    print(f"{m['name']}: +{d['added']} -{d['removed']} buildings")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
