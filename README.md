# PlanO — Architectural Planning & Estimation Platform

PlanO is a full-stack web application for architectural floor plan editing, AI-powered plan recognition, and renovation cost estimation. Users upload floor plans (images or PDFs), get automatic wall and room detection via machine learning, edit in a 2D/3D CAD environment, select renovation services, and receive cost estimates.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│           PlanO Frontend (React 19 + Vite)          │
│                  localhost:5174                      │
│   Landing → GeoSelect → Planner → Estimate → Pay   │
└────────────────────┬────────────────────────────────┘
                     │ iframe + postMessage (protocol v1)
┌────────────────────▼────────────────────────────────┐
│       React-Planner Engine (Webpack + Three.js)     │
│                  localhost:5173                      │
│    2D SVG editor · 3D WebGL viewer · Redux state    │
│    Catalog: walls, doors, windows, 50+ furniture    │
└────────────────────┬────────────────────────────────┘
                     │ HTTP POST /upload-plan
┌────────────────────▼────────────────────────────────┐
│         Raster Backend (FastAPI + Python 3.10)      │
│                  localhost:8010                      │
│    Upload → RasterScan API → JSON converter         │
└────────────────────┬────────────────────────────────┘
                     │ HTTPS (x-api-key)
┌────────────────────▼────────────────────────────────┐
│          RasterScan API (external ML service)       │
│          backend.rasterscan.com                     │
│    Image/PDF → walls, rooms, doors, windows         │
└─────────────────────────────────────────────────────┘
```

## Directory Structure

```
plano_master/
├── 00_frontend_skeleton/plano-ui/   # PlanO SPA (React 19, Vite, Tailwind)
├── 01_raster/                       # Python raster backend (FastAPI)
│   ├── server/app.py                # FastAPI server (:8010)
│   ├── send_to_rasterscan.py        # RasterScan API client
│   ├── rasterscan_to_reactplanner.py # JSON scene converter
│   ├── convert_raster_to_scene.py   # Template-based converter (legacy)
│   ├── templates/                   # React-Planner scene templates
│   ├── .env                         # API credentials (not committed)
│   ├── .env.example                 # Template for .env
│   └── requirements.txt             # Python dependencies
├── 02_react_planner/react-planner/  # Forked @archef2000/react-planner v2.0.15
├── 03_invoice/                      # Invoice module (planned)
├── 04_stripe/                       # Stripe payments (planned)
├── .gitignore
└── README.md
```

## Quick Start

### Prerequisites

- **Node.js** >= 20 (recommended: install via [nvm](https://github.com/nvm-sh/nvm))
- **Python** 3.10+ (3.10 recommended for compatibility)
- **System libraries** (for node-canvas, used by react-planner):
  - Ubuntu/Debian: `sudo apt install libcairo2-dev libpango1.0-dev libjpeg-turbo8-dev libgif-dev librsvg2-dev pkg-config build-essential`
  - Fedora: `sudo dnf install cairo-devel pango-devel libjpeg-turbo-devel giflib-devel librsvg2-devel`
- **RasterScan API key** (from [rasterscan.com](https://rasterscan.com))

### Setup

```bash
# 1. Clone
git clone git@github.com:memorylost731/plano_master.git
cd plano_master

# 2. Frontend
cd 00_frontend_skeleton/plano-ui
npm ci
cd ../..

# 3. React-Planner engine
cd 02_react_planner/react-planner
npm ci
cd ../..

# 4. Raster backend
cd 01_raster
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 5. Environment
cp .env.example .env
# Edit .env and add your RASTERSCAN_API_KEY
```

### Running (three terminals)

```bash
# Terminal 1 — Raster Backend (port 8010)
cd 01_raster && source .venv/bin/activate
uvicorn server.app:app --host 127.0.0.1 --port 8010

# Terminal 2 — React-Planner Engine (port 5173)
cd 02_react_planner/react-planner
npm start

# Terminal 3 — PlanO Frontend (port 5174)
cd 00_frontend_skeleton/plano-ui
npm run dev -- --port 5174
```

Open **http://localhost:5174** in your browser.

### One-liner (with tmux)

```bash
cd ~/plano_master && \
tmux new-session -d -s plano \
  'cd 01_raster && source .venv/bin/activate && uvicorn server.app:app --host 127.0.0.1 --port 8010' \; \
  split-window -h 'cd 02_react_planner/react-planner && npm start' \; \
  split-window -v 'cd 00_frontend_skeleton/plano-ui && npm run dev -- --port 5174' \; \
  attach
```

## Ports

| Service              | Port | Protocol |
|----------------------|------|----------|
| PlanO Frontend       | 5174 | HTTP     |
| React-Planner Engine | 5173 | HTTP     |
| Raster Backend       | 8010 | HTTP     |
| RasterScan API       | 443  | HTTPS    |

## User Flow

1. **Landing** — Select country, city, and service type (refurbishing / new build / individual)
2. **Planner** — 2D/3D floor plan editor with service selection sidebar
   - Draw walls, rooms, doors, windows manually
   - Or **upload** an image/PDF floor plan for AI-powered recognition
   - Toggle 2D and 3D views
   - Select renovation services per room (electricity, plumbing, painting, flooring, plastering, boards)
3. **Estimate** — Bill of Quantities with cost breakdown
4. **Payment** — Stripe checkout (planned)
5. **Confirmation** — Receipt and project summary (planned)

## Tech Stack

| Layer            | Technology                          | Version  |
|------------------|-------------------------------------|----------|
| Frontend UI      | React + TypeScript                  | 19.2.0   |
| Build (Frontend) | Vite                                | 7.2.4    |
| Styling          | Tailwind CSS                        | 4.1.18   |
| Routing          | React Router DOM                    | 7.11.0   |
| State            | React Context + localStorage        | built-in |
| Planner Engine   | @archef2000/react-planner (forked)  | 2.0.15   |
| 3D Graphics      | Three.js                            | 0.179.0  |
| Planner State    | Redux + Redux Toolkit               | 5.0.1    |
| Build (Planner)  | Webpack                             | 5.101.1  |
| Backend          | FastAPI + Python                    | 0.135.1  |
| ML Recognition   | RasterScan API (external)           | SaaS     |

## Implementation Status

| Module               | Status      | Notes                                |
|----------------------|-------------|--------------------------------------|
| GeoSelect            | Complete    | Country/city/service selection       |
| Planner (2D/3D)      | Complete    | Unified view with service sidebar    |
| PlannerFrame bridge  | Complete    | postMessage protocol v1              |
| React-Planner engine | Complete    | Full 2D/3D editing + catalog         |
| Raster upload        | Complete    | Image/PDF to AI recognition to scene |
| Estimate UI          | Partial     | BOQ mockup, no backend calculation   |
| Payment (Stripe)     | Planned     | 04_stripe directory exists           |
| Invoice generation   | Planned     | 03_invoice directory exists          |
| User authentication  | Planned     | Stub routes only                     |
| Admin dashboards     | Planned     | Stub routes only                     |
| Database persistence | Planned     | Currently localStorage only          |

## Git Workflow

- **main** — stable baseline
- **integrate/planner-iframe-overlay** — active development branch
- Tags: `plano-react-planner-aliases-v1` — first working planner integration

## License

See individual module licenses. React-Planner is MIT licensed.
