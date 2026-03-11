# PlanO Architecture Guide

## System Overview

PlanO is a three-service microservices application. Each service runs independently and communicates over HTTP or browser postMessage.

```
                    ┌─────────────┐
                    │   Browser   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            │
     ┌────────────┐  ┌──────────┐      │
     │  PlanO UI  │  │ Planner  │      │
     │   :5174    │◄─┤  :5173   │      │
     │  (parent)  │  │ (iframe) │      │
     └─────┬──────┘  └──────────┘      │
           │                            │
           │  POST /upload-plan         │
           ▼                            │
     ┌──────────┐                       │
     │  Raster  │                       │
     │  :8010   │                       │
     └────┬─────┘                       │
          │                             │
          │  HTTPS                      │
          ▼                             │
     ┌──────────┐                       │
     │RasterScan│                       │
     │  (SaaS)  │                       │
     └──────────┘                       │
```

## Service Details

### 1. PlanO Frontend (`00_frontend_skeleton/plano-ui/`)

**Role**: Client-facing SPA. Renders all UI, manages user flow, embeds the planner engine via iframe.

**Tech**: React 19, TypeScript, Vite, Tailwind CSS, React Router DOM

**Key Responsibilities**:
- Route management (landing, geo-select, planner, estimate, payment, confirmation)
- Service selection state (7 categories, ~30 sub-services each)
- iframe lifecycle management (load, communicate, teardown)
- File upload orchestration (user picks file, frontend sends to raster backend)
- State persistence (localStorage under key `plano:plannerSelections:v1`)

**Entry Points**:
- `src/main.tsx` — React root, wraps App in PlannerStateProvider
- `src/App.tsx` — BrowserRouter, route definitions

**State Management**:
- `src/state/plannerState.tsx` — React Context providing:
  - `selections: Map<ServiceCategory, Set<string>>` — which sub-services are active
  - `toggleSelection(category, subService)` — add/remove
  - `clearSelections()` — reset all
  - Auto-persists to localStorage on every change

**Service Categories** (defined in plannerState.tsx):
1. Electricity (wiring, sockets, lighting, panels, etc.)
2. Plumbing (pipes, fixtures, drainage, water heater, etc.)
3. Painting (interior walls, ceilings, exterior, trim, etc.)
4. Flooring (tiles, hardwood, laminate, vinyl, carpet, etc.)
5. Plastering (skim coat, rough cast, decorative, repair, etc.)
6. Boards (plasterboard, cement board, insulation, etc.)
7. Other (demolition, waste removal, scaffolding, etc.)

### 2. React-Planner Engine (`02_react_planner/react-planner/`)

**Role**: Standalone 2D/3D CAD editor for floor plans. Runs in an iframe.

**Tech**: React 18, Three.js, Redux, Webpack, Babel, TypeScript

**Key Responsibilities**:
- 2D SVG floor plan editing (walls, rooms, doors, windows, furniture)
- 3D WebGL visualization (Three.js, first-person walkthrough)
- Catalog system (extensible element registry)
- Scene state management (Redux with undo/redo)
- postMessage API for parent window communication

**Catalog System**:
- Elements are registered in catalog files under `demo/src/catalog/`
- Types: `lines` (walls), `holes` (doors/windows), `items` (furniture), `areas` (rooms)
- Each element has: 2D render, 3D render, properties panel, info metadata
- See `docs/HOW_TO_CREATE_AN_ELEMENT.md` for extending

**Scene JSON Format**:
```json
{
  "unit": "cm",
  "layers": {
    "layer-1": {
      "vertices": { "<id>": { "x": 100, "y": 200, "lines": [...] } },
      "lines":    { "<id>": { "type": "wall", "vertices": ["v1","v2"], "properties": {...} } },
      "areas":    { "<id>": { "type": "area", "vertices": ["v1","v2","v3"] } },
      "holes":    { "<id>": { "type": "door", "line": "l1", "offset": 0.5 } },
      "items":    { "<id>": { "type": "sofa", "x": 300, "y": 400, "rotation": 0 } }
    }
  },
  "grids": { "h1": {...}, "v1": {...} },
  "width": 3000,
  "height": 2000
}
```

**postMessage Protocol v1**:

Parent (PlanO) to Planner:
```javascript
// Load a scene
planner.postMessage({ type: 'CMD', cmd: 'LOAD_SCENE', payload: sceneJSON }, '*')

// Request current scene
planner.postMessage({ type: 'CMD', cmd: 'GET_SCENE' }, '*')

// New empty project
planner.postMessage({ type: 'CMD', cmd: 'NEW_PROJECT' }, '*')

// Load raster-converted scene
planner.postMessage({ type: 'CMD', cmd: 'LOAD_RASTER_JSON', payload: sceneJSON }, '*')
```

Planner to Parent:
```javascript
// Scene data response
parent.postMessage({ type: 'SCENE_JSON', payload: sceneJSON }, '*')
```

### 3. Raster Backend (`01_raster/`)

**Role**: Python microservice that converts uploaded floor plan images/PDFs into editable scene JSON.

**Tech**: FastAPI, Python 3.10, requests, python-dotenv

**Key Responsibilities**:
- Accept file uploads (images: PNG/JPG/BMP, documents: PDF)
- Forward to RasterScan ML API for wall/room detection
- Convert RasterScan response to react-planner scene JSON format
- Return scene JSON to frontend

**Pipeline**:
```
POST /upload-plan (multipart file)
  │
  ├── Save file to uploads/
  │
  ├── subprocess: send_to_rasterscan.py <file> <out/rasterscan_raw.json>
  │     └── HTTP POST to backend.rasterscan.com
  │         Headers: x-api-key: $RASTERSCAN_API_KEY
  │         Body: multipart image=@file
  │         Retry: exponential backoff (2^n seconds, max 5 attempts)
  │         Timeout: 180 seconds per request
  │         Retryable: 408, 429, 500-504
  │
  ├── subprocess: rasterscan_to_reactplanner.py <raw.json> <scene.json>
  │     └── Converts:
  │           walls → vertices + lines (with snapping/dedup)
  │           rooms → areas (polygon vertices)
  │           IDs: SHA1 hash-based (stable, deterministic)
  │           Properties: height=300cm, thickness=20cm, texture=bricks
  │
  └── Return scene.json as JSONResponse
```

**CORS Configuration** (in app.py):
- Allowed origins: `localhost:5173`, `localhost:5174`, `localhost:5175`
- All methods and headers allowed

**Environment Variables** (loaded from `.env` via python-dotenv):
- `RASTERSCAN_API_KEY` — Required. API key for RasterScan service.
- `RASTERSCAN_ENDPOINT` — Required. URL of the RasterScan API endpoint.

## Data Flow: Upload Floor Plan

This is the most complex flow in the application:

```
1. User clicks "Load project" in PlanO UI
2. PlannerFrame.tsx shows file picker (image/PDF)
3. Frontend POSTs file to localhost:8010/upload-plan
4. FastAPI saves file, spawns send_to_rasterscan.py subprocess
5. send_to_rasterscan.py POSTs to RasterScan API (with retry)
6. RasterScan returns JSON: { walls: [...], rooms: [...], doors: [...] }
7. FastAPI spawns rasterscan_to_reactplanner.py subprocess
8. Converter transforms to react-planner scene format
9. FastAPI returns scene JSON to frontend
10. PlannerFrame.tsx sends LOAD_RASTER_JSON postMessage to iframe
11. React-Planner renders the scene in 2D/3D
```

## Data Flow: Manual Editing

```
1. User draws/edits in the react-planner iframe (2D or 3D view)
2. Redux state updates (vertices, lines, areas, items, holes)
3. User clicks "Save" in PlanO toolbar
4. PlannerFrame.tsx sends GET_SCENE postMessage
5. React-Planner responds with SCENE_JSON
6. PlannerFrame.tsx offers download as .json file
```

## State Persistence

Currently the application uses **localStorage only** — no database:

| Data                 | Storage Key                     | Scope      |
|----------------------|---------------------------------|------------|
| Service selections   | `plano:plannerSelections:v1`    | Per-browser |
| Scene JSON           | Exported as file download       | Manual     |

## Security Considerations

- The RasterScan API key is stored in `01_raster/.env` (gitignored)
- CORS is restricted to localhost development ports
- No authentication system exists yet — all routes are public
- No HTTPS in development (all localhost HTTP)
- The `.env` file must never be committed to git

## Deployment Considerations (Future)

For production deployment, the following changes are needed:

1. **Reverse proxy** (nginx/caddy) in front of all three services
2. **HTTPS** with proper certificates
3. **Environment-based CORS** (not hardcoded localhost)
4. **Database** for project persistence (PostgreSQL recommended)
5. **Authentication** (OAuth2 or session-based)
6. **Container packaging** (Docker Compose for all services)
7. **Rate limiting** on the upload endpoint
8. **File validation** (size limits, type checking) on upload
