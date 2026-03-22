# TSCM 4D Mapping System -- Architecture Specification

## Status: ACCEPTED
## Date: 2026-03-13

---

## 1. SYSTEM TOPOLOGY

```
                         SSH TUNNEL (gpu-tunnel.service)
                    ports: 11434,5432,8000,8088,6379,8001

 ROG FLOW Z13 (EDGE)                          HADRIEN-SKOED-MT (SERVER)
 ===================                          ==========================
 27GB RAM, 24 CPU, no GPU                     RTX 6000 Ada 49GB VRAM
                                              3TB free disk
 +--------------------------+                 +-------------------------------+
 | Vite React :5174         |                 | Redis :6379                   |
 |  - MapLibre GL JS 3D     |    REST/SSE     |  - Task queue (Bull/BullMQ)   |
 |  - TimeSlider component  |<--------------->|  - Result cache (TTL 5min)    |
 |  - Trail renderer        |                 |                               |
 |  - Texture mesh overlay  |                 | Ollama :11434 (GPU)           |
 +--------------------------+                 |  - Pattern analysis           |
          |  proxy                            |  - Trajectory prediction      |
          v                                   |  - Anomaly detection          |
 +--------------------------+                 |                               |
 | TSCM Flask :8450         |    REST         | TSCM Server Worker :8451      |
 |  - /api/* (existing)     |<--------------->|  - /api/4d/* endpoints        |
 |  - /api/4d/snapshot      |                 |  - /api/textures/*            |
 |  - BLE/WiFi scanning     |                 |  - /api/ai/analyze            |
 |  - Local threat classify |                 |  - Heavy 4D computation       |
 |  - RSSI trilateration    |                 |  - Texture extraction         |
 |  - Edge AI (CPU Ollama)  |                 |  - ML trajectory prediction   |
 +--------------------------+                 +-------------------------------+
          |                                              |
          v                                              v
 +--------------------------+                 +-------------------------------+
 | tscm_heatmap.db (SQLite) |   rsync/REST    | tscm_canonical.db (SQLite)    |
 | 3,682 emitters           |<-- nightly -->  | OR PostgreSQL (c4isr-db)      |
 | 54K readings, 47.8K tomo |                 | Full history + computed data  |
 | 2 floor plans            |                 | Trajectories, predictions     |
 +--------------------------+                 +-------------------------------+
```

---

## 2. FILE STRUCTURE -- WHAT TO CREATE

### Edge (ROG) -- new files under existing projects

```
/home/memorylost/tscm-heatmap/
  tscm_heatmap.py                    # EXISTING -- add /api/4d/* routes
  tscm_edge_ai.py                    # NEW -- edge AI engine (CPU Ollama)
  tscm_sync.py                       # NEW -- edge<->server sync daemon

/home/memorylost/plano_master/00_frontend_skeleton/plano-ui/src/
  components/tscm/
    TscmPanel.tsx                    # EXISTING -- no changes needed
    TscmHeatmapLayer.tsx             # EXISTING -- extend with time filter
    TimeSlider.tsx                   # NEW -- 4D time scrubber/playback
    TrailLayer.tsx                   # NEW -- animated emitter movement polylines
    TextureMeshLayer.tsx             # NEW -- 3D building texture overlay
    FloorPlanLayer.tsx               # NEW -- refactored from TscmHeatmapLayer floor logic
  hooks/
    useTscm4D.ts                     # NEW -- data fetching + time state
  types/
    tscm.ts                          # NEW -- shared TypeScript types
```

### Server (hadrien-skoed-mt) -- new project

```
~/tscm-server/
  tscm_server.py                     # NEW -- Flask/FastAPI heavy compute worker
  tscm_textures.py                   # NEW -- texture extraction from rasta + OSM
  tscm_trajectory.py                 # NEW -- ML trajectory prediction (GPU)
  tscm_ai_bridge.py                  # NEW -- AI-to-AI coordination (Ollama GPU)
  requirements.txt
```

---

## 3. DATA FLOW -- 4D TIMELINE

```
USER DRAGS TIME SLIDER
         |
         v
TimeSlider.tsx  --> useTscm4D.ts --> GET /api/tscm/4d/snapshot?t0=...&t1=...
                                          |
                                          v
                                  tscm_heatmap.py (edge)
                                  [SQLite query: readings WHERE timestamp BETWEEN t0 AND t1]
                                          |
                                          v
                            +----------------------------------+
                            | Response: TscmSnapshot           |
                            | {                                |
                            |   time_range: [t0, t1],          |
                            |   emitters: [{                   |
                            |     id, address, name, type,     |
                            |     threat_level, positions: [{  |
                            |       lat, lng, rssi, timestamp  |
                            |     }]                           |
                            |   }],                            |
                            |   heatmap_points: [{             |
                            |     lat, lng, weight, timestamp  |
                            |   }],                            |
                            |   tomo_grid: [...]               |
                            | }                                |
                            +----------------------------------+
                                          |
                            +-------------+-------------+
                            |                           |
                       TrailLayer.tsx            TscmHeatmapLayer.tsx
                       (animated polylines)     (time-filtered heatmap)
```

---

## 4. API CONTRACTS

### 4.1 Edge APIs (add to tscm_heatmap.py on :8450)

#### GET /api/4d/time-range
Returns the available data range for the time slider.
```json
// Response
{
  "first_reading": "2025-11-15T08:23:38",
  "last_reading": "2026-03-12T18:27:26",
  "total_days": 119,
  "reading_count": 54034,
  "density": [           // readings per day, for sparkline in slider
    {"date": "2025-11-15", "count": 342},
    {"date": "2025-11-16", "count": 518},
    ...
  ]
}
```

#### GET /api/4d/snapshot?t0={iso}&t1={iso}&resolution={low|medium|high}
Returns emitters + positions for a time window. This is the primary 4D query.
```json
// Response
{
  "time_range": {"t0": "2025-12-01T00:00:00", "t1": "2025-12-01T23:59:59"},
  "emitters": [
    {
      "id": 42,
      "address": "AA:BB:CC:DD:EE:FF",
      "name": "Unknown BLE Beacon",
      "emitter_type": "ble",
      "threat_level": "HIGH",
      "positions": [
        {"lat": 35.9131, "lng": 14.5039, "rssi": -65, "ts": "2025-12-01T08:00:00"},
        {"lat": 35.9131, "lng": 14.5040, "rssi": -68, "ts": "2025-12-01T08:15:00"},
        {"lat": 35.9130, "lng": 14.5040, "rssi": -72, "ts": "2025-12-01T09:30:00"}
      ],
      "trail_color": "#f97316"
    }
  ],
  "heatmap_grid": [
    {"lat": 35.9131, "lng": 14.5039, "weight": 0.85, "ts": "2025-12-01T08:00:00"}
  ],
  "stats": {
    "active_emitters": 142,
    "new_this_window": 3,
    "disappeared": 7,
    "max_threat": "HIGH"
  }
}
```

#### GET /api/4d/trail/{emitter_id}?t0={iso}&t1={iso}
Full movement trail for a specific emitter.
```json
// Response
{
  "emitter_id": 42,
  "address": "AA:BB:CC:DD:EE:FF",
  "trail": [
    {"lat": 35.9131, "lng": 14.5039, "rssi": -65, "ts": "2025-12-01T08:00:00", "floor": 2},
    {"lat": 35.9131, "lng": 14.5040, "rssi": -68, "ts": "2025-12-01T08:15:00", "floor": 2}
  ],
  "mobility": "MOBILE",
  "distance_total_m": 12.4,
  "time_span_hours": 4.2
}
```

### 4.2 Server APIs (new tscm_server.py on :8451, tunneled)

#### POST /api/4d/trajectory-predict
GPU-accelerated trajectory prediction.
```json
// Request
{
  "emitter_id": 42,
  "trail": [/* positions array from edge */],
  "predict_minutes": 60
}

// Response
{
  "predicted_positions": [
    {"lat": 35.9130, "lng": 14.5041, "confidence": 0.82, "ts": "2026-03-12T19:00:00"},
    {"lat": 35.9129, "lng": 14.5042, "confidence": 0.65, "ts": "2026-03-12T19:30:00"}
  ],
  "pattern": "PERIODIC_DAILY",
  "model": "mistral-24b-q4"
}
```

#### POST /api/ai/analyze
Server Ollama GPU analysis -- replaces Claude for routine TSCM tasks.
```json
// Request
{
  "task": "threat_assessment",
  "context": {
    "emitter": {/* emitter data */},
    "trail": [/* positions */],
    "nearby_emitters": [/* co-located devices */],
    "time_pattern": "appears_daily_0800_1700"
  }
}

// Response
{
  "assessment": "Device shows characteristics of a commercial BLE tracker...",
  "threat_level_recommendation": "HIGH",
  "confidence": 0.78,
  "reasoning": ["Unknown manufacturer", "Periodic appearance pattern", "Signal strength consistent with concealed device"],
  "recommended_actions": ["Physical sweep of area near coordinates", "Check for AirTag/SmartTag form factor"]
}
```

#### GET /api/textures/building/{osm_id}
Returns texture data for a specific building.
```json
// Response
{
  "osm_id": "way/123456",
  "materials": {
    "walls": "limestone",
    "roof": "concrete_flat",
    "ground_floor": "glass_commercial"
  },
  "texture_urls": {
    "walls": "/api/textures/material/limestone_malta.jpg",
    "roof": "/api/textures/material/concrete_flat.jpg"
  },
  "source": "osm_tags+rasta_detection",
  "confidence": 0.72
}
```

### 4.3 AI-to-AI Bridge

#### POST /api/ai/edge-request (on server :8451)
Edge Ollama delegates heavy tasks to server Ollama.
```json
// Request (from edge tscm_edge_ai.py)
{
  "task_id": "uuid-here",
  "task_type": "pattern_analysis",  // or "anomaly_detection", "trajectory_prediction"
  "payload": {/* task-specific data */},
  "priority": "normal",             // "urgent" for CRITICAL threats
  "callback_url": "http://127.0.0.1:8450/api/ai/result"  // optional webhook
}

// Response (immediate)
{
  "task_id": "uuid-here",
  "status": "queued",
  "estimated_seconds": 15
}
```

#### GET /api/ai/result/{task_id} (on server :8451)
Poll for result (or use callback).
```json
// Response
{
  "task_id": "uuid-here",
  "status": "complete",  // or "processing", "failed"
  "result": {/* task-specific result */},
  "processing_time_ms": 2340,
  "model_used": "mistral-small-abliterated:24b-instruct-2501-q4_K_M"
}
```

---

## 5. FRONTEND COMPONENT DESIGNS

### 5.1 TimeSlider.tsx

Core state managed by `useTscm4D` hook:

```typescript
// /plano-ui/src/types/tscm.ts

export interface TimeRange {
  t0: string;  // ISO timestamp
  t1: string;
}

export interface TscmSnapshot {
  time_range: TimeRange;
  emitters: TscmEmitter4D[];
  heatmap_grid: HeatmapPoint[];
  stats: SnapshotStats;
}

export interface TscmEmitter4D extends TscmEmitter {
  positions: EmitterPosition[];
  trail_color: string;
}

export interface EmitterPosition {
  lat: number;
  lng: number;
  rssi: number;
  ts: string;
  floor?: number;
}

export interface PlaybackState {
  playing: boolean;
  speed: number;          // 0.5, 1, 2, 4, 8
  currentTime: string;    // ISO, the "playhead"
  windowSize: number;     // seconds -- how wide the visible window is
}
```

TimeSlider renders:
- A range slider spanning first_reading..last_reading (119 days)
- A density sparkline behind the slider (readings/day)
- Playback controls: |<< < [play/pause] > >>| with speed selector
- Current time display in top-left of slider
- The slider thumb = current window center; drag to scrub

Behavior:
- On scrub: debounced fetch to `/api/4d/snapshot?t0=...&t1=...`
- On play: advance currentTime by (speed * real elapsed), fetch every 500ms
- Window size adjustable: 1 hour, 6 hours, 1 day, 1 week

### 5.2 TrailLayer.tsx

Renders animated polylines on MapLibre for emitter movement:
- One polyline per emitter with >1 position in current time window
- Color = threat level color
- Animation: growing line segment following timestamp order
- Line width proportional to RSSI (thicker = stronger signal)
- Arrow at head showing direction of movement
- Click on trail point shows timestamp + RSSI popup

Implementation approach:
- GeoJSON source with LineString features per emitter
- Use MapLibre `line-gradient` with `line-progress` for animation
- Update line coordinates on each animation frame during playback
- Limit to top 50 most active emitters to prevent performance issues

### 5.3 TextureMeshLayer.tsx -- Building Textures

MapLibre `fill-extrusion` does NOT support per-face textures natively.
Three viable approaches, in order of recommendation:

**Option A: Custom WebGL overlay (RECOMMENDED)**
- Use MapLibre's `CustomLayerInterface` to render a Three.js scene
- Three.js meshes positioned at building footprint coordinates
- Apply material textures to mesh faces
- Sync Three.js camera with MapLibre camera on every frame
- Gives full control over textures, lighting, reflections

**Option B: Color-coded materials**
- Simpler: use `fill-extrusion-color` with material-based color palette
- limestone = #D4C5A9, concrete = #808080, glass = #87CEEB44 (translucent)
- No actual texture images, but communicates material type visually
- Works today with zero additional libraries

**Option C: Deck.gl overlay**
- Add `@deck.gl/core` + `@deck.gl/mesh-layers`
- Use `SimpleMeshLayer` with OBJ/glTF models per building
- Heavier dependency but mature library

Trade-off: Start with Option B (color-coded) as Phase 1, add Option A (Three.js) in Phase 2. Option B is a 2-hour change to the existing `fill-extrusion` paint. Option A is a multi-day project.

### 5.4 FloorPlanLayer.tsx -- Geo-Anchored Floor Plans

Refactored from existing code in TscmHeatmapLayer.tsx (lines 292-327).

Critical fix needed: the floor plan geo-anchors in the DB show:
- `lat_nw=35.9131, lng_nw=14.5038, lat_se=35.9130, lng_se=14.5041`
- This is Stella Maris, Sliema -- approximately 16m x 26m
- The building footprint from OSM needs to match these bounds exactly

To make floor plans match building size:
1. Query the OSM building polygon for Stella Maris
2. Use the polygon's bounding box as the image source coordinates
3. The existing `image` source approach in MapLibre is correct
4. Add `minzoom: 18` to only show at close zoom
5. Add floor level selector (the DB has `floor_level` column)

---

## 6. IMPLEMENTATION ORDER -- BUILD SEQUENCE

### Phase 1: 4D Time Core (3-4 days) -- HIGHEST VALUE

Files to create/modify:

1. **`/home/memorylost/plano_master/00_frontend_skeleton/plano-ui/src/types/tscm.ts`**
   - TypeScript types for 4D data model

2. **`/home/memorylost/tscm-heatmap/tscm_heatmap.py`** (MODIFY)
   - Add route: `GET /api/4d/time-range`
   - Add route: `GET /api/4d/snapshot?t0=&t1=&resolution=`
   - Add route: `GET /api/4d/trail/{emitter_id}?t0=&t1=`
   - These are pure SQLite queries against existing data -- no new tables needed

3. **`/home/memorylost/plano_master/00_frontend_skeleton/plano-ui/src/hooks/useTscm4D.ts`**
   - React hook: manages time range, current playback state, data fetching
   - Debounced fetch on scrub, interval fetch on playback

4. **`/home/memorylost/plano_master/00_frontend_skeleton/plano-ui/src/components/tscm/TimeSlider.tsx`**
   - Time scrubber UI with play/pause/speed controls
   - Density sparkline

5. **`/home/memorylost/plano_master/00_frontend_skeleton/plano-ui/src/components/tscm/TrailLayer.tsx`**
   - Animated polylines on MapLibre

6. **`/home/memorylost/plano_master/00_frontend_skeleton/plano-ui/src/pages/client/Tscm.tsx`** (MODIFY)
   - Wire TimeSlider and TrailLayer into the TSCM page
   - Pass time range to TscmHeatmapLayer for filtering

**Why first**: This unlocks the 4D dimension using 100% existing data. No server work needed. The 54K readings over 119 days become a visual timeline immediately. Maximum value, minimum new infrastructure.

### Phase 2: Material Colors on Buildings (1 day)

7. **`/home/memorylost/plano_master/00_frontend_skeleton/plano-ui/src/pages/client/Tscm.tsx`** (MODIFY)
   - Change `fill-extrusion-color` paint to use `building:material` tag from OSM vector tiles
   - Add color mapping: `limestone=#D4C5A9, concrete=#808080, glass=rgba(135,206,235,0.3), sandstone=#C2B280`
   - The OpenFreeMap tiles already include `building:material` in properties

**Why second**: One paint expression change gives visual material indication on every building. No new components or server work.

### Phase 3: Floor Plan Alignment Fix (1 day)

8. **`/home/memorylost/plano_master/00_frontend_skeleton/plano-ui/src/components/tscm/FloorPlanLayer.tsx`** (NEW)
   - Extract floor plan logic from TscmHeatmapLayer
   - Add OSM building polygon query to align floor plan to actual footprint
   - Floor level selector UI

9. **`/home/memorylost/plano_master/00_frontend_skeleton/plano-ui/src/components/tscm/TscmHeatmapLayer.tsx`** (MODIFY)
   - Remove floor plan rendering (moved to FloorPlanLayer)
   - Accept time range prop for filtered heatmap

### Phase 4: Server Worker + AI Bridge (3-4 days)

10. **`~/tscm-server/tscm_server.py`** on hadrien-skoed-mt (NEW)
    - FastAPI app on :8451
    - Endpoints: `/api/4d/trajectory-predict`, `/api/ai/analyze`, `/api/textures/*`
    - Redis task queue for async GPU jobs

11. **`~/tscm-server/tscm_ai_bridge.py`** on hadrien-skoed-mt (NEW)
    - Ollama client wrapping GPU-accelerated inference
    - Task types: threat_assessment, pattern_analysis, anomaly_detection, trajectory_prediction
    - Result caching in Redis (5min TTL)

12. **`/home/memorylost/tscm-heatmap/tscm_edge_ai.py`** on ROG (NEW)
    - Lightweight Ollama client for CPU inference
    - Decides locally whether to handle or delegate to server
    - Decision rule: if emitter count < 10 and task is simple classification -> local; else -> server

13. **`/home/memorylost/tscm-heatmap/tscm_sync.py`** on ROG (NEW)
    - Daemon that pushes new readings to server every 5 minutes
    - Pulls computed trajectories/predictions back
    - Uses `POST /api/sync/push` and `GET /api/sync/pull?since=`

**Why fourth**: The system works fully on edge-only for Phases 1-3. Server adds prediction and heavy AI but is not blocking.

### Phase 5: Three.js Texture Overlay (5+ days)

14. **`/home/memorylost/plano_master/00_frontend_skeleton/plano-ui/src/components/tscm/TextureMeshLayer.tsx`** (NEW)
    - MapLibre CustomLayerInterface + Three.js scene
    - Fetches texture data from server `/api/textures/building/{osm_id}`
    - Applies texture images to extruded building meshes
    - Camera sync with MapLibre

15. **`~/tscm-server/tscm_textures.py`** on server (NEW)
    - Rasta engine integration for wall material detection from floor plan images
    - OSM tag enrichment (`building:material`, `building:colour`)
    - Texture atlas generation (limestone, concrete, glass, etc.)

**Why last**: Highest effort, lowest immediate value for TSCM mission. Nice visual upgrade but does not help find threats.

---

## 7. VITE PROXY CONFIGURATION

Add server proxy to existing config:

```typescript
// vite.config.ts -- add to server.proxy
'/api/tscm-server': {
  target: 'http://127.0.0.1:8451',  // tunneled from GPU server
  changeOrigin: true,
  rewrite: (path) => path.replace(/^\/api\/tscm-server/, '/api'),
},
```

The GPU tunnel service needs port 8451 added:
```
# Add to gpu-tunnel.service SSH command
-L 8451:127.0.0.1:8451
```

---

## 8. TRADE-OFF MATRIX

| Decision | Chose | Gave Up | Rationale |
|----------|-------|---------|-----------|
| SQLite on edge, not PG | Simplicity, zero-config, existing data | Concurrent writes, complex queries | 54K rows fits comfortably; reads are the bottleneck, not writes |
| Edge-first 4D (Phase 1) | Immediate value, no infra dependency | Server GPU acceleration | 54K readings query in <100ms on SQLite; GPU not needed for reads |
| Color-coded materials before textures | 2-hour win vs multi-day project | Visual realism | Material colors communicate the same info; textures are cosmetic |
| REST polling over WebSocket | Simpler client, works through proxies | Real-time push, lower latency | 500ms poll during playback is indistinguishable from push at this data scale |
| Bull/Redis task queue on server | Reliable async, retries, priority | Simplicity (could use just REST) | GPU inference takes 2-15s; need queue to avoid timeout and support priority |
| CPU Ollama for edge AI | No GPU dependency, works offline | Speed (5-10x slower than GPU) | Edge only handles lightweight classification; heavy work goes to server |
| MapLibre CustomLayer for textures | Full Three.js control | Simplicity, Deck.gl maturity | Deck.gl adds 500KB+ bundle; Three.js gives exact control we need |

---

## 9. CRITICAL CONSTRAINTS

1. **25% reserve margin** on all resources (Black Parade principle):
   - ROG RAM: use max 20GB of 27GB (keep 7GB free)
   - Server VRAM: use max 37GB of 49GB (keep 12GB for Ollama overhead)
   - SQLite queries: LIMIT all results, paginate, never SELECT * unbounded

2. **Readings query performance**: 54K readings needs index on `(timestamp, emitter_id)`.
   Current indexes: `idx_readings_ts` on timestamp, `idx_readings_emitter` on emitter_id.
   **Add composite index**:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_readings_ts_emitter ON readings(timestamp, emitter_id);
   ```

3. **Floor plan coordinates**: DB says Stella Maris at 35.9131/14.5038.
   The geo_anchors.json has DIFFERENT coordinates (43.77/7.46 = Monaco).
   The DB coordinates are authoritative for the TSCM system.

4. **The Vite proxy rewrites `/api/tscm` to `/api`** -- all new 4D routes on the edge Flask
   must be under `/api/4d/*` which becomes `/api/tscm/4d/*` from the frontend perspective.

---

## 10. ADRs

### ADR-001: Edge-First 4D Timeline

**Status**: Accepted

**Context**: The 4D timeline needs 54K readings queried by time range. We could compute this on the server GPU (more power) or on the edge SQLite (simpler, lower latency).

**Decision**: Phase 1 runs entirely on edge. SQLite queries against indexed timestamp column serve 4D snapshots directly. Server is added in Phase 4 for prediction only.

**Consequences**: The system works offline and without the SSH tunnel. Queries are fast (SQLite with indexes on 54K rows is sub-100ms). We lose server GPU acceleration for the timeline, but gain independence and simplicity. If data grows past 500K readings, we may need to add server-side aggregation.

### ADR-002: Color-Coded Materials Before Texture Maps

**Status**: Accepted

**Context**: Requirement 3 asks for building textures. MapLibre fill-extrusion does not support per-face textures. Options: (A) Three.js custom layer overlay, (B) color-code by material tag, (C) Deck.gl mesh layers.

**Decision**: Phase 2 uses color-coded materials via existing fill-extrusion-color expression. Phase 5 adds Three.js overlay for actual textures.

**Consequences**: Phase 2 is a ~2-hour modification to one paint expression. It visually communicates material type (limestone=tan, concrete=gray, glass=translucent blue). We defer the 5+ day Three.js integration until the core 4D system is proven. Tradeoff: less visually impressive, but much faster to ship and debug.

### ADR-003: REST Polling Over WebSocket for Playback

**Status**: Accepted

**Context**: During 4D playback, the UI needs updated data as the time cursor advances. Options: WebSocket push, SSE, or REST polling.

**Decision**: REST polling at 500ms intervals during playback. The useTscm4D hook manages a setInterval that advances the time cursor and fetches new snapshots.

**Consequences**: Simpler implementation. Works through all proxies without upgrade negotiation. 500ms at 8x speed means we fetch a new 4-second window of data every 500ms real time, which is visually smooth. Downside: slightly more HTTP overhead than a persistent connection. If we later need sub-100ms updates (e.g., live scanning), we add SSE as a separate channel.

### ADR-004: AI Task Delegation Architecture

**Status**: Accepted

**Context**: Both edge (CPU Ollama) and server (GPU Ollama) run the same Mistral 24B model. Need a decision framework for which node handles which tasks.

**Decision**: Edge handles: device identification (known vendor lookup), simple threat classification (rule-based + lightweight prompt), RSSI trilateration (pure math). Server handles: trajectory prediction (needs pattern analysis over large time spans), anomaly detection (needs cross-emitter correlation), natural language threat reports, texture extraction from images.

**Consequences**: Edge works fully offline for basic TSCM. Server adds intelligence but is not required for core operation. The edge AI engine is a simple decision tree: if task is in the "lightweight" list, run locally; otherwise, POST to server queue and return task_id for polling. Risk: CPU Ollama on 24B Q4_K_M is slow (~2-5 tokens/sec); edge AI should only handle prompts under 200 tokens output.
