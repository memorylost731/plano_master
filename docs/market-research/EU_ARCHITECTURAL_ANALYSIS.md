# PlanO EU Market Expansion: Architectural Analysis by Country

**Date:** 2026-04-05 | **Purpose:** AI model configuration per-country, regional pricing, floor plan detection tuning

---

## Architectural Similarity Clusters

| Cluster | Countries | Dominant Construction | Wall Thickness |
|---------|-----------|----------------------|----------------|
| **Nordic** | Sweden, Finland, Denmark | Timber frame, CLT, light steel | 150-250mm (frame + insulation up to 400mm) |
| **Atlantic** | Ireland, Netherlands, Belgium | Cavity brick/block | 250-350mm |
| **Germanic** | Germany, Austria, Luxembourg | Solid brick, concrete block, prefab | 240-365mm |
| **Mediterranean** | Malta, Italy, Spain, Portugal, Greece, Cyprus, Croatia | Stone/concrete block, reinforced concrete | 200-300mm |
| **French** | France | Concrete block (parpaing), stone in south | 200-300mm |
| **Central European** | Poland, Czechia, Slovakia, Hungary, Slovenia | Brick (Porotherm), concrete block | 250-450mm |
| **Baltic** | Estonia, Latvia, Lithuania | Soviet-era precast panel + modern brick/timber | 200-350mm |
| **Southeast** | Romania, Bulgaria | Brick, reinforced concrete frame | 250-380mm |

---

## 1. Wall Construction & Thickness

| Country | Dominant Wall Type | Typical Ext. (cm) | Partition (cm) | AI Detection Notes |
|---------|-------------------|-------------------|----------------|-------------------|
| **Malta** | Limestone block (franka) | 23-30 | 10-15 | Thick walls, irregular older cores |
| **Italy** | RC frame + hollow brick infill (laterizio) | 25-35 | 8-12 | Dual-layer with air gap common |
| **Spain** | RC frame + hollow brick | 25-30 | 7-10 | Thin partitions, thick perimeter |
| **Portugal** | RC frame + hollow brick | 25-30 | 10-15 | Similar to Spain |
| **Greece** | RC frame + hollow brick/concrete block | 20-30 | 10 | Seismic columns visible on plans |
| **Cyprus** | RC frame + concrete block | 20-25 | 10 | Flat roofs universal |
| **Croatia** | Stone (coast), brick/RC (inland) | 25-50 | 10-15 | Coastal = very thick stone |
| **France** | Concrete block (parpaing) 70%, stone 15% | 20-30 | 7-10 | Parpaing = 20cm standard module |
| **Germany** | Solid brick, Porotherm, prefab concrete | 24-36.5 | 11.5-17.5 | DIN standards, precise dimensions |
| **Austria** | Solid brick, Porotherm | 25-38 | 10-15 | Similar to Germany |
| **Netherlands** | Cavity wall (2x brick + gap) | 27-35 | 10 | Cavity wall signature on plans |
| **Belgium** | Cavity brick | 30-35 | 9-14 | Heavy masonry tradition |
| **Luxembourg** | Concrete block, brick | 25-36 | 10-15 | Mix of French/German practice |
| **Ireland** | Concrete block cavity wall | 30-35 | 10 | Block + insulation + block |
| **Denmark** | Brick exterior, timber/steel frame | 25-35 | 10-15 | Brick veneer on frame |
| **Sweden** | Timber frame, CLT | 15-20 (frame) | 7-10 | Thin walls, heavy insulation layer |
| **Finland** | Timber frame, concrete (apartments) | 15-20 (frame) | 7-10 | Log construction in rural |
| **Poland** | Porotherm brick, silicate block | 25-44 | 8-12 | Porotherm 25/38/44 standard |
| **Czechia** | Porotherm, concrete block | 25-44 | 11.5-15 | Very similar to Poland |
| **Slovakia** | Porotherm, brick | 25-38 | 10-15 | Central European standard |
| **Hungary** | Porotherm, brick (tegla) | 25-38 | 10 | 30cm Porotherm dominant new-build |
| **Slovenia** | Brick, RC frame | 25-35 | 10-15 | Mix of Italian/Austrian practice |
| **Romania** | Brick, RC frame, BCA (aerated concrete) | 25-37.5 | 10-15 | BCA (autoclaved aerated) growing fast |
| **Bulgaria** | Brick, RC frame | 25-38 | 10-12 | Soviet panel blocks still 30%+ stock |
| **Estonia** | Precast panel (Soviet), timber (new) | 20-35 | 8-12 | Panel buildings = uniform dimensions |
| **Latvia** | Precast panel, brick | 20-35 | 8-12 | Same as Estonia |
| **Lithuania** | Precast panel, ceramic block | 20-35 | 8-12 | Largest Soviet panel stock in Baltics |

---

## 2. Floor Plan Conventions & Standards

| Cluster | Drawing Standard | Units | Door Symbol | Window Symbol | Key Notes |
|---------|-----------------|-------|-------------|---------------|-----------|
| **Germanic** (DE/AT/LU) | DIN 1356 | Metric (cm) | Arc + wall break | Parallel lines in wall | Most precise, standardized |
| **Nordic** (SE/FI/DK) | National (SIS, RT) | Metric (mm) | Arc, simplified | Thin line in wall | BIM adoption highest (70%+) |
| **French** (FR/BE/LU) | NF P 02-001 | Metric (cm) | Arc + threshold | Glass line in wall | Detailed material hatching |
| **Mediterranean** (IT/ES/PT/GR/CY/MT/HR) | UNI (IT), CTE (ES), local | Metric (cm/m) | Arc | Double line | Variable quality, often hand-drawn |
| **Central** (PL/CZ/SK/HU/SI) | PN (PL), CSN (CZ), DIN-influenced | Metric (cm) | DIN-style arc | DIN-style parallel | Transitioning to BIM |
| **Baltic** (EE/LV/LT) | GOST legacy + EN | Metric (mm) | GOST or DIN | GOST or EN | Soviet plans use GOST symbols |
| **Southeast** (RO/BG) | STAS (RO), BDS (BG), GOST-derived | Metric (cm) | Mixed | Mixed | Older plans often GOST |
| **Atlantic** (IE/NL) | BS (IE), NEN (NL) | Metric (mm) | Arc | Break in wall | NL highly digitized |

**All EU countries use metric.** Ireland historically used imperial but switched; some older Irish plans show feet/inches.

---

## 3. Eurocodes & Building Permits

All 27 EU countries have adopted Eurocodes (EN 1990-1999) with **National Annexes** that modify parameters. Key variation:

| Factor | High Variation Countries | Impact on PlanO |
|--------|------------------------|-----------------|
| Snow/wind loads | Nordic, Alpine | Roof structure detection |
| Seismic zones | IT, GR, HR, RO, BG, CY, PT, SI | Shear walls, column sizes on plans |
| Fire resistance | All (varies by building class) | Wall thickness requirements |
| Energy (EPBD) | All (nZEB by 2021) | Insulation thickness affects wall detection |

**Permit digitization level:**

| Level | Countries | Format |
|-------|-----------|--------|
| Fully digital (e-permit) | DK, EE, NL, FI, SE, AT | PDF/BIM, open APIs |
| Mostly digital | DE, FR, IE, BE, LU, CZ, LT | PDF upload, some paper |
| Mixed | IT, ES, PT, PL, HU, SK, SI, LV | Varies by municipality |
| Mostly paper | MT, GR, CY, RO, BG, HR | Paper archives, scanning in progress |

---

## 4. Average Room Sizes (m2)

| Cluster | Bedroom | Bathroom | Kitchen | Living Room | Total Avg Apt |
|---------|---------|----------|---------|-------------|---------------|
| **Nordic** | 14-18 | 6-9 | 10-14 | 25-35 | 85-110 |
| **Germanic** | 14-16 | 6-8 | 10-12 | 20-30 | 75-95 |
| **Atlantic** | 12-15 | 5-7 | 10-14 | 18-25 | 70-90 |
| **French** | 11-14 | 4-6 | 8-12 | 18-25 | 65-85 |
| **Mediterranean** | 10-14 | 4-6 | 7-10 | 16-22 | 55-80 |
| **Central** | 12-16 | 4-6 | 8-10 | 18-24 | 55-75 |
| **Baltic** | 10-14 | 3-5 | 6-9 | 16-20 | 45-65 |
| **Southeast** | 10-14 | 3-5 | 7-10 | 16-22 | 50-70 |

**PlanO implication:** Room detection confidence thresholds must be cluster-adjusted. A 9m2 room is a bedroom in Malta but a closet in Sweden.

---

## 5. Housing Stock Composition

| Country | Apartments % | Detached % | Terraced/Semi % | Avg Age |
|---------|-------------|-----------|----------------|---------|
| **Spain** | 66 | 20 | 14 | 1970s |
| **Italy** | 53 | 25 | 22 | 1960s |
| **Germany** | 53 | 31 | 16 | 1960s |
| **France** | 44 | 38 | 18 | 1970s |
| **Netherlands** | 30 | 15 | 55 | 1960s |
| **Sweden** | 46 | 40 | 14 | 1960s |
| **Poland** | 44 | 45 | 11 | 1970s |
| **Romania** | 42 | 52 | 6 | 1970s |
| **Ireland** | 12 | 45 | 43 | 1980s |
| **Malta** | 48 | 17 | 35 | Mixed |

**Key pattern:** Mediterranean + Eastern = apartment-heavy (standardized floor plans, easier AI). NL/IE = terraced (repetitive layouts). Nordic = larger, more varied.

---

## 6. Renovation Market

| Country | Reno Market (EUR bn/yr) | Reno vs New Build | Growth Driver |
|---------|------------------------|-------------------|---------------|
| **Germany** | 120-140 | 70:30 | Energy retrofit (KfW subsidies) |
| **France** | 80-100 | 65:35 | MaPrimeRenov, DPE energy labels |
| **Italy** | 70-90 | 75:25 | Superbonus 110% (winding down) |
| **Spain** | 30-40 | 55:45 | EU Recovery Fund, tourism reno |
| **Netherlands** | 25-35 | 60:40 | Energy labels, heat pump mandate |
| **Poland** | 15-25 | 50:50 | EU cohesion funds, Clean Air |
| **Sweden** | 20-25 | 55:45 | ROT tax deduction (30%) |
| **Belgium** | 15-20 | 65:35 | Old stock, energy premiums |
| **Austria** | 12-18 | 60:40 | Raus aus Ol (exit oil) |
| **Ireland** | 8-12 | 45:55 | Housing crisis, SEAI grants |
| **Others** | 2-8 each | 40-65% reno | EU Renovation Wave target: 35M buildings by 2030 |

**Total EU renovation market: ~450-550 EUR bn/yr.** The EU Renovation Wave directive is the single biggest tailwind -- it mandates energy upgrades across all member states.

---

## 7. Material Palette by Cluster

| Cluster | Flooring | Wall Finish | Ceiling |
|---------|----------|-------------|---------|
| **Nordic** | Engineered wood, vinyl plank | Paint (white dominant) | Painted plaster, acoustic panels |
| **Germanic** | Laminate, engineered wood, tile (bathrooms) | Paint, Raufaser wallpaper (DE) | Painted plaster |
| **Atlantic** | Carpet (IE/UK legacy), laminate, tile | Paint, wallpaper (NL) | Painted plaster, suspended |
| **French** | Parquet, tile, vinyl | Paint (white/neutral) | Plaster, exposed beams (south) |
| **Mediterranean** | Ceramic/porcelain tile dominant | Paint, plaster (exposed stone accent) | Plaster, concrete slab |
| **Central** | Laminate, wood parquet, tile | Paint, wallpaper (older) | Plaster, suspended (offices) |
| **Baltic** | Laminate, vinyl, parquet | Paint, wallpaper (older Soviet) | Plaster, drop ceiling |
| **Southeast** | Ceramic tile, laminate | Paint, decorative plaster | Plaster, concrete slab |

**PlanO pricing implication:** Tile labor is 2-3x more expensive in Nordic vs Mediterranean. Wood flooring is standard in North but premium in South.

---

## 8. Key Competitors by Market

| Market | Competitor | Type | Strength |
|--------|-----------|------|----------|
| **DE** | Planungswelten, Houzz DE, McMakler | Visualization + marketplace | Large user base |
| **FR** | Kozikaza, HomeByMe (Dassault) | Free 3D planning | HomeByMe = massive (Dassault backed) |
| **IT** | Houzz IT, DomuS3D | Design + manufacturer catalog | Tile/bathroom focus |
| **ES** | Planner5D ES, Habitissimo | Planning + contractor matching | Habitissimo = lead gen |
| **NL** | Floorplanner (HQ here), Verbouwkosten.com | Floor plan + cost calculator | Floorplanner is global from NL |
| **Nordic** | Roomsketcher (NO-origin), Byggahus.se | Planning + DIY community | RoomSketcher = main rival |
| **PL** | Homebook.pl, Archipelag | Design + prefab house plans | Cost estimation gap |
| **IE** | MyHome.ie, BuildStore | Property + self-build | No plan AI competitors |
| **EE/LV/LT** | Minimal local competition | -- | Blue ocean |
| **RO/BG** | Minimal local competition | -- | Blue ocean |
| **MT** | None significant | -- | Home market, test here first |

---

## 9. PlanO Configuration Matrix (Recommended)

| Parameter | Nordic | Germanic | Atlantic | French | Mediterranean | Central | Baltic | Southeast |
|-----------|--------|----------|----------|--------|---------------|---------|--------|-----------|
| Min wall detect (px) | 3 | 5 | 5 | 4 | 5 | 5 | 4 | 5 |
| Partition threshold (cm) | 10 | 11.5 | 10 | 7 | 8 | 10 | 8 | 10 |
| Room size min (m2) | 6 | 5 | 4 | 4 | 3 | 4 | 3 | 3 |
| Symbol library | SIS/RT | DIN 1356 | BS/NEN | NF | UNI/local | DIN-derived | GOST+EN | GOST+EN |
| Default tile floor | No | No | No | Mixed | Yes | No | No | Yes |
| Labor rate index | 3.0x | 2.5x | 2.2x | 2.0x | 1.0x (base) | 0.8x | 0.6x | 0.5x |
| BIM likelihood | High | Medium | Medium | Medium | Low | Low | Low | Low |
| Plan quality | High | High | Medium | Medium | Variable | Medium | Variable | Variable |

---

## 10. Expansion Priority (Market Size x Accessibility x Competition Gap)

| Priority | Country | Why |
|----------|---------|-----|
| 1 | **Malta** | Home market, live now |
| 2 | **Italy** | Huge reno market, weak digital tools, similar construction to Malta |
| 3 | **France** | MaPrimeRenov creates demand, HomeByMe is visualization-only (no cost) |
| 4 | **Germany** | Largest market, high willingness to pay, but competitive |
| 5 | **Spain** | Large reno wave, tourism-driven, low competition |
| 6 | **Netherlands** | Highly digital, Floorplanner HQ but no cost estimation |
| 7 | **Poland** | Fast-growing, EU funds, almost no competition |
| 8 | **Ireland** | English-speaking, housing crisis, no competitors |
| 9 | **Nordics** (SE/FI/DK) | High spend per project, RoomSketcher is main rival |
| 10 | **Baltics + SE Europe** | Blue ocean but small markets |

---

*Generated for PlanO market expansion planning. Labor rate indices are relative to Mediterranean baseline. All figures are estimates based on Eurostat housing data, national building codes, and industry reports (2024-2026).*
