

# European Floor Plan Recognition: Technical Specifications for CV Models

## 1. Symbol Standards by Country/Region

| Symbol | DIN 1356 (DE/AT/CH) | BS 1192 / BS 8541 (UK/IE) | NF P02-001 (FR) | UNI (IT) | Nordic (SFS/SS/NS) |
|--------|---------------------|---------------------------|------------------|----------|---------------------|
| **Door (swing)** | 90° arc + leaf line, wall break | 90° arc + leaf line, wall break | 90° arc, thinner leaf | 90° arc, wall break marked with ticks | 90° arc, often 30° increments shown |
| **Door (sliding)** | Dashed rectangle in wall, arrow | Dashed rectangle, arrow | Dashed line + arrow | Arrow along wall line | Dashed pocket, arrow |
| **Window** | Double parallel lines in wall break | Double line with center cross-hatch | Double line, sometimes filled black | Three parallel lines | Double line, short perpendicular ticks |
| **Stairs** | Arrow UP direction, numbered treads, break line at cut | Arrow UP, break line (zigzag) | Arrow sens montée, numbered | Arrow UP, break line | Arrow UP, treads numbered, diagonal break |
| **Walls (section)** | Solid fill or 45° hatch (concrete), no fill (masonry outlined) | Hatched (concrete), cross-hatched (brick), solid (structural) | Solid black fill (load-bearing), thin line (partition) | Solid fill or diagonal hatch | Solid black (load-bearing), thin line (non-load) |
| **Dimensions** | Meters with comma decimal (3,50), dimension chains, ticks | Millimeters (3500), arrows or ticks | Meters with comma (3,50), ticks | Meters with comma, ticks | Millimeters (3500), ticks |
| **Room labels** | Room name + area (m²) centered, font DIN 1451 | Room name + area, any clear font | Name + surface in m², centered | Name + area (mq) | Name + m², standardized fonts |

**Critical CV distinctions:**
- Wall representation is the highest-variance symbol. French plans use solid black for structural walls (easy to segment); German plans use hatch patterns requiring texture classification.
- Decimal separator: comma (continental) vs. period (UK/IE). Dimension units: mm (UK, Nordic) vs. m (DE, FR, IT).
- Door swing arcs are nearly universal but line weight varies 2-4x between traditions.

## 2. Standard Adoption by Country

| Standard Family | Countries | Key Document | Notes |
|----------------|-----------|--------------|-------|
| **DIN 1356** | Germany, Austria, Switzerland, Luxembourg | DIN 1356-1:1995 (replaced by DIN ISO 7519) | Most prescriptive. Hatch patterns codified. |
| **BS 1192 / BS 8541** | UK, Ireland, Malta, Cyprus | BS 8541-2:2011 (symbol library) | Transitioning to BS EN ISO 7519. mm units. |
| **NF P02-001** | France, Belgium (Wallonia), Monaco | NF P02-001:1987 | Solid-black load-bearing walls. Unique. |
| **UNI 3972 / UNI EN ISO** | Italy, San Marino | UNI EN ISO 7519:1997 | Triple-line windows distinctive. |
| **Nordic (SFS/SS/NS/DS)** | Finland, Sweden, Norway, Denmark | SFS-EN ISO 7519, SS-EN ISO 7519 | mm units, very clean minimal style. |
| **NEN** | Netherlands | NEN 47/NEN-EN-ISO 7519 | Hybrid DIN-influenced, metric. |
| **NBN** | Belgium (Flanders) | NBN-EN-ISO 7519 | DIN-influenced (Flanders) vs NF (Wallonia). |
| **CTE/UNE** | Spain, Portugal | UNE-EN ISO 7519 | DIN-influenced but local quirks in labeling. |
| **PN / ISO adoption** | Poland, Czechia, others (EU-East) | EN ISO 7519 direct adoption | Post-2000 ISO harmonization, older plans follow Soviet GOST remnants. |

**Key differences for CV:**

| Feature | DIN family | BS family | NF (French) |
|---------|-----------|-----------|-------------|
| Wall fill | Hatch patterns by material | Hatch + color coding | Solid black vs thin line |
| Units | m (comma) | mm (period) | m (comma) |
| Scale text | M 1:100 | Scale 1:100 | Éch. 1/100 |
| North arrow | Standard DIN symbol | Varies | Varies |
| Title block | Bottom-right, DIN A-series | Bottom-right, BS format | Bottom-right, cartouche |

## 3. Scale and Paper Conventions

| Plan Type | Standard Scales | Primary Paper | Orientation |
|-----------|----------------|---------------|-------------|
| Site plan | 1:200, 1:500 | A1 (594×841mm) | North-up preferred |
| Floor plan | **1:50** (DE/Nordic), **1:100** (FR/IT/ES/UK) | A1 or A3 (folded) | Longest facade horizontal |
| Detail plan | 1:20, 1:10, 1:5 | A3 (297×420mm) | Context-dependent |
| Planning/permit | 1:100, 1:200 | A1 | Per local authority |

**CV implications:** A model must detect the scale bar or title block to normalize measurements. 1:50 plans show individual brick courses and hardware; 1:100 plans abstract these away. The same building at 1:50 vs 1:100 produces fundamentally different symbol rendering.

## 4. Digital Format Landscape (2026 estimate)

| Region | Primary CAD | BIM Adoption | IFC Mandate | Hand-drawn % |
|--------|-------------|-------------|-------------|-------------|
| UK/IE | AutoCAD + Revit | **High** (70%+) | **Yes** — BS EN ISO 19650, public projects since 2016 | <5% |
| DE/AT/CH | AutoCAD, Allplan, ArchiCAD | **High** (60%+) | **Yes** — BIM mandate public >5M€ (2025+) | <5% |
| Nordics | Revit, ArchiCAD, MagiCAD | **Very high** (75%+) | **Yes** — Finland/Norway lead | <3% |
| FR | AutoCAD, Revit, Archicad | **Medium** (40%) | Partial — Plan BIM 2022 | ~10% (renovation sector) |
| IT | AutoCAD dominant | **Low-Medium** (25%) | Phased mandate (2025: >1M€) | ~15% |
| ES/PT | AutoCAD dominant | **Low** (20%) | Emerging mandates | ~15% |
| EU-East (PL/CZ/RO) | AutoCAD, Allplan | **Low** (15%) | Minimal | ~20% (older stock) |
| Mediterranean (GR/HR/MT) | AutoCAD, some hand-drawn | **Low** (10%) | None or pilot | 20-30% |

**Format distribution for training data:** Target ~50% DWG/DXF, ~25% PDF (print-from-CAD), ~15% scanned raster (hand-drawn), ~10% IFC/RVT exports. The scanned raster segment is critical — renovation projects (the bulk of European construction) often start from decades-old hand-drawn originals.

## 5. Data Augmentation Strategy

### Synthetic Generation Pipeline

```
Base templates (per standard family) → Parametric variation → Render → Degrade → Augment
```

**Step 1 — Parametric generation** (per-family templates):

| Parameter | Range | Method |
|-----------|-------|--------|
| Wall thickness | 100-600mm | Random within structural constraints |
| Room count | 1-12 per floor | Grammar-based layout generation |
| Door width | 700-1200mm | Uniform sampling |
| Window width | 600-2400mm | Uniform sampling |
| Symbol style | 5 families (DIN/BS/NF/UNI/Nordic) | Categorical selection |
| Scale | 1:50, 1:100, 1:200 | Affects line weight + detail level |

**Step 2 — Rendering transforms:**
- Line weight jitter: ±30% per element class
- Font substitution: 8-10 common architectural fonts (DIN 1451, Arial, Helvetica, Futura, ISOCPEUR)
- Hatch density variation: ±25%
- Annotation language: DE/EN/FR/IT/ES/SV/NL/PL label pools

**Step 3 — Degradation (simulating real-world scans):**
- Gaussian blur (σ=0.5-2.0) for scan quality
- Salt-and-pepper noise for photocopy artifacts
- Perspective warp (±3°) for misaligned scans
- JPEG compression (quality 30-85)
- Partial occlusion (stamps, annotations, coffee stains: 5-15% coverage)
- Yellowing/aging color shift for archival documents

**Step 4 — Geometric augmentation:**
- Rotation: 0°, 90°, 180°, 270° (plans are axis-aligned but scans aren't)
- Random crop (simulating partial sheets)
- Scale perturbation: ±10% (miscalibrated scanners)
- Mirror (valid for training; real plans aren't symmetric but symbol recognition is laterally invariant)

### Country-Crossing Augmentation

The key insight: **mix symbol families within a single plan** at low probability (~5%) to force the model to recognize symbols by shape rather than co-occurrence context. A French-style solid-black wall with German-style dimension ticks is unlikely in practice but teaches robust feature extraction.

### Recommended Training Distribution

| Source | Weight | Purpose |
|--------|--------|---------|
| Real annotated plans (CubiCasa5K, ROBIN, SESYD) | 30% | Ground truth diversity |
| Synthetic DIN-family | 20% | Largest market segment |
| Synthetic BS-family | 15% | BIM-heavy, clean data |
| Synthetic NF-family | 10% | Unique wall convention |
| Synthetic Nordic/UNI/mixed | 10% | Coverage |
| Degraded scans of all above | 15% | Robustness |

**Public datasets to bootstrap:** CubiCasa5K (5000 Finnish plans, annotated), ROBIN (100+ plans, room boundaries), SESYD (synthetic, symbols), BRIDGE (scanned historical), R2V (raster-to-vector benchmark). Supplement with permit archives — many EU municipalities publish planning applications as public records (UK Planning Portal, French permis de construire archives).
