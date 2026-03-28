"""
PlanO Map Layer Engine — serves custom overlay layers over base map tiles.

Layers (added progressively):
  L0: Base map (OpenMapTiles / Protomaps — world vector tiles)
  L1: SCADA infrastructure (Malta — 8,154 assets)
  L2: TSCM emitters (BLE/WiFi heatmap — 3,707 emitters)
  L3: Intelligence overlay (persons of interest, locations, events)
  L4: Property / real estate (ownership, valuations, permits)
  L5: AdS-CFT field map (physics-based RF propagation)
  L6: Forensic timeline (geolocated events over time)

Each layer serves as GeoJSON via API, consumed by MapLibre as sources.
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


DATA_DIR = Path.home() / "data-gathering-agent"


class MapLayerEngine:
    """Serves geographic overlay layers from C4ISR databases."""

    def __init__(self):
        self._cache = {}
        self._cache_ts = {}

    def _cache_get(self, key: str, max_age: int = 300) -> Optional[dict]:
        """Return cached value if fresh."""
        if key in self._cache:
            age = (datetime.now() - self._cache_ts[key]).total_seconds()
            if age < max_age:
                return self._cache[key]
        return None

    def _cache_set(self, key: str, value: dict):
        self._cache[key] = value
        self._cache_ts[key] = datetime.now()

    # ── L1: SCADA Infrastructure ──

    def scada_layer(self, bounds: Optional[Dict] = None) -> dict:
        """Malta SCADA assets as GeoJSON."""
        cached = self._cache_get("scada")
        if cached:
            return cached

        features = []
        db_path = DATA_DIR / "scada_mt.db"
        if not db_path.exists():
            return {"type": "FeatureCollection", "features": []}

        try:
            c = sqlite3.connect(str(db_path))
            c.row_factory = sqlite3.Row
            cur = c.cursor()
            cur.execute("SELECT * FROM assets LIMIT 10000")
            for row in cur.fetchall():
                r = dict(row)
                lat = r.get("latitude") or r.get("lat")
                lng = r.get("longitude") or r.get("lng") or r.get("lon")
                if lat and lng:
                    try:
                        features.append({
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": [float(lng), float(lat)]},
                            "properties": {
                                "name": r.get("name", ""),
                                "type": r.get("asset_type", r.get("type", "")),
                                "operator": r.get("operator", ""),
                                "status": r.get("status", ""),
                                "category": "scada",
                                "layer": "L1",
                            }
                        })
                    except (ValueError, TypeError):
                        pass
            c.close()
        except Exception:
            pass

        result = {"type": "FeatureCollection", "features": features, "layer": "L1_SCADA", "count": len(features)}
        self._cache_set("scada", result)
        return result

    # ── L2: TSCM Emitters ──

    def tscm_layer(self) -> dict:
        """TSCM emitters as GeoJSON with signal strength."""
        import requests
        try:
            r = requests.get("http://127.0.0.1:8450/api/emitters", timeout=5)
            emitters = r.json() if isinstance(r.json(), list) else r.json().get("emitters", [])
        except Exception:
            emitters = []

        features = []
        for e in emitters:
            lat = e.get("lat") or e.get("latitude")
            lng = e.get("lng") or e.get("longitude") or e.get("lon")
            if lat and lng:
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [float(lng), float(lat)]},
                    "properties": {
                        "mac": e.get("mac", ""),
                        "name": e.get("name", e.get("ssid", "")),
                        "type": e.get("type", "unknown"),
                        "signal": e.get("rssi", e.get("signal_strength", -100)),
                        "first_seen": e.get("first_seen", ""),
                        "last_seen": e.get("last_seen", ""),
                        "category": "tscm",
                        "layer": "L2",
                    }
                })

        return {"type": "FeatureCollection", "features": features, "layer": "L2_TSCM", "count": len(features)}

    # ── L3: Intelligence Overlay ──

    def intel_layer(self) -> dict:
        """Persons of interest and intelligence events as GeoJSON."""
        features = []

        # From ID cards with location
        try:
            with open(DATA_DIR / "id_cards.json") as f:
                cards = json.load(f)
            for card in cards:
                loc = card.get("location", "")
                if not loc:
                    continue
                # Geocode known locations
                coords = self._geocode_known(loc)
                if coords:
                    dd = card.get("due_diligence", {})
                    features.append({
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": coords},
                        "properties": {
                            "name": card.get("name", ""),
                            "role": card.get("role", ""),
                            "category_person": card.get("category", ""),
                            "risk_flags": dd.get("risk_flags", 0),
                            "dd_findings": dd.get("findings_count", 0),
                            "nationality": card.get("nationality", ""),
                            "category": "intel",
                            "layer": "L3",
                        }
                    })
        except Exception:
            pass

        return {"type": "FeatureCollection", "features": features, "layer": "L3_INTEL", "count": len(features)}

    # ── L4: Real Estate ──

    def property_layer(self) -> dict:
        """Property and real estate data as GeoJSON."""
        features = []
        # Known properties from the case
        properties = [
            {"name": "Fort Cambridge Apt 1901", "lat": 35.9167, "lng": 14.4933,
             "type": "apartment", "owner": "Hadrien Majoie", "status": "occupied"},
            {"name": "Fort Cambridge Apt 1801", "lat": 35.9167, "lng": 14.4933,
             "type": "apartment", "owner": "disputed", "status": "contested"},
        ]

        # TODO: Enrich from Malta Lands Authority data

        for p in properties:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [p["lng"], p["lat"]]},
                "properties": {
                    "name": p["name"],
                    "type": p["type"],
                    "owner": p.get("owner", ""),
                    "status": p.get("status", ""),
                    "category": "property",
                    "layer": "L4",
                }
            })

        return {"type": "FeatureCollection", "features": features, "layer": "L4_PROPERTY", "count": len(features)}

    # ── L6: Forensic Timeline (geolocated events) ──

    def timeline_layer(self, start_date: str = None, end_date: str = None) -> dict:
        """Geolocated timeline events as GeoJSON."""
        features = []
        try:
            c = sqlite3.connect(str(DATA_DIR / "divorce_evidence.db"))
            cur = c.cursor()
            query = "SELECT event_date, event_type, description FROM timeline_events WHERE description LIKE '%Malta%' OR description LIKE '%Monaco%' OR description LIKE '%Paris%'"
            if start_date:
                query += f" AND event_date >= '{start_date}'"
            if end_date:
                query += f" AND event_date <= '{end_date}'"
            query += " ORDER BY event_date DESC LIMIT 500"
            cur.execute(query)
            for date, etype, desc in cur.fetchall():
                coords = self._geocode_from_text(desc)
                if coords:
                    features.append({
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": coords},
                        "properties": {
                            "date": date,
                            "type": etype,
                            "description": desc[:200],
                            "category": "timeline",
                            "layer": "L6",
                        }
                    })
            c.close()
        except Exception:
            pass

        return {"type": "FeatureCollection", "features": features, "layer": "L6_TIMELINE", "count": len(features)}

    # ── Layer Index ──

    def available_layers(self) -> List[dict]:
        """List all available map layers."""
        return [
            {"id": "L0", "name": "Base Map", "type": "vector_tiles", "source": "self-hosted PMTiles",
             "endpoint": None, "description": "OpenMapTiles world map"},
            {"id": "L1", "name": "SCADA Infrastructure", "type": "geojson", "source": "scada_mt.db",
             "endpoint": "/layers/scada", "description": "8,154 Malta SCADA assets"},
            {"id": "L2", "name": "TSCM Emitters", "type": "geojson", "source": "tscm_heatmap API",
             "endpoint": "/layers/tscm", "description": "BLE/WiFi emitters with signal strength"},
            {"id": "L3", "name": "Intelligence", "type": "geojson", "source": "id_cards.json",
             "endpoint": "/layers/intel", "description": "Persons of interest geolocated"},
            {"id": "L4", "name": "Real Estate", "type": "geojson", "source": "property data",
             "endpoint": "/layers/property", "description": "Property ownership and status"},
            {"id": "L5", "name": "AdS-CFT Field", "type": "grid", "source": "ads_geo_engine",
             "endpoint": "/ads/field-map", "description": "Physics-based RF field map"},
            {"id": "L6", "name": "Forensic Timeline", "type": "geojson", "source": "divorce_evidence.db",
             "endpoint": "/layers/timeline", "description": "Geolocated events over time"},
        ]

    # ── Geocoding helpers ──

    @staticmethod
    def _geocode_known(location: str) -> Optional[List[float]]:
        """Simple geocoder for known locations."""
        known = {
            "malta": [14.5146, 35.8989],
            "valletta": [14.5146, 35.8989],
            "sliema": [14.5020, 35.9130],
            "st julians": [14.4893, 35.9186],
            "monaco": [7.4246, 43.7384],
            "monte carlo": [7.4246, 43.7384],
            "paris": [2.3522, 48.8566],
            "geneva": [6.1432, 46.2044],
            "zurich": [8.5417, 47.3769],
            "sydney": [151.2093, -33.8688],
            "london": [0.1278, 51.5074],
            "san marino": [12.4578, 43.9424],
            "nice": [7.2620, 43.7102],
            "marseille": [5.3698, 43.2965],
            "rome": [12.4964, 41.9028],
            "dubai": [55.2708, 25.2048],
            "liechtenstein": [9.5215, 47.1660],
        }
        loc_lower = location.lower().strip()
        for key, coords in known.items():
            if key in loc_lower:
                return coords
        return None

    @staticmethod
    def _geocode_from_text(text: str) -> Optional[List[float]]:
        """Extract location from event description text."""
        text_lower = text.lower()
        locations = {
            "fort cambridge": [14.4933, 35.9167],
            "malta": [14.5146, 35.8989],
            "sliema": [14.5020, 35.9130],
            "monaco": [7.4246, 43.7384],
            "paris": [2.3522, 48.8566],
            "corradino": [14.5000, 35.8720],
        }
        for key, coords in locations.items():
            if key in text_lower:
                return coords
        return None


def register_layer_routes(app):
    """Register map layer endpoints on the FastAPI app."""
    from fastapi import Query

    engine = MapLayerEngine()

    @app.get("/layers")
    def list_layers():
        return {"layers": engine.available_layers()}

    @app.get("/layers/scada")
    def get_scada():
        return engine.scada_layer()

    @app.get("/layers/tscm")
    def get_tscm():
        return engine.tscm_layer()

    @app.get("/layers/intel")
    def get_intel():
        return engine.intel_layer()

    @app.get("/layers/property")
    def get_property():
        return engine.property_layer()

    @app.get("/layers/timeline")
    def get_timeline(start: str = Query(None), end: str = Query(None)):
        return engine.timeline_layer(start_date=start, end_date=end)
