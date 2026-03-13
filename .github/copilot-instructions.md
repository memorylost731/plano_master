# PlanO - Construction Marketplace Platform

## Project Overview

PlanO is a construction services marketplace focused on Malta and Gozo (19 cities). The platform connects property owners with construction professionals through an interactive floor plan editor and geospatial city selector.

**Company**: Strada Forge Holdings Limited (Malta)

## Architecture

### Frontend
- **Framework**: React + Vite
- **Styling**: Tailwind CSS
- **Maps**: MapLibre GL JS (OSM 3D buildings, GeoJSON city boundaries)
- **Floor Plans**: react-planner integration via iframe + postMessage bridge
- **City Selector**: GeoSelect 3D component — Malta + Gozo coverage with 19 city polygons

### Backend
- **API**: FastAPI (Python 3.10)
- **Engine**: Rasta — open-source floor plan processing + texture pipeline
- **Server**: GPU server (hadrien-skoed-mt) behind Caddy reverse proxy
- **Database**: PostgreSQL

### TSCM Overlay
- Counter-surveillance 4D overlay layer integrated into the MapLibre map view
- Separate from core marketplace functionality

## Key Components

### City Selector (`GeoSelect`)
- MapLibre GL JS map centered on Malta
- GeoJSON boundaries for 19 cities across Malta and Gozo
- 3D building extrusions from OSM data
- Click-to-select city flow leading into service area definition

### react-planner Integration
- Embedded via iframe with postMessage API
- PlanO toolbar replaces original react-planner toolbar
- Catalog selection bridge: PlanO UI triggers catalog, planner returns selection
- Face selection bridge for 3D wall/surface operations

### Rasta Backend
- Floor plan raster-to-vector engine
- Texture pipeline for material rendering
- Wall dimension extraction from uploaded plans
- REST API endpoints consumed by the frontend

## Development

```bash
# Frontend
cd frontend && npm install && npm run dev

# Backend
cd backend && pip install -r requirements.txt && uvicorn main:app --reload
```

## Deployment

- Caddy serves the frontend and proxies API requests to FastAPI
- GPU server handles Rasta processing and model inference
- Production domain: plano-pro.com

## Conventions
- Commit messages: conventional commits (feat/fix/chore/refactor)
- Branch strategy: `plano-mt` is the active development branch
- No force pushes to main or plano-mt
