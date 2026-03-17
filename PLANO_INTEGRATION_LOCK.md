# PlanO Integration Lock

Rules that must hold during continued development. Based on codebase as of 2026-03-11.

---

## 1. Official Upload Owner

plano-ui owns all file uploads. The single entry point is `PlannerFrame.tsx:loadProjectPicker()`.

- JSON files: parsed in plano-ui, sent to iframe via `LOAD_PROJECT_JSON`.
- Image/PDF files: posted to raster server at `RASTER_URL`, result sent to iframe via `LOAD_RASTER_JSON`.

The react-planner engine must never fetch from the raster server directly. `toolbar-load-button.tsx` is disabled (`condition: false` in `toolbar.tsx` line 108). Do not re-enable it.

---

## 2. Planner Boundary Rule

react-planner is a geometry engine only. It handles walls, holes, items, areas, vertices, 2D canvas, and 3D rendering.

**Must not exist inside `02_react_planner/react-planner/src/`:**
- Service names (painting, flooring, plastering, boards, electricity, plumbing)
- Sub-service lists or taxonomies
- Pricing, rates, quantities, or BOQ logic
- User authentication or authorization
- API calls to any backend

**Currently violates this rule (known debt):**
- `src/components/catalog-view/catalog-item.tsx` lines 132-170: `isPaintSelector()` hardcodes paint names and emits `CATALOG_SERVICE_SELECTED` with business fields.
- `demo/src/catalog_custom/mycatalog.ts` lines 10-60: `PLANO_MAIN_SERVICES` and `PLANO_SUBSERVICES` define PlanO domain taxonomy inside the engine.

These violations are acknowledged. Do not add more. New business logic goes in `00_frontend_skeleton/plano-ui/src/`.

---

## 3. Current Iframe Protocol v1

All messages carry `protocolVersion: 1`. Parent filters on origin. Iframe filters on protocolVersion.

### Parent to iframe

Envelope: `{ protocolVersion: 1, type: "CMD", cmd: string, payload?: object }`

| Command | Payload | Status |
|---|---|---|
| `NEW_PROJECT` | none | active |
| `OPEN_CATALOG` | none | active |
| `CHANGE_CATALOG_PAGE` | `{ newPage: string, oldPage?: string }` | active |
| `VIEW_2D` | none | active |
| `VIEW_3D` | none | active |
| `SELECT_TOOL_EDIT` | none | active |
| `UNDO` | none | active |
| `OPEN_PROJECT_CONFIGURATOR` | none | active |
| `LOAD_PROJECT_JSON` | `{ scene: object }` | active |
| `LOAD_RASTER_JSON` | `{ raw: object }` | active |
| `REQUEST_SCENE_JSON` | none | active |
| `VIEW_3D_FIRST_PERSON` | none | declared, never sent |
| `TOOL_PAN` | none | declared, never sent |
| `TOOL_ZOOM_IN` | none | declared, never sent |
| `TOOL_ZOOM_OUT` | none | declared, never sent |
| `UNSELECT_ALL` | none | declared, never sent |

Special: `{ protocolVersion: 1, type: "PING" }` sent on iframe load. Not a CMD.

### Iframe to parent

| Event | Payload | Emitter |
|---|---|---|
| `MODE_CHANGED` | `{ mode: string }` inside `payload` | `renderer.tsx` |
| `ERROR` | `message: string` at top level (not in payload) | `renderer.tsx` |
| `SCENE_JSON` | `{ scene: object }` inside `payload` | `renderer.tsx` |
| `SURFACE_SELECTED` | `{ surfaceId, wallId, surfaceType }` inside `payload` | `viewer3d.tsx` directly |
| `CATALOG_SERVICE_SELECTED` | `{ mainService, subService, materialKey, materialLabel, color }` inside `payload` | `catalog-item.tsx` directly |

**Protocol rules:**
- Do not bump protocolVersion without updating both sides simultaneously.
- SURFACE_SELECTED and CATALOG_SERVICE_SELECTED are emitted from engine source files, not renderer.tsx. They use hardcoded `protocolVersion: 1`, not the constant. Keep them in sync manually.
- ERROR is the only event with data at top level instead of inside payload. Do not change this without updating PlannerFrame.tsx line 144.

---

## 4. Current State Ownership Rule

### plano-ui owns (plannerState.tsx context):

| State | Persisted to localStorage | Lost on reload |
|---|---|---|
| `activeMain` | yes | no |
| `selected` (sub-service toggles per service) | yes | no |
| `selectedSurfaces` (working scratchpad) | no | yes |
| `areaServiceDraft` (4 Sets: painting, flooring, plastering, boards) | no | yes |
| `activeAreaSubService` | no | yes |
| `activeAreaMaterialKey` | no | yes |
| `activeAreaMaterialLabel` | no | yes |
| `activeAreaMaterialColor` | no | yes |

### Planner.tsx owns (local state, lost on navigation):

| State | Purpose |
|---|---|
| `viewMode` | "2D" or "3D", resets to "2D" |
| `engineMode` | raw mode string from iframe |

### react-planner iframe owns (Redux store, lost on iframe reload):

- Full scene graph (walls, holes, items, areas, vertices)
- Catalog state and current page
- 3D highlight state (`highlightedMeshes` Map in viewer3d.tsx)
- Viewer camera position and controls

**Ownership rule:** plano-ui never reads the iframe Redux store directly. It requests data via postMessage (`REQUEST_SCENE_JSON`). The iframe never reads plano-ui context. It receives commands via postMessage.

---

## 5. Rules for Future Area-Service Draft Ledger Work

The area-service draft ledger (`areaServiceDraft`) is the data structure that tracks which surfaces belong to which area service. The following rules must hold for any work that extends it.

**Rule 1: Four area services only.** The AreaService type is `"painting" | "flooring" | "plastering" | "boards"`. Object services (electricity, plumbing, other) use drag-and-drop items, not surface selection. Do not mix the two models.

**Rule 2: The ledger lives in plano-ui only.** Surface-to-service assignments are plano-ui business logic. They must not be stored inside the react-planner Redux store or in any file under `02_react_planner/`.

**Rule 3: Each surface entry must carry its material.** The current `areaServiceDraft` stores bare surface IDs (`Set<string>`). This is insufficient. When a surface is assigned to a service, the sub-service name, material key, material label, and color that were active at assignment time must be stored alongside the surface ID. Otherwise the system cannot distinguish two surfaces painted different colors under the same service.

**Rule 4: The ledger must be persisted.** Currently `areaServiceDraft`, `selectedSurfaces`, and all active-area fields are lost on reload. Any implementation must save the ledger to localStorage (same key or a new versioned key) and restore it on load.

**Rule 5: Re-highlighting requires a new protocol command.** When the user switches back to a service, plano-ui must tell the iframe which surfaces to highlight for that service. No such command exists today. The 3D highlight state is internal to `viewer3d.tsx` and cannot be driven from outside. A new postMessage command will be needed. It must be added to both PlannerFrame.tsx (sender) and renderer.tsx (handler). It must not put business logic inside the engine — the engine receives surface IDs and a color, it does not know what service they belong to.

**Rule 6: m2 must come from the engine.** Wall surface area (height times segment length) is computable only from the react-planner scene graph. When a surface is selected, the engine must include the area in m2 in the SURFACE_SELECTED event payload, or plano-ui must be able to request it. The current SURFACE_SELECTED payload does not include m2. This must be added to the protocol.

**Rule 7: handleCatalogServiceSelected must accept all four area services.** Currently Planner.tsx line 82 gates on `payload.mainService === "painting"` only. When catalog material items are added for flooring, plastering, and boards, this handler must accept those mainService values using the same pattern.
