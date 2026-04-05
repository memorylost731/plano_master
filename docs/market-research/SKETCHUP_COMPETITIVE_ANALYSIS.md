# SketchUp Competitive Analysis — PlanO Strategy

## 1. SketchUp Product Suite & Pricing

| Tier | Price | Target | Key Features |
|------|-------|--------|-------------|
| **Free (Schools)** | $0 | K-12 education | Web modeler, lessons, Chromebook support |
| **Go** | $119/yr ($10.75/mo) | Hobbyists, light design | Web + iPad, 3D Warehouse, cloud storage, sharing |
| **Pro** | $399/yr ($33.25/mo) | Professionals | Desktop app, LayOut (2D docs), 1000+ extensions, IFC/DWG |
| **Studio** | $819/yr ($68.25/mo) | Architects, studios | V-Ray rendering, Revit import, point cloud, 360° panoramas |

**Revenue model:** Subscription SaaS. No per-project or homeowner tier. Education subsidized.

---

## 2. SketchUp Feature Matrix

### Core 3D Modeling Tools
| Feature | SketchUp Has | PlanO Status | PlanO Advantage |
|---------|-------------|-------------|-----------------|
| Push/Pull (extrude faces) | Yes (signature tool) | Partial (react-planner 3D) | AI-assisted: detect walls → auto-extrude |
| Follow Me (sweep along path) | Yes | No | Lower priority — not renovation-critical |
| Offset (parallel edges) | Yes | No | Can implement in react-planner |
| Line/Arc/Rectangle/Circle | Yes | Yes (2D editor) | Equal |
| Eraser/Move/Rotate/Scale | Yes | Partial | Need full transform tools |
| Tape Measure/Dimensions | Yes | Partial (rulers) | Need smart dimensioning |
| Section Planes | Yes (Pro) | No | Important for renovation — show wall sections |
| Solid Tools (union/subtract) | Yes (Pro) | No | Boolean operations — Phase 2 |
| Dynamic Components | Yes (Pro) | No | Parametric objects — Phase 3 |

### Materials & Textures
| Feature | SketchUp | PlanO | Advantage |
|---------|----------|-------|-----------|
| Material library | Large (built-in) | Ogi's tile pipeline (paint, flooring, boards) | **PlanO**: region-specific materials |
| Texture positioning | Manual UV mapping | Auto from Rasta detection | **PlanO**: AI-detected materials |
| Photoreal materials | iPad only | GPU-rendered (Three.js) | **PlanO**: web-based, no app install |
| Custom textures | Upload image | Upload image | Equal |
| Material quantity takeoff | Via extensions | Built-in (BOQ/estimate) | **PlanO**: native cost estimation |

### Documentation & Output
| Feature | SketchUp | PlanO | Advantage |
|---------|----------|-------|-----------|
| 2D construction docs (LayOut) | Pro only ($399/yr) | Not yet | Must build — critical for contractors |
| DWG/DXF export | Pro only | Not yet | Need this for architect interop |
| PDF export | Yes | Planned | Tier-gated, watermark on free |
| 3D model export (OBJ/FBX/glTF) | Pro only | Not yet | Three.js can export glTF natively |
| BIM/IFC | Pro (basic), Studio (full) | Not yet | Phase 3 |
| Rendered images | V-Ray (Studio $819/yr) | Three.js renderer | **PlanO**: included in all tiers |
| 360° panorama | Studio only | Three.js + WebXR | **PlanO**: web-based, no plugin |
| AR view | iPad only | WebXR (any device) | **PlanO**: no app install needed |

### Collaboration
| Feature | SketchUp | PlanO | Advantage |
|---------|----------|-------|-----------|
| Cloud storage | Trimble Connect | Project DB (planned) | Equal |
| Real-time sharing | Comments on models | Shareable URLs (planned) | **PlanO**: viral loop ("Made with PlanO") |
| Team management | Yes (per-seat) | Agency tier (planned) | Equal |
| Version history | Trimble Connect | Git-like (planned) | **PlanO**: diff between versions |
| Client portal | No | Planned (Agency tier) | **PlanO**: client sees progress |

### What SketchUp Does NOT Have (PlanO Differentiators)
| Feature | Why It Matters | PlanO Implementation |
|---------|---------------|---------------------|
| **AI floor plan recognition** | Upload image → instant 3D model | Rasta (CubiCasa5k GPU engine) — LIVE |
| **Automated cost estimation** | Renovation budget from floor plan | BOQ engine with regional rates |
| **Renovation-specific workflow** | SketchUp is generic 3D, not renovation | Select building → choose services → estimate |
| **Contractor marketplace** | Connect homeowner to contractor | Referral system, contractor profiles |
| **Subsidy calculator** | EU renovation incentives | Per-country subsidy eligibility |
| **Material sourcing** | Link plan to real products with prices | Supplier partnerships (tile, paint, flooring) |
| **Permit-ready output** | Plans formatted for local building permits | Per-country permit templates |
| **Geo-located building selection** | Click building on map → start project | MapLibre 3D + OSM data — LIVE |
| **15 AI business agents** | Automated marketing, SEO, support | Ollama-powered, running on timers |
| **Self-hosted / sovereign** | No vendor lock-in, GDPR compliant | Docker + own infrastructure |

---

## 3. SketchUp Weaknesses (User Complaints)

Based on reviews (G2, Capterra, Reddit, forums):

### Top Pain Points
1. **Subscription fatigue** — Was once $495 perpetual, now $399/yr recurring. Users resent losing access if they stop paying.
2. **Web version is limited** — Free tier stripped down. Can't do real work without Pro.
3. **No native rendering** — Need V-Ray ($819/yr Studio) or external plugins for photorealism.
4. **Crashes on complex models** — Poor performance with detailed architectural models (>50K faces).
5. **No real parametric modeling** — Not truly BIM. Dynamic Components are awkward.
6. **LayOut is clunky** — Professionals find LayOut inferior to dedicated 2D documentation tools.
7. **Extension dependency** — Core product missing features, need to buy/find extensions for basic functionality.
8. **No AI capabilities** — Zero AI features. Manual everything.
9. **No cost estimation** — Pure geometry tool. No connection to real-world costs.
10. **Mobile (iPad) is expensive** — $119/yr minimum for iPad access.

### Opportunity Matrix
| SketchUp Pain Point | PlanO Solution | Difficulty |
|---------------------|---------------|------------|
| Subscription lock-in | Homeowner $4.99 one-time option | Easy |
| No rendering | Three.js real-time 3D included free | Done |
| No AI | Rasta AI floor plan detection | Done |
| No cost estimation | Built-in BOQ with regional rates | In progress |
| Extension dependency | Core features built-in | Architecture choice |
| No renovation focus | Purpose-built for renovation | Core product |
| No geo features | MapLibre building selection | Done |
| Crashes on complexity | WebGL + efficient scene graph | Architecture |
| No collaboration | Shareable URLs + client portal | Planned |

---

## 4. Implementation Roadmap — Feature Parity + Beyond

### Phase 1: MVP (Current Sprint — April 5-9)
- [x] 2D floor plan editor (react-planner)
- [x] 3D view with materials (Three.js)
- [x] AI floor plan detection (Rasta/CubiCasa5k)
- [x] Service selection (7 trades, 43 items)
- [x] Geo building selection (MapLibre 3D)
- [x] SaaS dashboard + pricing tiers
- [ ] User auth (Supabase)
- [ ] Stripe payments
- [ ] Project save to DB

### Phase 2: Core Pro Features (Month 2-3)
- [ ] Smart dimensioning (auto-measure walls, rooms)
- [ ] Material quantity takeoff (automatic from floor plan)
- [ ] PDF export (with tier-based watermark)
- [ ] DWG/DXF export (for architect interop)
- [ ] Push/Pull tool (extrude walls in 3D)
- [ ] Section plane views
- [ ] Undo/redo history
- [ ] Project templates (bathroom, kitchen, full apartment)

### Phase 3: Pro Differentiators (Month 4-6)
- [ ] Real-time collaboration (WebSocket)
- [ ] Client portal (shareable project URLs)
- [ ] Cost estimation engine (regional rates, material prices)
- [ ] Subsidy calculator (EU renovation incentives)
- [ ] Permit-ready output (per-country templates)
- [ ] AR/VR walkthrough (WebXR)
- [ ] Contractor marketplace integration
- [ ] IFC/BIM export

### Phase 4: Platform (Month 7-12)
- [ ] 3D model library (like 3D Warehouse but construction-focused)
- [ ] Plugin/extension API
- [ ] White-label for architectural firms
- [ ] Multi-language (27 EU languages)
- [ ] Native mobile app (React Native)
- [ ] Offline mode
- [ ] AI design suggestions ("your bathroom is too small for this layout")
- [ ] Photorealistic rendering (Three.js post-processing)

---

## 5. Competitive Positioning

```
                    ┌─────────────────────────────────────────┐
                    │           HIGH CAPABILITY                │
                    │                                         │
    GENERAL ◄───────┤  SketchUp Pro    Revit    ArchiCAD     │
    PURPOSE         │     $399/yr     $3000/yr   $4000/yr    │
                    │                                         │
                    │  SketchUp Free   Floorplanner           │
                    │     $0            $5/plan              │
                    │                                         │
                    ├─────────────────────────────────────────┤
                    │                                         │
    RENOVATION ◄────┤  MagicPlan     RoomSketcher             │
    FOCUSED         │   $10/mo        $49/mo                 │
                    │                                         │
                    │  ┌──────────────────────────┐          │
                    │  │  PlanO                    │          │
                    │  │  $9-49/mo + $4.99/plan   │          │
                    │  │  AI + Cost + Geo + SaaS  │          │
                    │  └──────────────────────────┘          │
                    │                                         │
                    │           LOW CAPABILITY                │
                    └─────────────────────────────────────────┘
```

**PlanO's niche:** Renovation-focused, AI-powered, contractor-oriented. Not competing with SketchUp on general 3D modeling — competing on the renovation workflow where SketchUp is weakest.

---

## 6. "Do Better" Strategy

| SketchUp Feature | How PlanO Does It Better |
|-----------------|-------------------------|
| Manual 3D modeling from scratch | **Upload photo → AI generates 3D model in seconds** |
| Generic material library | **Region-specific materials with real prices from local suppliers** |
| No cost awareness | **Every element has a cost. Total visible in real-time.** |
| Desktop app required for pro features | **100% web-based. Works on any device.** |
| $819/yr for rendering | **Real-time 3D rendering included free** |
| No renovation workflow | **Built for renovation: select building → detect plan → choose services → estimate → hire contractor** |
| No location awareness | **3D map with every building. Click to start.** |
| No AI at all | **AI floor plan detection, AI cost estimation, AI design suggestions, 15 AI agents** |
| $399/yr minimum for professionals | **$19/mo Pro ($228/yr saves $171 vs SketchUp Pro)** |
| No subsidy integration | **"You qualify for €15,000 in MaPrimeRénov" shown automatically** |
