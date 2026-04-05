# SketchUp Competitive Intelligence -- Full Feature Analysis

**Date:** 2026-04-05
**Purpose:** Feature-by-feature breakdown for PlanO competitive positioning

---

## 1. Pricing Tiers (as of July 2025)

| Tier | Price | Platform | Target |
|------|-------|----------|--------|
| **Free** | $0 | Web only | Hobbyists, students |
| **Go** | $129/yr ($19.99/mo) | Web + iPad | Mobile designers, field pros |
| **Pro** | $399/yr ($33.25/mo) | Desktop + Web + iPad | Architects, contractors |
| **Studio** | $819/yr ($68.25/mo annual only) | Windows desktop only | Firms needing rendering + BIM |
| **Education** | $55/yr | Desktop + Web + iPad | Students/educators (US/CA) |

**PlanO angle:** Their cheapest useful tier is $129/yr. PlanO targets the renovation/contractor niche that SketchUp ignores -- we can undercut at $9-29/mo with AI doing the heavy lifting.

---

## 2. Feature Breakdown by Tier

### 2.1 SketchUp Free (Web)

| Feature | Detail |
|---------|--------|
| 3D Modeler | Browser-based, no install |
| Drawing tools | Line, Rectangle, Circle, Arc, Push/Pull, Move, Rotate, Scale, Offset, Eraser |
| Push/Pull | Extrude faces into 3D -- signature tool |
| Components | Create and reuse, basic only |
| Materials | Apply textures/colors to surfaces |
| 3D Warehouse | Browse and download models (millions available) |
| Measurement | Tape Measure, Dimensions |
| Sections | Section planes to cut through model |
| Import | SKP, PNG, JPG only |
| Export | SKP, PNG, STL only |
| Storage | 10GB Trimble Connect |
| Commercial use | NOT allowed |

**Weaknesses:** No DWG/DXF export (useless for contractors), no LayOut, no extensions, no offline, no Follow Me tool, no Dynamic Components, very limited export. Essentially a demo.

**PlanO exploit:** Free tier that actually exports useful formats (PDF floor plans, DXF). SketchUp Free is a glorified toy.

### 2.2 SketchUp Go (Web + iPad)

Everything in Free, plus:

| Feature | Detail |
|---------|--------|
| iPad app | Native modeling on tablet |
| AR Viewing | View models in augmented reality (iPad) |
| Photoreal Materials | PBR materials on iPad |
| Follow Me | Extrude face along a path |
| Solid Tools | Union, Subtract, Intersect, Trim, Split |
| Tags/Layers | Organize model elements |
| Advanced camera | Scenes, section planes, animations |
| Import | + DWG, DXF, DAE, KMZ, 3DS, DEM, STL |
| Export | + DWG, DXF, DAE, KMZ, 3DS, FBX, XSI, OBJ, VRML |
| Storage | Unlimited Trimble Connect |
| Collaboration | Private links, real-time commenting |
| AI tools | AI Render + AI Assistant (credit-based) |

**Weaknesses:** No desktop app, no LayOut (no construction documents), no extensions, no Dynamic Components. iPad-only for mobile. No offline web.

**PlanO exploit:** We run on any browser + PWA offline. Their Go tier at $129/yr still can't produce construction documents.

### 2.3 SketchUp Pro (Desktop)

Everything in Go, plus:

| Feature | Detail |
|---------|--------|
| Desktop modeler | Native Windows/Mac app, full performance |
| LayOut | 2D documentation: dimensions, annotations, title blocks, multi-page sheets |
| LayOut drafting | Extend, Trim, Fillet, Chamfer tools |
| Style Builder | Create custom rendering styles |
| PreDesign | Climate/site analysis for early design decisions |
| Dynamic Components | Parametric objects with configurable attributes |
| Live Components | 200+ configurable objects from 3D Warehouse |
| Extensions | Access to 1000+ plugins (Extension Warehouse) |
| Scenes & Animations | Walkthrough animations, scene transitions |
| Sandbox Tools | Terrain modeling, grading |
| IFC support | BIM interoperability (import/export) |
| Enhanced DWG | Full CAD compatibility |
| Geolocation | Import terrain and imagery from Google Earth |
| Import additions | + DDF, IFC, IFCZIP, BMP, PSD, TIF, TGA, PDF (Mac) |
| Export additions | + IFC, WRL, TIF, EPS, PDF (Mac) |
| Classifier | Assign IFC types for BIM |
| Generate Report | Extract component data to CSV/HTML |
| Ruby API | Full scripting/automation |

**Weaknesses:** LayOut is clunky (universally complained about). Extensions are required for basic tasks (beveling, UV mapping, architectural walls). No built-in rendering. Performance degrades on complex models. No real-time collaboration on desktop.

**PlanO exploit:** Our AI generates construction documents automatically from the floor plan. No need for a separate "LayOut" workflow. Rasta AI replaces their entire extension ecosystem.

### 2.4 SketchUp Studio (Windows Only)

Everything in Pro, plus:

| Feature | Detail |
|---------|--------|
| V-Ray by Chaos | Photorealistic rendering engine |
| V-Ray animations | Rendered walkthroughs and fly-throughs |
| V-Ray 360 panoramas | Immersive client presentations |
| Scan Essentials | Import and model from point cloud data (LAS/LAZ/E57/PLY) |
| Revit Importer | Import .rvt files directly |
| Sefaira | Energy analysis (being phased out) |
| Import additions | + RVT, RWP, LAS, LAZ, TZF, PLY, E57 |

**Weaknesses:** Windows-only. V-Ray has steep learning curve. Point cloud workflow is basic compared to dedicated tools. $819/yr is steep. No Mac support for Studio features.

**PlanO exploit:** AI rendering (our Rasta engine) produces photorealistic images from text prompts in seconds -- no V-Ray learning curve. Democratize what Studio charges $819/yr for.

---

## 3. Core Modeling Tools (All Platforms)

| Tool | What It Does | Tier |
|------|-------------|------|
| Line | Draw edges | All |
| Rectangle | Draw rectangles | All |
| Circle / Polygon | Draw circles and polygons | All |
| Arc (2-point, 3-point, pie) | Draw arcs | All |
| Push/Pull | Extrude flat face into 3D volume | All |
| Follow Me | Extrude face along a path (cornices, pipes) | Go+ |
| Move | Translate geometry | All |
| Rotate | Rotate geometry with protractor snapping | All |
| Scale | Resize geometry | All |
| Offset | Create parallel edges inward/outward | All |
| Eraser | Delete edges/faces | All |
| Paint Bucket | Apply materials/colors | All |
| Tape Measure | Measure distances, create guides | All |
| Protractor | Measure and create angular guides | All |
| Dimensions | Add dimension annotations | All |
| Text / 3D Text | Label and annotate | All |
| Section Planes | Cut through model to see interiors | All |
| Orbit / Pan / Zoom | Navigate the 3D viewport | All |
| Solid Tools | Boolean operations (Union, Subtract, etc.) | Go+ |
| Sandbox | Terrain from contours/scratch | Pro+ |
| Axes | Set custom coordinate system | All |
| Interact | Click Dynamic Component behaviors | Pro+ |

---

## 4. 3D Warehouse

- **Scale:** Millions of free models (estimated 4-5M+)
- **Categories:** Architecture, furniture, fixtures, appliances, vehicles, landscapes, structural, MEP, signage, electronics, people, animals
- **Manufacturer models:** Curated catalogs from real brands (Herman Miller, IKEA-style, etc.)
- **Integration:** Direct download into SketchUp from within the app
- **User uploads:** Anyone can contribute
- **Filtering:** By polygon count, file size, likes, downloads
- **Limitations:** Quality varies wildly. Heavy models crash SketchUp. No quality control. Many models are poorly optimized.

**PlanO exploit:** We curate a renovation-specific library: cabinets, fixtures, tiles, flooring, appliances -- all with real pricing data and supplier links. Quality over quantity. AI generates custom furniture on demand.

---

## 5. Extension Warehouse

- **Count:** ~1000+ official extensions, 900+ on SketchUcation (third-party)
- **Categories:** Rendering, animation, terrain, architecture (walls/doors/windows), woodworking, CNC/fabrication, energy analysis, BIM, reporting, UV mapping, geometry tools
- **Popular extensions:** V-Ray, Enscape, Profile Builder (walls), 1001bit (architecture), Fredo6 suite (round corners, push/pull), Eneroth (various), Curic (deep select, section)
- **Pricing:** Mix of free and paid ($10-$500+)
- **Access:** Pro and Studio only. Free and Go users get nothing.
- **Limitation:** Extensions are desktop-only. Web/iPad users have zero extension access.

**PlanO exploit:** Every feature locked behind paid extensions -- wall tools, door/window insertion, rounding, UV mapping -- we build natively. "1000 extensions" means "1000 things that should be built in."

---

## 6. Trimble Connect

| Feature | Detail |
|---------|--------|
| Cloud storage | Unlimited for paid tiers, 10GB free |
| File support | 45+ file types |
| Sharing | Private links, public links, permission levels |
| Commenting | Real-time commenting on models |
| Viewer | Web, mobile, desktop viewers |
| Version history | Track model changes |
| Clash detection | Basic clash detection for BIM |
| To-do management | Assign tasks to team members |
| Activity log | Track who did what |
| Mixed-format projects | Combine SketchUp, IFC, DWG, PDF in one project |

**Weaknesses:** Clunky UI. Not real-time co-editing (you share snapshots, not live models). Poor compared to Figma-style collaboration. No integrated chat/video.

**PlanO exploit:** Real-time multiplayer editing (like Figma for floor plans). Contractor sees changes live. Homeowner approves in-canvas. Built-in chat. This is where SketchUp is 10 years behind.

---

## 7. AI Capabilities

| Feature | Detail | Tier |
|---------|--------|------|
| AI Render | Generative AI visualization from SketchUp scenes. Text prompts + style control. Inpainting, negative prompts, reference images. | Go+ (credit-based) |
| AI Assistant | Chatbot for help, troubleshooting, and modeling guidance. Can answer "how do I..." questions. | Go+ |
| Generate Object | Text/image prompt to 3D object. Creates simple geometry from description. | Go+ (30 credits/object) |
| Credit system | Starter allocation with subscription. AI Render = 5 credits. Generate Object = 30 credits. Extra credits purchasable. | Go+ |

**Weaknesses:**
- Credit-based = nickel-and-diming users
- AI Render produces concept images, not editable 3D geometry
- Generate Object creates basic shapes, not production-ready models
- AI Assistant is a chatbot, not an autonomous modeling agent
- No AI for: floor plan generation, cost estimation, material takeoffs, code compliance, contractor scheduling
- No AI-driven renovation workflow at all

**PlanO exploit:** This is our nuclear advantage. Rasta AI:
- Generates complete floor plans from room descriptions or photos
- Auto-estimates renovation costs with real supplier pricing
- Produces construction documents automatically
- AI is the core product, not a credit-gated add-on
- Understands building codes, contractor workflows, material compatibility
- AI renders are included, unlimited, not credit-metered

---

## 8. Floor Plan & Renovation Handling

**What SketchUp offers:**
- Manual wall drawing (line by line, push/pull to height)
- No dedicated wall tool (need extensions like Profile Builder or 1001bit)
- No automatic door/window insertion with proper wall cuts
- No room detection or labeling
- No area calculation per room (manual)
- Section planes for floor plan views, then LayOut for documentation
- Renovation: toggle layers for existing vs. new vs. demolished -- all manual setup
- No material/cost estimation
- No contractor-specific views or workflows
- No permit document generation
- No building code awareness

**What users actually do:**
- Draw everything from scratch
- Buy 3-5 extensions ($50-200 each) just to get basic architectural tools
- Spend hours on LayOut formatting construction documents
- Use separate software for cost estimation (Excel, Bluebeam, PlanSwift)
- Use separate software for scheduling (MS Project, Buildertrend)

**PlanO exploit:** This is the entire gap we fill:
- AI-assisted wall detection from photos or sketches
- Smart walls with automatic door/window cuts
- Room auto-detection with area/volume calculation
- Integrated cost estimation with real pricing
- One-click construction document generation
- Renovation-specific modes (existing/demolish/new with proper hatching)
- Contractor dashboard with material lists and scheduling
- Building code awareness per jurisdiction

---

## 9. Top User Complaints (G2, Capterra, Reddit, Forums)

| Complaint | Frequency | PlanO Response |
|-----------|-----------|----------------|
| **Crashes on complex models** | Very common | WebGL/Three.js with LOD + streaming = no crashes |
| **LayOut is clunky and slow** | Universal | No separate app needed -- docs auto-generated |
| **Too dependent on extensions** | Very common | Everything built in natively |
| **Subscription model frustration** | Common | Lower price + more value per dollar |
| **No parametric constraints** | Common | Constraint-based editing from day one |
| **Poor UV mapping** | Common | AI-driven material application |
| **No dedicated architectural tools** | Very common | Smart walls, doors, windows native |
| **Rendering requires V-Ray ($540+)** | Common | AI rendering included |
| **UI needs modernization** | Growing | Modern React UI, responsive, mobile-first |
| **No public roadmap** | Frustrating | Open development, public roadmap |
| **Material library gutted in 2025** | Recent outrage | Curated, growing library with AI generation |
| **No in-line math in dimensions** | Requested | Expression-based input (e.g., "3000-18*2") |
| **No SVG import natively** | Requested | SVG import native |
| **Web version too limited** | Common | Web-first, full feature parity |
| **No real-time collaboration** | Major gap | Figma-style multiplayer built in |

---

## 10. Missing Features Users Desperately Want

1. **Dedicated bevel/fillet tool** -- built in, not extension
2. **Non-destructive live booleans** -- modifier stack like Blender
3. **Spline/curve editing** -- post-creation control points
4. **Vertex/edge/face selection modes** -- sub-object editing
5. **Architectural toolset** -- smart walls, auto-stairs, railings
6. **Lofting/skinning** -- surface from cross-sections
7. **Better terrain tools** -- landscape architecture grade
8. **Parametric constraints** -- dimensions that drive geometry
9. **In-app rendering** -- without V-Ray
10. **Real-time collaboration** -- Google Docs for 3D

---

## 11. Strategic Summary for PlanO

### Where SketchUp is Strong (Respect)
- Brand recognition: 30M+ users, industry standard in architecture
- 3D Warehouse: massive free model library
- Push/Pull paradigm: intuitive 3D modeling concept
- Extension ecosystem: deep third-party investment
- Cross-platform: desktop + web + iPad
- Education market: strong pipeline of trained users

### Where SketchUp is Weak (Attack)
- **No renovation workflow** -- zero contractor-specific features
- **No cost estimation** -- completely absent
- **No AI-native design** -- AI is bolted on, credit-gated, superficial
- **Extension dependency** -- basic features require paid plugins
- **LayOut is universally hated** -- separate app, clunky, slow
- **No real-time collaboration** -- 2016-era sharing model
- **Web version is crippled** -- Free tier is a demo, not a product
- **No building code awareness** -- no regulatory intelligence
- **No homeowner-facing mode** -- only for professionals
- **Pricing creep** -- $399/yr for Pro, up from $349, trending to $500+

### PlanO Positioning
SketchUp is a general-purpose 3D modeler that architects have bent into a construction tool using extensions and workarounds. PlanO is purpose-built for renovation and construction, with AI at the core. We don't compete with SketchUp on general 3D modeling -- we make it irrelevant for the renovation/contractor market by doing in 5 minutes what takes them 5 hours.

**Key differentiators:**
1. AI-first (not AI-added)
2. Renovation-native (not general-purpose)
3. Cost estimation built in (not separate software)
4. Real-time collaboration (not file sharing)
5. Construction docs auto-generated (not manual LayOut)
6. Web-first, full features free tier (not crippled demo)
7. Homeowner + contractor dual interface (not pro-only)

---

## Sources

- [SketchUp Plans and Pricing](https://sketchup.trimble.com/en/plans-and-pricing)
- [SketchUp Price 2026 Full Guide](https://www.sketchupafrica.com/sketchup-price-in-2026-full-cost-plan-comparison-guide/)
- [SketchUp Pricing Breakdown](https://www.myarchitectai.com/blog/sketchup-pricing)
- [SketchUp Reviews - Capterra](https://www.capterra.com/p/211798/SketchUp/reviews/)
- [SketchUp Reviews - G2](https://www.g2.com/products/sketchup/reviews)
- [SketchUp AI Tools](https://sketchup.trimble.com/en/ai-in-sketchup)
- [SketchUp AI Launch - Engineering.com](https://www.engineering.com/trimble-launches-sketchup-ai-for-rendering-and-object-generation/)
- [SketchUp 2025 Features - CG Channel](https://www.cgchannel.com/2025/03/trimble-releases-sketchup-2025-0/)
- [SketchUp 2026 Features - CG Channel](https://www.cgchannel.com/2025/10/trimble-releases-sketchup-2026-0/)
- [SketchUp Feature Requests - Community Forum](https://forums.sketchup.com/t/sketchup-modeling-tool-feature-requests-modeling-tools-only/304583)
- [SketchUp What's New](https://sketchup.trimble.com/en/whats-new)
- [3D Warehouse](https://3dwarehouse.sketchup.com/)
- [Extension Warehouse](https://extensions.sketchup.com/)
- [Trimble Connect](https://sketchup.trimble.com/en/products/trimble-connect)
- [SketchUp for Construction](https://sketchup.trimble.com/en/industries/construction)
