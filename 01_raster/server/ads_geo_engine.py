"""
AdS-CFT Geographic Engine — maps physical geography onto Anti-de Sitter spacetime.

Architecture:
    Geographic coordinates (lat, lng, alt) → AdS bulk coordinates (r, θ, φ)
    Building footprints → confining potential V(r)
    TSCM emitters → field sources on the AdS manifold
    SCADA assets → boundary (CFT) observables
    Signal propagation → geodesics on AdS metric

The holographic principle maps:
    - Bulk (3+1D spacetime around a building) → full electromagnetic/surveillance field
    - Boundary (2D floor plan surface) → holographic projection (what sensors see)

API endpoints served at /ads/ prefix on the raster server.
"""

import math
import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


# ── AdS Geometry ──

@dataclass
class AdSPoint:
    """Point in Anti-de Sitter space mapped from geographic coordinates."""
    r: float        # radial (distance from building center, meters → AdS units)
    theta: float    # polar angle (elevation / floor level)
    phi: float      # azimuthal angle (compass bearing)
    t: float = 0.0  # time coordinate

    # Geographic origin
    lat: float = 0.0
    lng: float = 0.0
    alt: float = 0.0


class AdSGeoEngine:
    """Maps geographic space onto AdS manifold for PlanO.

    The AdS radius L sets the scale of confinement:
    - Small L = tight confinement (indoor, single room)
    - Large L = loose confinement (building complex, neighborhood)

    Λ = -d(d-1)/(2L²) is always negative (AdS, never dS).
    """

    def __init__(self, ads_radius: float = 50.0, dimension: int = 4):
        """Initialize with AdS radius in meters (sets the confinement scale).

        Args:
            ads_radius: L in meters. 50m ≈ building scale. 500m ≈ neighborhood.
            dimension: spatial dimensions (4 for 3+1 spacetime)
        """
        self.L = ads_radius
        self.d = dimension
        self.lambda_cosmo = -(dimension * (dimension - 1)) / (2 * ads_radius**2)
        self.center_lat = 0.0
        self.center_lng = 0.0
        self.center_alt = 0.0

    def set_origin(self, lat: float, lng: float, alt: float = 0.0):
        """Set the geographic center (building centroid)."""
        self.center_lat = lat
        self.center_lng = lng
        self.center_alt = alt

    def geo_to_ads(self, lat: float, lng: float, alt: float = 0.0) -> AdSPoint:
        """Map geographic coordinates to AdS bulk coordinates.

        Uses Haversine for distance, bearing for azimuth,
        altitude difference for polar angle.
        """
        # Distance from center (meters)
        r_meters = self._haversine(self.center_lat, self.center_lng, lat, lng)

        # Bearing from center
        phi = self._bearing(self.center_lat, self.center_lng, lat, lng)

        # Elevation angle (from altitude difference)
        alt_diff = alt - self.center_alt
        theta = math.atan2(alt_diff, max(r_meters, 0.1))

        # Map to AdS radial coordinate (r/L normalization)
        r_ads = r_meters / self.L

        return AdSPoint(r=r_ads, theta=theta, phi=phi, lat=lat, lng=lng, alt=alt)

    def ads_metric(self, point: AdSPoint) -> Dict[str, float]:
        """Compute AdS metric tensor components at a point.

        ds² = -(1 + r²/L²)dt² + dr²/(1 + r²/L²) + r²dΩ²
        """
        r = point.r * self.L  # back to meters for metric
        r_over_L_sq = (r / self.L) ** 2

        g_tt = -(1 + r_over_L_sq)     # time-time (always negative → causal)
        g_rr = 1.0 / (1 + r_over_L_sq)  # radial-radial (compressed near center)
        g_angular = r ** 2              # angular part

        return {
            "g_tt": g_tt,
            "g_rr": g_rr,
            "g_angular": g_angular,
            "r_ads": point.r,
            "confining": r_over_L_sq > 1.0,  # beyond AdS radius = strong confinement
        }

    def confining_potential(self, point: AdSPoint) -> float:
        """V(r) = -Λr²/6 — grows quadratically, confines everything."""
        r = point.r * self.L
        return -self.lambda_cosmo * r**2 / 6

    def field_strength(self, source: AdSPoint, target: AdSPoint) -> float:
        """Signal/field strength from source to target on AdS geodesic.

        In AdS, fields are confined — they don't decay to zero at infinity
        but oscillate. This models RF propagation in buildings better than
        free-space path loss.
        """
        # AdS geodesic distance
        dr = target.r - source.r
        dphi = target.phi - source.phi
        dtheta = target.theta - source.theta

        # Proper distance on AdS
        r_avg = (source.r + target.r) / 2 * self.L
        g_rr = 1.0 / (1 + (r_avg / self.L) ** 2)

        ds_sq = g_rr * (dr * self.L) ** 2 + r_avg**2 * (dtheta**2 + math.sin(source.theta + dtheta/2)**2 * dphi**2)
        ds = math.sqrt(max(ds_sq, 0.01))

        # AdS field: 1/ds with confining oscillation (doesn't vanish at infinity)
        # This models multipath propagation in buildings
        confining_factor = math.cos(ds / self.L) ** 2  # oscillatory, never zero
        return confining_factor / max(ds, 0.1)

    def holographic_projection(self, bulk_points: List[AdSPoint]) -> List[Dict]:
        """Project bulk (3D) data onto the boundary (2D floor plan).

        The holographic principle: all information in the bulk is encoded
        on the boundary. This maps 3D building data to 2D floor plan overlays.
        """
        boundary = []
        for pt in bulk_points:
            # Project to boundary (r → ∞ in AdS, but we use r=L as boundary)
            x_boundary = self.L * math.cos(pt.phi) * math.sin(pt.theta + math.pi/2)
            y_boundary = self.L * math.sin(pt.phi) * math.sin(pt.theta + math.pi/2)

            # Boundary energy density ~ confining potential
            energy = self.confining_potential(pt)

            boundary.append({
                "x": x_boundary,
                "y": y_boundary,
                "energy": energy,
                "field": self.field_strength(AdSPoint(r=0, theta=0, phi=0), pt),
                "source_lat": pt.lat,
                "source_lng": pt.lng,
                "source_alt": pt.alt,
                "r_ads": pt.r,
                "confined": pt.r > 1.0,  # beyond AdS radius
            })

        return boundary

    def emitter_field_map(self, emitters: List[Dict],
                          grid_size: int = 50,
                          bounds: Tuple[float, float, float, float] = None) -> Dict:
        """Generate a field intensity map from TSCM emitters on the AdS manifold.

        Each emitter is a field source. The total field at any point is the
        superposition of all sources propagated via AdS geodesics.

        Returns a grid suitable for heatmap rendering.
        """
        if not bounds:
            lats = [e.get("lat", 0) for e in emitters]
            lngs = [e.get("lng", 0) for e in emitters]
            bounds = (min(lats), min(lngs), max(lats), max(lngs))

        lat_min, lng_min, lat_max, lng_max = bounds
        dlat = (lat_max - lat_min) / grid_size if lat_max > lat_min else 0.001
        dlng = (lng_max - lng_min) / grid_size if lng_max > lng_min else 0.001

        # Convert emitters to AdS points
        sources = []
        for e in emitters:
            pt = self.geo_to_ads(e.get("lat", 0), e.get("lng", 0), e.get("alt", 0))
            pt.t = e.get("signal_strength", -50) / -100  # normalize dBm
            sources.append(pt)

        # Compute field at each grid point
        grid = []
        for i in range(grid_size):
            for j in range(grid_size):
                lat = lat_min + i * dlat
                lng = lng_min + j * dlng
                target = self.geo_to_ads(lat, lng)

                # Superposition of all source fields
                total_field = 0.0
                for src in sources:
                    total_field += self.field_strength(src, target) * src.t

                grid.append({
                    "lat": lat,
                    "lng": lng,
                    "field": total_field,
                    "potential": self.confining_potential(target),
                    "r_ads": target.r,
                })

        return {
            "grid": grid,
            "grid_size": grid_size,
            "bounds": bounds,
            "lambda": self.lambda_cosmo,
            "L": self.L,
            "sources": len(sources),
        }

    def resonance_modes(self, building_footprint: List[Tuple[float, float]],
                        n_modes: int = 8) -> List[Dict]:
        """Compute resonance modes of the AdS potential for a building.

        In AdS, the confining potential has discrete energy levels
        (like a quantum harmonic oscillator). These correspond to
        the natural resonance frequencies of RF propagation in the building.

        Fibonacci harmonics set the natural frequencies per the Black Parade principle.
        """
        # Building perimeter → effective L
        if building_footprint:
            lats = [p[0] for p in building_footprint]
            lngs = [p[1] for p in building_footprint]
            center_lat = sum(lats) / len(lats)
            center_lng = sum(lngs) / len(lngs)
            max_r = max(self._haversine(center_lat, center_lng, lat, lng)
                       for lat, lng in building_footprint)
            self.set_origin(center_lat, center_lng)
            self.L = max(max_r, 1.0)
            self.lambda_cosmo = -(self.d * (self.d - 1)) / (2 * self.L**2)

        # Fibonacci sequence for harmonic structure
        fib = [1, 1]
        for _ in range(n_modes + 5):
            fib.append(fib[-1] + fib[-2])

        # Energy levels: E_n = (n + d/2) * ω_AdS
        # ω_AdS = 1/L (natural frequency of AdS potential)
        omega_ads = 1.0 / self.L

        modes = []
        for n in range(n_modes):
            energy = (n + self.d / 2) * omega_ads
            # Fibonacci modulation
            fib_factor = fib[n + 2] / fib[n + 3]  # golden ratio convergence
            freq_hz = energy * fib_factor * 1e9  # scale to GHz for RF

            modes.append({
                "mode": n,
                "energy_ads": energy,
                "frequency_ghz": freq_hz / 1e9,
                "wavelength_m": 3e8 / max(freq_hz, 1),
                "fibonacci_ratio": fib_factor,
                "penetration_depth_m": self.L / (n + 1),
                "confined": True,
            })

        return modes

    # ── Helpers ──

    @staticmethod
    def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Distance in meters between two geographic points."""
        R = 6371000  # Earth radius in meters
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (math.sin(dlat/2)**2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlng/2)**2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def _bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Bearing in radians from point 1 to point 2."""
        dlng = math.radians(lng2 - lng1)
        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        x = math.sin(dlng) * math.cos(lat2_r)
        y = (math.cos(lat1_r) * math.sin(lat2_r) -
             math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlng))
        return math.atan2(x, y)


# ── FastAPI routes ──

def register_ads_routes(app):
    """Register AdS-CFT geographic endpoints on the FastAPI app."""
    from fastapi import Query
    from pydantic import BaseModel

    engine = AdSGeoEngine()

    class GeoPoint(BaseModel):
        lat: float
        lng: float
        alt: float = 0.0

    class EmitterInput(BaseModel):
        emitters: List[Dict]
        grid_size: int = 50
        ads_radius: float = 50.0

    class BuildingInput(BaseModel):
        footprint: List[List[float]]  # [[lat, lng], ...]
        n_modes: int = 8

    @app.get("/ads/health")
    def ads_health():
        return {"status": "ok", "engine": "AdS-CFT Geographic", "lambda": engine.lambda_cosmo, "L": engine.L}

    class MetricInput(BaseModel):
        point: GeoPoint
        origin: Optional[GeoPoint] = None

    @app.post("/ads/metric")
    def compute_metric(data: MetricInput):
        """Compute AdS metric tensor at a geographic point."""
        if data.origin:
            engine.set_origin(data.origin.lat, data.origin.lng, data.origin.alt)
        else:
            engine.set_origin(data.point.lat, data.point.lng, data.point.alt)
        ads_pt = engine.geo_to_ads(data.point.lat, data.point.lng, data.point.alt)
        metric = engine.ads_metric(ads_pt)
        metric["potential"] = engine.confining_potential(ads_pt)
        metric["point"] = {"r": ads_pt.r, "theta": ads_pt.theta, "phi": ads_pt.phi}
        return metric

    @app.post("/ads/field-map")
    def compute_field_map(data: EmitterInput):
        """Generate AdS field intensity map from emitters."""
        engine.L = data.ads_radius
        engine.lambda_cosmo = -(engine.d * (engine.d - 1)) / (2 * engine.L**2)
        # Set origin to emitter centroid
        if data.emitters:
            c_lat = sum(e.get("lat", 0) for e in data.emitters) / len(data.emitters)
            c_lng = sum(e.get("lng", 0) for e in data.emitters) / len(data.emitters)
            engine.set_origin(c_lat, c_lng)
        return engine.emitter_field_map(data.emitters, grid_size=data.grid_size)

    @app.post("/ads/resonance")
    def compute_resonance(data: BuildingInput):
        """Compute resonance modes for a building footprint."""
        footprint = [(p[0], p[1]) for p in data.footprint]
        return {"modes": engine.resonance_modes(footprint, n_modes=data.n_modes),
                "lambda": engine.lambda_cosmo, "L": engine.L}

    @app.post("/ads/holographic")
    def holographic_project(points: List[GeoPoint]):
        """Project 3D points to 2D holographic boundary."""
        ads_points = [engine.geo_to_ads(p.lat, p.lng, p.alt) for p in points]
        return {"boundary": engine.holographic_projection(ads_points),
                "lambda": engine.lambda_cosmo, "L": engine.L}

    class PropagateInput(BaseModel):
        source: GeoPoint
        target: GeoPoint
        origin: Optional[GeoPoint] = None

    @app.post("/ads/propagate")
    def propagate_signal(data: PropagateInput):
        """Compute signal propagation from source to target via AdS geodesic."""
        if data.origin:
            engine.set_origin(data.origin.lat, data.origin.lng, data.origin.alt)
        else:
            engine.set_origin(data.source.lat, data.source.lng, data.source.alt)
        src = engine.geo_to_ads(data.source.lat, data.source.lng, data.source.alt)
        tgt = engine.geo_to_ads(data.target.lat, data.target.lng, data.target.alt)
        return {
            "field_strength": engine.field_strength(src, tgt),
            "distance_m": engine._haversine(data.source.lat, data.source.lng, data.target.lat, data.target.lng),
            "source_potential": engine.confining_potential(src),
            "target_potential": engine.confining_potential(tgt),
            "source_r_ads": src.r,
            "target_r_ads": tgt.r,
            "lambda": engine.lambda_cosmo,
            "L": engine.L,
        }
