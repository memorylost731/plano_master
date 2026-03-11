# PlanO Development Guide

## Environment Setup

### System Dependencies

**Ubuntu 24.04 / Debian:**
```bash
# Build tools
sudo apt install build-essential pkg-config

# Node canvas native deps (required by react-planner)
sudo apt install libcairo2-dev libpango1.0-dev libjpeg-turbo8-dev libgif-dev librsvg2-dev

# Python 3.10 (if not available in default repos)
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.10 python3.10-venv python3.10-dev
```

**Fedora 43+:**
```bash
# Build tools
sudo dnf install gcc gcc-c++ make cmake

# Node canvas native deps
sudo dnf install cairo-devel pango-devel libjpeg-turbo-devel giflib-devel librsvg2-devel

# Python 3.10
sudo dnf install python3.10 python3.10-devel
```

### Node.js (via nvm)

```bash
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20
nvm alias default 20
```

### Full Project Setup

```bash
git clone git@github.com:memorylost731/plano_master.git
cd plano_master

# Frontend
cd 00_frontend_skeleton/plano-ui && npm ci && cd ../..

# React-Planner
cd 02_react_planner/react-planner && npm ci && cd ../..

# Raster backend
cd 01_raster
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your RasterScan API key
cd ..
```

## Running in Development

You need three terminals (or use tmux):

### Terminal 1: Raster Backend

```bash
cd ~/plano_master/01_raster
source .venv/bin/activate
uvicorn server.app:app --host 127.0.0.1 --port 8010 --reload
```

The `--reload` flag enables auto-restart on Python file changes.

**Health check:**
```bash
curl http://127.0.0.1:8010/docs
# Should return the FastAPI Swagger UI
```

### Terminal 2: React-Planner Engine

```bash
cd ~/plano_master/02_react_planner/react-planner
npm start
```

Starts Webpack dev server on port 5173 with hot module replacement.

**Health check:**
Open http://localhost:5173 — should show the react-planner UI directly.

### Terminal 3: PlanO Frontend

```bash
cd ~/plano_master/00_frontend_skeleton/plano-ui
npm run dev -- --port 5174
```

Starts Vite dev server on port 5174 with HMR.

**Health check:**
Open http://localhost:5174 — should show the PlanO landing page.

### tmux One-liner

```bash
cd ~/plano_master && \
tmux new-session -d -s plano \
  'cd 01_raster && source .venv/bin/activate && uvicorn server.app:app --host 127.0.0.1 --port 8010 --reload' \; \
  split-window -h 'cd 02_react_planner/react-planner && npm start' \; \
  split-window -v 'cd 00_frontend_skeleton/plano-ui && npm run dev -- --port 5174' \; \
  attach
```

### Checking All Ports

```bash
ss -ltnp | grep -E ':(5173|5174|8010)\b'
```

## Project Structure Deep Dive

### Frontend (`00_frontend_skeleton/plano-ui/src/`)

```
src/
├── main.tsx                          # Entry point, PlannerStateProvider wrapper
├── App.tsx                           # BrowserRouter, all route definitions
├── App.css                           # Global styles
├── index.css                         # Tailwind imports
├── app/
│   └── ClientLayout.tsx              # Shared header + footer navigation
├── components/
│   └── planner/
│       └── PlannerFrame.tsx          # iframe bridge to react-planner
│                                     # Handles: postMessage, file upload,
│                                     # download, scene load/save
├── pages/client/
│   ├── GeoSelect.tsx                 # Step 1: Location + service type
│   ├── Planner.tsx                   # Step 2: Main planner view (2D/3D)
│   ├── Planner2D.tsx                 # Legacy 2D-only view
│   ├── Planner3D.tsx                 # Legacy 3D-only view
│   ├── Estimate.tsx                  # Step 3: Bill of Quantities
│   ├── Payment.tsx                   # Step 4: Stripe checkout (stub)
│   └── Confirmation.tsx              # Step 5: Post-payment (stub)
└── state/
    └── plannerState.tsx              # React Context for service selections
                                      # Persists to localStorage
```

### Raster Backend (`01_raster/`)

```
01_raster/
├── server/
│   └── app.py                        # FastAPI application
│                                     # POST /upload-plan endpoint
│                                     # CORS middleware config
│                                     # Subprocess orchestration
├── send_to_rasterscan.py             # RasterScan API client
│                                     # Exponential backoff retry
│                                     # 180s timeout per request
├── rasterscan_to_reactplanner.py     # RasterScan → react-planner converter
│                                     # SHA1-based stable IDs
│                                     # Point snapping/dedup
│                                     # Wall, room, door processing
├── convert_raster_to_scene.py        # Template-based converter (legacy)
├── rs_to_planner.py                  # Deprecated stub
├── templates/
│   └── react_planner_template.json   # Canonical scene structure
├── out/                              # Converter output (gitignored)
├── uploads/                          # Upload staging (gitignored)
├── logs/                             # Server logs (gitignored)
├── .env                              # API credentials (gitignored)
├── .env.example                      # .env template
└── requirements.txt                  # Python dependencies
```

### React-Planner (`02_react_planner/react-planner/src/`)

```
src/
├── index.ts                          # Public API exports
├── react-planner.tsx                 # Main React component
├── react-planner-context.tsx         # React context provider
├── models.ts                         # Redux state shape
├── types.ts                          # TypeScript interfaces
├── constants.ts                      # Enums, defaults
├── actions/                          # Redux action creators
│   ├── project-actions.ts            # New/load/save project
│   ├── scene-actions.ts              # Scene manipulation
│   ├── lines-actions.ts              # Wall operations
│   ├── area-actions.ts               # Room operations
│   ├── holes-actions.ts              # Door/window operations
│   ├── items-actions.ts              # Furniture operations
│   ├── vertices-actions.ts           # Point operations
│   ├── viewer2d-actions.ts           # 2D camera pan/zoom
│   └── viewer3d-actions.ts           # 3D camera control
├── reducers/                         # Redux reducers (mirror actions)
├── class/                            # Domain model classes
│   ├── vertex.ts, line.ts, area.ts   # Geometric primitives
│   ├── hole.ts, item.ts              # Architectural elements
│   ├── layer.ts, project.ts          # Scene structure
│   └── group.ts, guide.ts           # Grouping and guides
├── catalog/                          # Element catalog system
│   ├── catalog.ts                    # Registry
│   ├── factories/                    # 2D/3D rendering factories
│   │   ├── wall-factory.tsx          # 2D wall renderer
│   │   ├── wall-factory-3d.ts        # 3D wall mesh (Three.js)
│   │   ├── area-factory.tsx          # 2D floor renderer
│   │   └── area-factory-3d.ts        # 3D floor mesh
│   └── properties/                   # Property editor components
├── components/                       # React UI components
│   ├── viewer-2d/                    # 2D SVG canvas
│   ├── viewer-3d/                    # 3D Three.js viewport
│   ├── sidebar/                      # Property editors
│   ├── catalog-view/                 # Element browser
│   └── footerbar/                    # Bottom toolbar
├── plugins/                          # Extension system
├── translator/                       # Internationalization
└── utils/                            # Utilities
```

## Common Development Tasks

### Adding a New Page/Route

1. Create component in `00_frontend_skeleton/plano-ui/src/pages/client/`
2. Add route in `App.tsx`
3. Add navigation link in `ClientLayout.tsx` if needed

### Adding a New Service Category

Edit `00_frontend_skeleton/plano-ui/src/state/plannerState.tsx`:
1. Add category to the `ServiceCategory` type
2. Add sub-services array
3. Add to the initial state map

### Adding Furniture to the Planner Catalog

See `02_react_planner/react-planner/docs/HOW_TO_CREATE_AN_ELEMENT.md`

1. Create element directory under `demo/src/catalog/items/`
2. Define `planner-element.tsx` with 2D/3D render functions
3. Register in `demo/src/catalog/mycatalog.ts`

### Modifying the Raster Pipeline

The conversion pipeline has two converters:
- `rasterscan_to_reactplanner.py` — **preferred**, robust with snapping
- `convert_raster_to_scene.py` — legacy template-based

To modify wall/room processing, edit `rasterscan_to_reactplanner.py`.

### Testing the Upload Pipeline Manually

```bash
# Direct RasterScan API test
cd 01_raster && source .venv/bin/activate
python send_to_rasterscan.py /path/to/floorplan.png out/rasterscan_raw.json

# Convert to react-planner format
python rasterscan_to_reactplanner.py out/rasterscan_raw.json out/scene.react.json

# Or test via the FastAPI endpoint
curl -X POST http://localhost:8010/upload-plan \
  -F "file=@/path/to/floorplan.png"
```

## Troubleshooting

### "RASTERSCAN_API_KEY is not set in environment"

The `.env` file is not being loaded. Ensure:
1. `01_raster/.env` exists with a valid key
2. `python-dotenv` is installed (`pip install python-dotenv`)
3. The `load_dotenv()` call is in `server/app.py` (fixed in commit 0c3aa76)

### React-Planner iframe shows blank

1. Check that port 5173 is running: `ss -ltnp | grep 5173`
2. Check browser console for CORS or postMessage errors
3. Ensure react-planner webpack-dev-server started successfully

### Upload fails with 500 error

1. Check raster backend logs in the terminal running uvicorn
2. Verify RasterScan API key is valid: `curl -X POST $RASTERSCAN_ENDPOINT -H "x-api-key: $RASTERSCAN_API_KEY" -F "image=@test.png"`
3. Check that `send_to_rasterscan.py` and `rasterscan_to_reactplanner.py` are executable

### npm ci fails on react-planner

Usually missing native deps for node-canvas. Install:
```bash
# Ubuntu
sudo apt install libcairo2-dev libpango1.0-dev libjpeg-turbo8-dev libgif-dev librsvg2-dev

# Fedora
sudo dnf install cairo-devel pango-devel libjpeg-turbo-devel giflib-devel librsvg2-devel
```

### Node version issues

The project requires Node.js >= 20. Use nvm:
```bash
nvm install 20 && nvm use 20
```
