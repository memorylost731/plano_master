/**
 * PlanO — EU Market Configuration
 *
 * Architecture profiles per country for:
 * - Rasta AI model tuning (wall thickness, symbol style, scale)
 * - Cost estimation (labor rates, material costs by region)
 * - UI localization (units, currency, plan conventions)
 *
 * DEBUG: Each entry includes `_debug` metadata for traceability
 */

/* ── Types ── */

export type ArchCluster =
  | "mediterranean"    // MT, IT, ES, PT, GR, CY, HR
  | "nordic"           // FI, SE, DK
  | "central"          // DE, AT, CZ, SK, PL, HU, SI
  | "western"          // FR, BE, NL, LU
  | "atlantic"         // IE
  | "baltic"           // EE, LV, LT
  | "eastern"          // RO, BG
  ;

export type WallType =
  | "limestone"        // Malta, parts of Mediterranean
  | "brick"            // UK, NL, BE, Central Europe
  | "concrete_block"   // Southern/Eastern Europe
  | "timber_frame"     // Nordic, Baltic
  | "reinforced_concrete" // Apartment blocks everywhere
  | "prefab_panel"     // Eastern Europe (Soviet-era)
  | "aerated_concrete" // DE, AT, Scandinavia (Ytong/Porotherm)
  ;

export type PlanStandard = "din" | "bs" | "nf" | "uni" | "local";

export type FloorMaterial =
  | "ceramic_tile"
  | "porcelain_tile"
  | "hardwood"
  | "laminate"
  | "vinyl"
  | "stone"
  | "microcement"
  | "polished_concrete"
  | "parquet"
  | "carpet"
  ;

export interface CountryProfile {
  code: string;           // ISO 3166-1 alpha-2
  name: string;
  cluster: ArchCluster;
  currency: string;       // EUR, SEK, DKK, PLN, CZK, HUF, RON, BGN, HRK

  // Architecture
  wallTypes: WallType[];           // dominant wall construction, ordered by prevalence
  wallThicknessCm: [number, number]; // [exterior, interior partition]
  avgRoomSizes: {                   // m² averages
    bedroom: number;
    bathroom: number;
    kitchen: number;
    livingRoom: number;
  };
  commonBuildingTypes: string[];

  // Plan conventions
  planStandard: PlanStandard;
  scaleConventions: string[];      // e.g., ["1:50", "1:100"]
  unitSystem: "metric";            // all EU is metric
  doorSymbol: "arc" | "line" | "arc_and_line";
  windowSymbol: "double_line" | "filled" | "broken_line";

  // Rasta AI tuning
  rastaModelHints: {
    wallThicknessRange: [number, number]; // px range at 1:100 scale
    typicalDPI: number;
    dominantColors: string[];       // wall fill colors in plans
    textLanguage: string;           // for OCR room labels
  };

  // Materials palette (for cost estimation)
  flooringPalette: FloorMaterial[];
  wallFinishes: string[];

  // Market
  renovationMarketBn: number;      // billion EUR annual renovation market
  digitalPlanPct: number;          // % of building permits submitted digitally
  competitors: string[];

  // Debug metadata
  _debug: {
    dataSource: string;
    lastUpdated: string;
    confidence: "high" | "medium" | "low";
    notes: string;
  };
}

/* ── Country Profiles ── */

export const EU_COUNTRIES: CountryProfile[] = [
  // ═══════════════════════════════════════
  // MEDITERRANEAN CLUSTER
  // ═══════════════════════════════════════
  {
    code: "MT",
    name: "Malta",
    cluster: "mediterranean",
    currency: "EUR",
    wallTypes: ["limestone", "concrete_block", "reinforced_concrete"],
    wallThicknessCm: [30, 10],
    avgRoomSizes: { bedroom: 12, bathroom: 5, kitchen: 10, livingRoom: 18 },
    commonBuildingTypes: ["terraced house", "apartment block", "townhouse", "farmhouse (razzett)"],
    planStandard: "local",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 8],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "en",
    },
    flooringPalette: ["ceramic_tile", "porcelain_tile", "stone", "microcement"],
    wallFinishes: ["paint", "plaster (monacote)", "stone restoration", "silicato"],
    renovationMarketBn: 0.3,
    digitalPlanPct: 60,
    competitors: ["local architects", "no major SaaS"],
    _debug: {
      dataSource: "Malta PA, local market knowledge",
      lastUpdated: "2026-04-05",
      confidence: "high",
      notes: "Primary market. Limestone = unique thick walls. PA eApplications since 2006.",
    },
  },
  {
    code: "IT",
    name: "Italy",
    cluster: "mediterranean",
    currency: "EUR",
    wallTypes: ["brick", "reinforced_concrete", "concrete_block", "stone"],
    wallThicknessCm: [35, 10],
    avgRoomSizes: { bedroom: 14, bathroom: 5, kitchen: 10, livingRoom: 20 },
    commonBuildingTypes: ["apartment block", "townhouse", "villa", "rural farmhouse"],
    planStandard: "uni",
    scaleConventions: ["1:50", "1:100", "1:200"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 9],
      typicalDPI: 150,
      dominantColors: ["#000000", "#C0C0C0"],
      textLanguage: "it",
    },
    flooringPalette: ["ceramic_tile", "porcelain_tile", "stone", "parquet", "microcement"],
    wallFinishes: ["paint", "stucco", "Venetian plaster", "exposed brick"],
    renovationMarketBn: 75,
    digitalPlanPct: 50,
    competitors: ["Edilportale", "Houzz Italy", "local studios"],
    _debug: {
      dataSource: "ISTAT housing statistics, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "medium",
      notes: "Massive renovation market (Superbonus 110%). Regional variation extreme (North vs South).",
    },
  },
  {
    code: "ES",
    name: "Spain",
    cluster: "mediterranean",
    currency: "EUR",
    wallTypes: ["brick", "reinforced_concrete", "concrete_block"],
    wallThicknessCm: [25, 7],
    avgRoomSizes: { bedroom: 11, bathroom: 5, kitchen: 9, livingRoom: 20 },
    commonBuildingTypes: ["apartment block", "terraced house", "villa", "piso"],
    planStandard: "local",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [3, 7],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "es",
    },
    flooringPalette: ["ceramic_tile", "porcelain_tile", "laminate", "parquet"],
    wallFinishes: ["paint", "plaster", "exposed brick"],
    renovationMarketBn: 30,
    digitalPlanPct: 55,
    competitors: ["Habitissimo", "Houzz Spain", "Cerámicas"],
    _debug: {
      dataSource: "INE, CTE building code",
      lastUpdated: "2026-04-05",
      confidence: "medium",
      notes: "CTE (Código Técnico de la Edificación). Ceramic tile is king.",
    },
  },
  {
    code: "PT",
    name: "Portugal",
    cluster: "mediterranean",
    currency: "EUR",
    wallTypes: ["concrete_block", "reinforced_concrete", "stone"],
    wallThicknessCm: [25, 8],
    avgRoomSizes: { bedroom: 12, bathroom: 4, kitchen: 8, livingRoom: 18 },
    commonBuildingTypes: ["apartment block", "townhouse", "villa", "moradia"],
    planStandard: "local",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [3, 7],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "pt",
    },
    flooringPalette: ["ceramic_tile", "porcelain_tile", "hardwood", "stone"],
    wallFinishes: ["paint", "azulejo tiles", "plaster"],
    renovationMarketBn: 5,
    digitalPlanPct: 45,
    competitors: ["Habitissimo PT", "local architects"],
    _debug: {
      dataSource: "INE Portugal, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "medium",
      notes: "Golden Visa renovation boom. Azulejo tile tradition = unique wall treatment.",
    },
  },
  {
    code: "GR",
    name: "Greece",
    cluster: "mediterranean",
    currency: "EUR",
    wallTypes: ["reinforced_concrete", "brick", "concrete_block"],
    wallThicknessCm: [25, 10],
    avgRoomSizes: { bedroom: 12, bathroom: 4, kitchen: 8, livingRoom: 18 },
    commonBuildingTypes: ["apartment block (polykatoikia)", "villa", "island house"],
    planStandard: "local",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [3, 7],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "el",
    },
    flooringPalette: ["ceramic_tile", "stone", "marble", "laminate"],
    wallFinishes: ["paint", "plaster", "marble cladding"],
    renovationMarketBn: 3,
    digitalPlanPct: 35,
    competitors: ["spitogatos.gr", "local architects"],
    _debug: {
      dataSource: "ELSTAT, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "low",
      notes: "Polykatoikia (multi-story concrete) dominates. Very low digital plan adoption.",
    },
  },
  {
    code: "CY",
    name: "Cyprus",
    cluster: "mediterranean",
    currency: "EUR",
    wallTypes: ["concrete_block", "reinforced_concrete", "stone"],
    wallThicknessCm: [25, 10],
    avgRoomSizes: { bedroom: 14, bathroom: 5, kitchen: 10, livingRoom: 22 },
    commonBuildingTypes: ["villa", "apartment block", "townhouse"],
    planStandard: "local",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [3, 7],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "el",
    },
    flooringPalette: ["ceramic_tile", "porcelain_tile", "stone", "marble"],
    wallFinishes: ["paint", "plaster", "stone cladding"],
    renovationMarketBn: 0.5,
    digitalPlanPct: 40,
    competitors: ["local architects"],
    _debug: {
      dataSource: "CYSTAT, local knowledge",
      lastUpdated: "2026-04-05",
      confidence: "medium",
      notes: "Similar to Malta/Greece. Strong expat renovation market.",
    },
  },
  {
    code: "HR",
    name: "Croatia",
    cluster: "mediterranean",
    currency: "EUR",
    wallTypes: ["brick", "concrete_block", "reinforced_concrete", "stone"],
    wallThicknessCm: [30, 10],
    avgRoomSizes: { bedroom: 12, bathroom: 4, kitchen: 8, livingRoom: 18 },
    commonBuildingTypes: ["apartment block", "family house", "stone house (coast)"],
    planStandard: "local",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 8],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "hr",
    },
    flooringPalette: ["ceramic_tile", "laminate", "parquet", "stone"],
    wallFinishes: ["paint", "plaster", "stone restoration"],
    renovationMarketBn: 2,
    digitalPlanPct: 40,
    competitors: ["njuskalo.hr", "local architects"],
    _debug: {
      dataSource: "DZS Croatia, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "low",
      notes: "EU renovation wave funding available. Dalmatian coast = stone buildings.",
    },
  },

  // ═══════════════════════════════════════
  // NORDIC CLUSTER
  // ═══════════════════════════════════════
  {
    code: "FI",
    name: "Finland",
    cluster: "nordic",
    currency: "EUR",
    wallTypes: ["timber_frame", "aerated_concrete", "brick"],
    wallThicknessCm: [30, 10],
    avgRoomSizes: { bedroom: 14, bathroom: 6, kitchen: 12, livingRoom: 25 },
    commonBuildingTypes: ["detached house", "terraced house", "apartment block"],
    planStandard: "local",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 8],
      typicalDPI: 200,
      dominantColors: ["#000000", "#FFFFFF"],
      textLanguage: "fi",
    },
    flooringPalette: ["hardwood", "laminate", "vinyl", "ceramic_tile"],
    wallFinishes: ["paint", "wallpaper", "wood panel"],
    renovationMarketBn: 8,
    digitalPlanPct: 85,
    competitors: ["CubiCasa (HQ here!)", "Floorplanner"],
    _debug: {
      dataSource: "Statistics Finland, CubiCasa publications",
      lastUpdated: "2026-04-05",
      confidence: "high",
      notes: "CubiCasa5k was trained on Finnish plans — our baseline model. High digital adoption.",
    },
  },
  {
    code: "SE",
    name: "Sweden",
    cluster: "nordic",
    currency: "SEK",
    wallTypes: ["timber_frame", "aerated_concrete", "brick"],
    wallThicknessCm: [30, 10],
    avgRoomSizes: { bedroom: 13, bathroom: 6, kitchen: 12, livingRoom: 24 },
    commonBuildingTypes: ["detached house", "apartment block", "terraced (radhus)"],
    planStandard: "din",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 8],
      typicalDPI: 200,
      dominantColors: ["#000000", "#FFFFFF"],
      textLanguage: "sv",
    },
    flooringPalette: ["hardwood", "parquet", "laminate", "vinyl"],
    wallFinishes: ["paint", "wallpaper", "wood panel"],
    renovationMarketBn: 12,
    digitalPlanPct: 90,
    competitors: ["RoomSketcher (HQ here)", "Floorplanner", "Planner5D"],
    _debug: {
      dataSource: "SCB Sweden, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "high",
      notes: "RoomSketcher's home market. Very high digital adoption. BIM mandate for public buildings.",
    },
  },
  {
    code: "DK",
    name: "Denmark",
    cluster: "nordic",
    currency: "DKK",
    wallTypes: ["brick", "timber_frame", "aerated_concrete"],
    wallThicknessCm: [35, 10],
    avgRoomSizes: { bedroom: 13, bathroom: 6, kitchen: 11, livingRoom: 24 },
    commonBuildingTypes: ["detached house", "apartment block", "terraced (rækkehus)"],
    planStandard: "din",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 9],
      typicalDPI: 200,
      dominantColors: ["#000000", "#FFFFFF"],
      textLanguage: "da",
    },
    flooringPalette: ["hardwood", "parquet", "laminate", "vinyl"],
    wallFinishes: ["paint", "wallpaper"],
    renovationMarketBn: 8,
    digitalPlanPct: 85,
    competitors: ["Floorplanner", "MagicPlan"],
    _debug: {
      dataSource: "Danmarks Statistik, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "high",
      notes: "Red brick tradition. Very high digital plan adoption. Strong BIM culture.",
    },
  },

  // ═══════════════════════════════════════
  // CENTRAL EUROPEAN CLUSTER
  // ═══════════════════════════════════════
  {
    code: "DE",
    name: "Germany",
    cluster: "central",
    currency: "EUR",
    wallTypes: ["brick", "aerated_concrete", "reinforced_concrete", "timber_frame"],
    wallThicknessCm: [36, 11],
    avgRoomSizes: { bedroom: 15, bathroom: 7, kitchen: 10, livingRoom: 25 },
    commonBuildingTypes: ["apartment block (Mehrfamilienhaus)", "detached house (Einfamilienhaus)", "terraced (Reihenhaus)"],
    planStandard: "din",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc_and_line",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [5, 10],
      typicalDPI: 200,
      dominantColors: ["#000000", "#808080", "#FFFFFF"],
      textLanguage: "de",
    },
    flooringPalette: ["laminate", "parquet", "hardwood", "ceramic_tile", "vinyl"],
    wallFinishes: ["paint", "wallpaper", "Raufaser"],
    renovationMarketBn: 120,
    digitalPlanPct: 70,
    competitors: ["Roomle", "Cedreo", "Palette CAD", "local architects"],
    _debug: {
      dataSource: "Destatis, BMWK, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "high",
      notes: "Largest EU renovation market. DIN standard is the reference for Central Europe. Thick walls (EnEV insulation). KfW renovation subsidies driving demand.",
    },
  },
  {
    code: "AT",
    name: "Austria",
    cluster: "central",
    currency: "EUR",
    wallTypes: ["brick", "aerated_concrete", "timber_frame", "reinforced_concrete"],
    wallThicknessCm: [38, 12],
    avgRoomSizes: { bedroom: 15, bathroom: 6, kitchen: 10, livingRoom: 24 },
    commonBuildingTypes: ["apartment block", "detached house", "terraced house"],
    planStandard: "din",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc_and_line",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [5, 10],
      typicalDPI: 200,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "de",
    },
    flooringPalette: ["parquet", "hardwood", "laminate", "ceramic_tile"],
    wallFinishes: ["paint", "plaster", "wallpaper"],
    renovationMarketBn: 15,
    digitalPlanPct: 70,
    competitors: ["Roomle (HQ here)", "local architects"],
    _debug: {
      dataSource: "Statistik Austria, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "medium",
      notes: "Follows German standards closely. Roomle is based here. Very thick exterior walls (passive house standards).",
    },
  },
  {
    code: "CZ",
    name: "Czechia",
    cluster: "central",
    currency: "CZK",
    wallTypes: ["brick", "aerated_concrete", "prefab_panel", "reinforced_concrete"],
    wallThicknessCm: [30, 10],
    avgRoomSizes: { bedroom: 13, bathroom: 4, kitchen: 8, livingRoom: 20 },
    commonBuildingTypes: ["apartment block (panelák)", "family house", "townhouse"],
    planStandard: "din",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 8],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "cs",
    },
    flooringPalette: ["laminate", "vinyl", "ceramic_tile", "parquet"],
    wallFinishes: ["paint", "wallpaper", "plaster"],
    renovationMarketBn: 6,
    digitalPlanPct: 55,
    competitors: ["local architects", "Stavebniny DEK"],
    _debug: {
      dataSource: "CSU, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "medium",
      notes: "Panelák renovation = huge market (prefab concrete panel buildings). Czech follows DIN-adjacent standards.",
    },
  },
  {
    code: "SK",
    name: "Slovakia",
    cluster: "central",
    currency: "EUR",
    wallTypes: ["brick", "prefab_panel", "aerated_concrete"],
    wallThicknessCm: [30, 10],
    avgRoomSizes: { bedroom: 12, bathroom: 4, kitchen: 7, livingRoom: 18 },
    commonBuildingTypes: ["apartment block (panelák)", "family house"],
    planStandard: "din",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 8],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "sk",
    },
    flooringPalette: ["laminate", "vinyl", "ceramic_tile"],
    wallFinishes: ["paint", "wallpaper", "plaster"],
    renovationMarketBn: 2,
    digitalPlanPct: 45,
    competitors: ["local architects"],
    _debug: {
      dataSource: "SUSR, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "low",
      notes: "Similar to Czechia. Panelák renovation driven by EU funds.",
    },
  },
  {
    code: "PL",
    name: "Poland",
    cluster: "central",
    currency: "PLN",
    wallTypes: ["brick", "aerated_concrete", "prefab_panel", "reinforced_concrete"],
    wallThicknessCm: [30, 10],
    avgRoomSizes: { bedroom: 12, bathroom: 4, kitchen: 7, livingRoom: 18 },
    commonBuildingTypes: ["apartment block", "detached house", "terraced house"],
    planStandard: "din",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 8],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "pl",
    },
    flooringPalette: ["laminate", "ceramic_tile", "vinyl", "parquet"],
    wallFinishes: ["paint", "wallpaper", "plaster", "decorative stone"],
    renovationMarketBn: 15,
    digitalPlanPct: 50,
    competitors: ["OLX nieruchomosci", "Ceneo", "local architects"],
    _debug: {
      dataSource: "GUS Poland, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "medium",
      notes: "Large market, growing fast. Mix of panelák and new construction. EU renovation wave funds.",
    },
  },
  {
    code: "HU",
    name: "Hungary",
    cluster: "central",
    currency: "HUF",
    wallTypes: ["brick", "aerated_concrete", "prefab_panel"],
    wallThicknessCm: [30, 10],
    avgRoomSizes: { bedroom: 12, bathroom: 4, kitchen: 7, livingRoom: 18 },
    commonBuildingTypes: ["apartment block", "family house"],
    planStandard: "din",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 8],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "hu",
    },
    flooringPalette: ["laminate", "ceramic_tile", "parquet"],
    wallFinishes: ["paint", "wallpaper", "plaster"],
    renovationMarketBn: 4,
    digitalPlanPct: 40,
    competitors: ["ingatlan.com", "local architects"],
    _debug: {
      dataSource: "KSH, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "low",
      notes: "Socialist-era housing stock needs massive renovation. Low digital adoption.",
    },
  },
  {
    code: "SI",
    name: "Slovenia",
    cluster: "central",
    currency: "EUR",
    wallTypes: ["brick", "reinforced_concrete", "timber_frame"],
    wallThicknessCm: [30, 10],
    avgRoomSizes: { bedroom: 13, bathroom: 5, kitchen: 9, livingRoom: 20 },
    commonBuildingTypes: ["detached house", "apartment block", "terraced house"],
    planStandard: "din",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 8],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "sl",
    },
    flooringPalette: ["parquet", "laminate", "ceramic_tile"],
    wallFinishes: ["paint", "plaster"],
    renovationMarketBn: 1.5,
    digitalPlanPct: 55,
    competitors: ["local architects"],
    _debug: {
      dataSource: "SURS, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "low",
      notes: "Small market, high quality standards. Alpine + Mediterranean mix.",
    },
  },

  // ═══════════════════════════════════════
  // WESTERN EUROPEAN CLUSTER
  // ═══════════════════════════════════════
  {
    code: "FR",
    name: "France",
    cluster: "western",
    currency: "EUR",
    wallTypes: ["concrete_block", "brick", "reinforced_concrete", "timber_frame"],
    wallThicknessCm: [25, 7],
    avgRoomSizes: { bedroom: 12, bathroom: 5, kitchen: 9, livingRoom: 22 },
    commonBuildingTypes: ["apartment block (immeuble)", "house (maison)", "HLM social housing"],
    planStandard: "nf",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [3, 7],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "fr",
    },
    flooringPalette: ["parquet", "ceramic_tile", "laminate", "vinyl"],
    wallFinishes: ["paint", "wallpaper", "decorative plaster"],
    renovationMarketBn: 50,
    digitalPlanPct: 60,
    competitors: ["Kozikaza", "HomeByMe (Dassault)", "Cedreo", "Houzz France"],
    _debug: {
      dataSource: "INSEE, FNAIM, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "high",
      notes: "NF standards (Normes Françaises). MaPrimeRénov driving renovation. Second largest EU market.",
    },
  },
  {
    code: "BE",
    name: "Belgium",
    cluster: "western",
    currency: "EUR",
    wallTypes: ["brick", "concrete_block", "timber_frame"],
    wallThicknessCm: [30, 10],
    avgRoomSizes: { bedroom: 14, bathroom: 5, kitchen: 10, livingRoom: 22 },
    commonBuildingTypes: ["terraced house (rijwoning)", "apartment block", "detached house"],
    planStandard: "din",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 8],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "nl",
    },
    flooringPalette: ["laminate", "parquet", "ceramic_tile", "vinyl"],
    wallFinishes: ["paint", "wallpaper", "decorative plaster"],
    renovationMarketBn: 12,
    digitalPlanPct: 65,
    competitors: ["Immoweb", "Floorplanner", "local architects"],
    _debug: {
      dataSource: "Statbel, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "medium",
      notes: "Red brick tradition. Bilingual market (NL/FR). Energy renovation mandate driving demand.",
    },
  },
  {
    code: "NL",
    name: "Netherlands",
    cluster: "western",
    currency: "EUR",
    wallTypes: ["brick", "concrete_block", "timber_frame"],
    wallThicknessCm: [27, 10],
    avgRoomSizes: { bedroom: 13, bathroom: 5, kitchen: 10, livingRoom: 22 },
    commonBuildingTypes: ["terraced house (rijtjeshuis)", "apartment block", "canal house"],
    planStandard: "din",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [3, 7],
      typicalDPI: 200,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "nl",
    },
    flooringPalette: ["laminate", "hardwood", "vinyl", "ceramic_tile"],
    wallFinishes: ["paint", "stucco", "wallpaper"],
    renovationMarketBn: 15,
    digitalPlanPct: 80,
    competitors: ["Floorplanner (HQ here!)", "Funda", "local architects"],
    _debug: {
      dataSource: "CBS, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "high",
      notes: "Floorplanner's home market. Highest home ownership renovation rate in EU. Very digital.",
    },
  },
  {
    code: "LU",
    name: "Luxembourg",
    cluster: "western",
    currency: "EUR",
    wallTypes: ["brick", "aerated_concrete", "reinforced_concrete"],
    wallThicknessCm: [30, 10],
    avgRoomSizes: { bedroom: 15, bathroom: 6, kitchen: 12, livingRoom: 25 },
    commonBuildingTypes: ["detached house", "apartment block", "terraced house"],
    planStandard: "din",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc_and_line",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 8],
      typicalDPI: 200,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "fr",
    },
    flooringPalette: ["parquet", "ceramic_tile", "laminate"],
    wallFinishes: ["paint", "plaster", "wallpaper"],
    renovationMarketBn: 1.5,
    digitalPlanPct: 75,
    competitors: ["local architects"],
    _debug: {
      dataSource: "STATEC, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "low",
      notes: "Small but wealthy market. Follows German/French standards mix. High spend per project.",
    },
  },

  // ═══════════════════════════════════════
  // ATLANTIC CLUSTER
  // ═══════════════════════════════════════
  {
    code: "IE",
    name: "Ireland",
    cluster: "atlantic",
    currency: "EUR",
    wallTypes: ["concrete_block", "brick", "timber_frame"],
    wallThicknessCm: [30, 10],
    avgRoomSizes: { bedroom: 12, bathroom: 5, kitchen: 12, livingRoom: 20 },
    commonBuildingTypes: ["semi-detached house", "terraced house", "bungalow", "apartment"],
    planStandard: "bs",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 8],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "en",
    },
    flooringPalette: ["laminate", "hardwood", "ceramic_tile", "carpet"],
    wallFinishes: ["paint", "plaster", "wallpaper"],
    renovationMarketBn: 6,
    digitalPlanPct: 65,
    competitors: ["MyBuilder IE", "local architects"],
    _debug: {
      dataSource: "CSO Ireland, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "medium",
      notes: "BS standards (shared with UK). English-speaking = easy market entry. Housing crisis driving renovation.",
    },
  },

  // ═══════════════════════════════════════
  // BALTIC CLUSTER
  // ═══════════════════════════════════════
  {
    code: "EE",
    name: "Estonia",
    cluster: "baltic",
    currency: "EUR",
    wallTypes: ["timber_frame", "prefab_panel", "brick", "aerated_concrete"],
    wallThicknessCm: [30, 10],
    avgRoomSizes: { bedroom: 12, bathroom: 4, kitchen: 7, livingRoom: 18 },
    commonBuildingTypes: ["apartment block (hrushchyovka)", "detached house", "terraced house"],
    planStandard: "local",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 8],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "et",
    },
    flooringPalette: ["laminate", "hardwood", "vinyl", "ceramic_tile"],
    wallFinishes: ["paint", "wallpaper", "plaster"],
    renovationMarketBn: 1,
    digitalPlanPct: 80,
    competitors: ["local architects"],
    _debug: {
      dataSource: "Statistics Estonia, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "medium",
      notes: "Very digital-first country. Soviet-era housing stock needs renovation. E-residency = easy company setup.",
    },
  },
  {
    code: "LV",
    name: "Latvia",
    cluster: "baltic",
    currency: "EUR",
    wallTypes: ["prefab_panel", "brick", "timber_frame"],
    wallThicknessCm: [30, 10],
    avgRoomSizes: { bedroom: 11, bathroom: 3, kitchen: 6, livingRoom: 16 },
    commonBuildingTypes: ["apartment block", "detached house"],
    planStandard: "local",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 8],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "lv",
    },
    flooringPalette: ["laminate", "vinyl", "ceramic_tile", "hardwood"],
    wallFinishes: ["paint", "wallpaper", "plaster"],
    renovationMarketBn: 0.8,
    digitalPlanPct: 50,
    competitors: ["local architects"],
    _debug: {
      dataSource: "CSB Latvia, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "low",
      notes: "Soviet prefab renovation market. EU structural funds driving demand.",
    },
  },
  {
    code: "LT",
    name: "Lithuania",
    cluster: "baltic",
    currency: "EUR",
    wallTypes: ["prefab_panel", "brick", "aerated_concrete", "timber_frame"],
    wallThicknessCm: [30, 10],
    avgRoomSizes: { bedroom: 11, bathroom: 3, kitchen: 7, livingRoom: 17 },
    commonBuildingTypes: ["apartment block", "detached house"],
    planStandard: "local",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 8],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "lt",
    },
    flooringPalette: ["laminate", "vinyl", "ceramic_tile"],
    wallFinishes: ["paint", "wallpaper", "plaster"],
    renovationMarketBn: 1.2,
    digitalPlanPct: 55,
    competitors: ["local architects"],
    _debug: {
      dataSource: "Statistics Lithuania, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "low",
      notes: "Similar to Latvia. Multi-apartment renovation program driving demand.",
    },
  },

  // ═══════════════════════════════════════
  // EASTERN EUROPEAN CLUSTER
  // ═══════════════════════════════════════
  {
    code: "RO",
    name: "Romania",
    cluster: "eastern",
    currency: "RON",
    wallTypes: ["brick", "prefab_panel", "reinforced_concrete", "concrete_block"],
    wallThicknessCm: [30, 10],
    avgRoomSizes: { bedroom: 11, bathroom: 3, kitchen: 7, livingRoom: 16 },
    commonBuildingTypes: ["apartment block (bloc)", "detached house", "villa"],
    planStandard: "local",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [4, 8],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "ro",
    },
    flooringPalette: ["ceramic_tile", "laminate", "parquet", "vinyl"],
    wallFinishes: ["paint", "wallpaper", "decorative plaster"],
    renovationMarketBn: 5,
    digitalPlanPct: 35,
    competitors: ["Imobiliare.ro", "local architects"],
    _debug: {
      dataSource: "INS Romania, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "low",
      notes: "Fast-growing market. EU renovation wave funds. Mix of communist-era and new construction.",
    },
  },
  {
    code: "BG",
    name: "Bulgaria",
    cluster: "eastern",
    currency: "BGN",
    wallTypes: ["brick", "prefab_panel", "reinforced_concrete"],
    wallThicknessCm: [25, 10],
    avgRoomSizes: { bedroom: 11, bathroom: 3, kitchen: 6, livingRoom: 16 },
    commonBuildingTypes: ["apartment block", "detached house"],
    planStandard: "local",
    scaleConventions: ["1:50", "1:100"],
    unitSystem: "metric",
    doorSymbol: "arc",
    windowSymbol: "double_line",
    rastaModelHints: {
      wallThicknessRange: [3, 7],
      typicalDPI: 150,
      dominantColors: ["#000000", "#808080"],
      textLanguage: "bg",
    },
    flooringPalette: ["ceramic_tile", "laminate", "vinyl"],
    wallFinishes: ["paint", "plaster", "wallpaper"],
    renovationMarketBn: 1.5,
    digitalPlanPct: 25,
    competitors: ["imot.bg", "local architects"],
    _debug: {
      dataSource: "NSI Bulgaria, Eurostat",
      lastUpdated: "2026-04-05",
      confidence: "low",
      notes: "Lowest digital adoption in EU. Communist-era prefab renovation needed. Cheap labor market.",
    },
  },
];

/* ── Helper functions ── */

/** Get country profile by ISO code */
export function getCountry(code: string): CountryProfile | undefined {
  return EU_COUNTRIES.find((c) => c.code === code);
}

/** Get all countries in a cluster */
export function getCluster(cluster: ArchCluster): CountryProfile[] {
  return EU_COUNTRIES.filter((c) => c.cluster === cluster);
}

/** Get total EU renovation market size */
export function getTotalRenovationMarket(): number {
  return EU_COUNTRIES.reduce((sum, c) => sum + c.renovationMarketBn, 0);
}

/** Get countries sorted by renovation market size (for market prioritization) */
export function getMarketPriority(): CountryProfile[] {
  return [...EU_COUNTRIES].sort((a, b) => b.renovationMarketBn - a.renovationMarketBn);
}

/** Get Rasta model hints for a country (for AI config) */
export function getRastaConfig(code: string) {
  const country = getCountry(code);
  if (!country) return null;
  return {
    ...country.rastaModelHints,
    wallTypes: country.wallTypes,
    wallThicknessCm: country.wallThicknessCm,
    flooringPalette: country.flooringPalette,
    planStandard: country.planStandard,
  };
}

/* ── Debug: Print market summary ── */
if (typeof window !== "undefined" && (window as any).__PLANO_DEBUG__) {
  const total = getTotalRenovationMarket();
  console.log(`[PlanO] EU renovation market: €${total.toFixed(0)}B total`);
  console.log("[PlanO] Market priority:");
  getMarketPriority().slice(0, 10).forEach((c, i) => {
    console.log(`  ${i + 1}. ${c.name}: €${c.renovationMarketBn}B (${c.cluster})`);
  });
}
