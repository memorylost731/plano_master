

# PlanO Construction/Renovation Technology Landscape: 2026-2031 Projections

## Methodology Note

These projections synthesize publicly available data through early 2025: industry reports (McKinsey, BCG, Dodge Construction Network), EU regulatory calendars, patent filings, VC funding databases, and technology capability trajectories. Confidence levels reflect the inherent uncertainty in multi-year forecasting — treat "High" confidence predictions as planning assumptions and "Medium/Low" as scenario inputs.

---

## TIER 1: 3-Year Practical Projections (2026-2028) — High Confidence

### AI/ML in Construction

| Prediction | Date | Probability | Confidence | Reasoning | PlanO Action |
|---|---|---|---|---|---|
| Floor plan recognition hits 97% accuracy | Q2 2027 | 85% | High | CubiCasa5k baseline was 91% in 2023; transformer-based architectures (LayoutLMv3, Donut) are gaining 2-3 pts/year on document understanding tasks. 99% requires domain-specific fine-tuning on diverse EU housing stock | **Invest in proprietary training data NOW** — photograph 10K+ EU floor plans (Malta, Bulgaria priority). The gap between 97% and 99% is where your competitive moat lives |
| Floor plan recognition hits 99% accuracy | Q4 2028 | 55% | Medium | The last 2% requires handling edge cases: hand-drawn plans, poor scans, non-standard EU formats. Needs large labeled datasets that don't exist publicly yet | Build annotation pipeline; this dataset becomes an acquisition asset |
| AI generates complete renovation plans from text | Q3 2028 | 40% | Medium | GPT-4V/Claude already generate rough layouts. "Complete" means structurally valid + code-compliant + costed. Compliance is the bottleneck — building codes are not yet machine-readable in most EU countries | Build a machine-readable EU building code database (Malta first). This is the real moat, not the AI model |
| AI cost estimation within 5% margin | Q1 2028 | 45% | Medium | Requires: (1) regional material price feeds, (2) labor rate databases, (3) scope-of-work classification. Data availability, not model capability, is the constraint | Partner with material suppliers for price APIs. Start collecting actual vs. estimated costs from every PlanO job |
| Generative AI interior design goes mainstream | Q2 2027 | 75% | High | Already happening (Midjourney, DALL-E for mood boards). "Mainstream" = contractors showing AI renders to clients as standard practice. Adoption curve follows smartphone photography in real estate (~3 years from novelty to expectation) | Add AI room visualization as a feature by Q4 2026. Low engineering cost, high perceived value |

### Hardware Trajectory

| Prediction | Date | Probability | Confidence | Reasoning | PlanO Action |
|---|---|---|---|---|---|
| Budget phones (<$300) with LiDAR | Q4 2028 | 50% | Medium | Sony's dToF sensors are commoditizing. Samsung included basic ToF in A-series briefly, then removed it. The driver will be AR applications creating consumer demand. Currently: iPhone Pro ($999+), iPad Pro ($799+) only have survey-grade LiDAR | **Do not build LiDAR-dependent features as primary flow.** Keep it as premium enhancement. Photogrammetry (multi-photo 3D) on standard cameras is the democratic path |
| Phone runs real-time floor plan detection locally | Q2 2027 | 70% | High | Qualcomm Snapdragon 8 Gen 3 NPU already does 75 TOPS. MobileNet-class models for room segmentation run at 30fps today. The bottleneck is model optimization, not hardware | Build an on-device model. Privacy advantage (floor plans never leave phone), works offline on construction sites with no signal. Major differentiator |
| AR glasses <$500 exist | Q1 2027 | 60% | Medium | Meta Orion prototype shown 2024, consumer target ~2027. Xreal Air 2 already $399 but limited FOV. "Usable for construction" needs spatial anchoring + outdoor brightness | Monitor but don't build for AR glasses yet. When they arrive, PlanO's 3D model data becomes the content layer |
| 10% of EU contractors use AR on-site | 2030+ | 30% | Low | Construction is notoriously slow to adopt. Hard hats + safety glasses + AR = ergonomic nightmare. Tablet-based AR (hold up iPad, see overlay) will precede glasses | Support tablet AR overlay of renovation plans onto real rooms by Q4 2027 |

### EU Regulatory Timeline

| Prediction | Date | Probability | Confidence | Reasoning | PlanO Action |
|---|---|---|---|---|---|
| EPBD MEPS: worst-performing (G-rated) buildings must renovate to F | 2030 (residential), 2027 (non-residential) | 90% | High | EPBD recast adopted 2024. Non-residential: EPC F by 2027, EPC E by 2030. Residential: national trajectories due by 2026, zero-emission target by 2050. Countries have some flexibility | **This is PlanO's single largest demand driver.** Build EPC improvement simulation: "your building is G, here's the renovation to reach F, here's the cost." Malta has ~45% G/F rated buildings |
| Malta MEPS transposition | Q2 2027 | 70% | High | Malta typically transposes late but EU pressure is intense. BCA (Building & Construction Authority) already consulting | Be the platform Malta's BCA recommends. Attend consultation, offer PlanO as compliance tool |
| Bulgaria MEPS transposition | Q4 2027 | 60% | Medium | Bulgaria has massive G/F stock (~60%). EU structural funds conditional on EPBD compliance | Bulgaria = high volume, low ARPU. Partner with local contractors, price in BGN |
| BIM mandate expands to residential renovation | 2029-2030 | 45% | Medium | Currently BIM mandated for public works >€5M in most EU states. Trend is downward in threshold. Residential renovation BIM is 5+ years away except in Nordics | Build "BIM-lite" export — simplified IFC files from PlanO renovation plans. Positions for mandate without over-engineering |
| Digital-only building permits (3+ EU countries) | 2028 | 65% | High | Estonia (already digital), Finland (2025-2026), Netherlands (2026-2027). France piloting. Others follow | Build permit-ready PDF/XML export. When digital permits arrive, PlanO should generate submission-ready packages automatically |

---

## TIER 2: 5-Year Speculative Projections (2029-2031) — Medium Confidence

### Market Size

| Metric | 2026 | 2028 | 2031 | Source/Reasoning |
|---|---|---|---|---|
| EU renovation market (total) | €275B | €310B | €375B | European Commission Renovation Wave targets 35M building units by 2030. EPBD MEPS forces the spending. ~4% CAGR accelerating post-2028 as MEPS enforcement bites |
| Malta renovation market | €180M | €220M | €300M | Small absolute, high growth. EU Recovery & Resilience funds allocate €54M for green transition. MEPS forces 45% of building stock through renovation |
| Bulgaria renovation market | €1.8B | €2.4B | €3.5B | €2.7B allocated in EU structural funds for energy renovation 2021-2027 cycle. Disbursement peaks 2026-2028. Second cycle extends to 2031 |
| SaaS penetration in EU construction | 12% | 18% | 28% | McKinsey (2023): construction digitization at ~15 years behind other industries. SaaS penetration was 8% in 2023, growing ~3pts/year. COVID accelerated by 2 years |
| EU contractors using SaaS tools | 1.2M | 1.8M | 2.8M | ~10M contractors in EU. Micro-firms (<5 employees) are 95% of the market. Mobile-first SaaS that works in the field wins |

### Competitor Trajectory

| Prediction | Date | Probability | Confidence | Reasoning | PlanO Action |
|---|---|---|---|---|---|
| Autodesk enters renovation SaaS directly | Q2 2028 | 55% | Medium | PlanGrid acquisition ($875M, 2018) was project management, not design. Autodesk's DNA is enterprise/commercial. Residential renovation is low-ARPU, high-volume — not their model. More likely: they acquire someone | Be acquirable or be differentiated. If PlanO has 50K+ users and proprietary EU renovation data, Autodesk is a buyer |
| SketchUp adds AI floor plan recognition | Q4 2027 | 65% | Medium | Trimble (SketchUp owner) has been adding AI features. Floor plan → 3D model is obvious. But SketchUp serves architects, not contractors/homeowners | PlanO's audience is downstream of SketchUp. Different buyer persona. Not a direct threat if PlanO stays contractor/homeowner focused |
| Apple expands RoomPlan into renovation | 2028-2029 | 40% | Low | Apple has LiDAR + RoomPlan API + ARKit. But Apple builds platforms, not vertical SaaS. More likely: they improve RoomPlan API and PlanO builds on it | Build on RoomPlan API today. If Apple improves the scan, PlanO benefits. If Apple enters renovation, they'll need content partners |
| Google enters home renovation | 2029+ | 25% | Low | Google killed Measure app (2023). ARCore is developer-focused. Google's pattern: build platform, let others build apps. Threat is indirect (improved ARCore makes competitors easier to build) | Low threat. Use ARCore for Android parity with Apple LiDAR |

### Startups to Watch

- **Beamy (France)** — raised €10M 2024, BIM + renovation compliance
- **Facilio (Singapore/EU)** — $35M Series B, building operations
- **Hover (US)** — $120M raised, exterior measurements from photos. Could pivot to interior
- **Oculo (UK)** — 360° site documentation, raised £1.5M seed
- **iSolve/Zillow-adjacent startups** — US-focused, but EU expansion likely post-2028

### Exit Market

| Metric | 2026-2027 | 2028-2029 | 2030-2031 |
|---|---|---|---|
| SaaS revenue multiples (construction vertical) | 6-8x ARR | 7-10x ARR | 8-12x ARR (if EPBD drives adoption wave) |
| ARR threshold for acquisition interest | €2M+ | €3M+ | €5M+ (as market matures, bar rises) |
| PE/VC appetite for construction tech | Recovering (post-2023 correction) | Strong (EPBD enforcement = guaranteed demand) | Peak (proving period, clear winners emerge) |
| Active acquirers | Autodesk, Trimble, Nemetschek, Procore | + Schneider Electric, Saint-Gobain, Kingspan | + PE rollups (Thoma Bravo pattern) |

**Key signal:** Procore ($PCOR, $10B market cap) acquired 4 companies in 2023-2024. Nemetschek acquired GoCanvas for $400M (2024). The vertical is consolidating. Construction SaaS companies with €2M+ ARR and strong EU positioning will attract offers.

---

## Strategic Implications for PlanO (Priority-Ordered)

1. **EPBD compliance tooling is the #1 growth lever.** Build EPC simulation + renovation pathway generator before competitors. Malta and Bulgaria first (small markets, fast iteration, EU funds flowing).

2. **On-device AI is the moat.** Floor plan detection that runs on a phone, offline, with no cloud dependency = privacy advantage + works on construction sites. Invest here over cloud AI.

3. **Proprietary renovation data compounds.** Every floor plan scanned, every cost estimate validated, every renovation completed through PlanO trains the next model. Start collecting ground truth data immediately.

4. **Do not bet on LiDAR or AR glasses for the 3-year plan.** Both are coming but not at the price point or adoption level that moves your market. Photogrammetry and standard camera AI is the path.

5. **Position for acquisition by 2029-2030.** The EPBD enforcement wave (2027-2030) will peak acquirer interest. Target: €3M ARR, 50K+ active users, proprietary EU building data, multi-country. Autodesk, Nemetschek, or Procore are natural buyers. Current construction SaaS multiples at 6-10x ARR make a €20-30M exit realistic at €3M ARR.

6. **Autonomous AI agents handling 100% of SaaS ops** — realistic timeline is 2030+ for back-office (billing, support, onboarding), never for the full product loop within this window. Plan for AI-assisted, not AI-autonomous.
