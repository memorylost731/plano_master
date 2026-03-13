export interface PlanOCity {
  id: string;
  name: string;
  island: "Malta" | "Gozo";
  center: [number, number]; // [lng, lat]
  zoom: number;
  pitch: number;
  bearing: number;
  bbox: [number, number, number, number]; // [south, west, north, east] for Overpass queries
  description: string;
  active: boolean; // whether providers are onboarded
  default?: boolean; // default city on load
}

export const PLANO_CITIES: PlanOCity[] = [
  // ── Malta ──────────────────────────────────────
  {
    id: "valletta",
    name: "Valletta",
    island: "Malta",
    center: [14.5146, 35.8989],
    zoom: 16,
    pitch: 60,
    bearing: -20,
    bbox: [35.893, 14.506, 35.905, 14.522],
    description: "Capital city, UNESCO World Heritage",
    active: true,
    default: true,
  },
  {
    id: "sliema",
    name: "Sliema",
    island: "Malta",
    center: [14.5039, 35.9130],
    zoom: 16,
    pitch: 55,
    bearing: -15,
    bbox: [35.907, 14.495, 35.920, 14.510],
    description: "Residential & commercial waterfront",
    active: true,
  },
  {
    id: "st-julians",
    name: "St Julian's",
    island: "Malta",
    center: [14.4907, 35.9197],
    zoom: 15,
    pitch: 55,
    bearing: -10,
    bbox: [35.912, 14.480, 35.930, 14.500],
    description: "Entertainment, hospitality, high-rise development",
    active: true,
  },
  {
    id: "three-cities",
    name: "Three Cities",
    island: "Malta",
    center: [14.5220, 35.8870],
    zoom: 15,
    pitch: 50,
    bearing: 10,
    bbox: [35.880, 14.510, 35.895, 14.535],
    description: "Birgu, Senglea, Cospicua — heritage restoration hub",
    active: true,
  },
  {
    id: "birkirkara",
    name: "Birkirkara",
    island: "Malta",
    center: [14.4620, 35.8970],
    zoom: 15,
    pitch: 45,
    bearing: 0,
    bbox: [35.888, 14.450, 35.905, 14.475],
    description: "Largest town, dense residential",
    active: true,
  },
  {
    id: "mosta",
    name: "Mosta",
    island: "Malta",
    center: [14.4258, 35.9094],
    zoom: 15,
    pitch: 45,
    bearing: 5,
    bbox: [35.900, 14.415, 35.920, 14.440],
    description: "Central Malta, Rotunda landmark",
    active: true,
  },
  {
    id: "qormi",
    name: "Qormi",
    island: "Malta",
    center: [14.4720, 35.8760],
    zoom: 15,
    pitch: 45,
    bearing: 0,
    bbox: [35.868, 14.460, 35.885, 14.485],
    description: "Industrial & residential, affordable reno stock",
    active: true,
  },
  {
    id: "naxxar",
    name: "Naxxar",
    island: "Malta",
    center: [14.4430, 35.9150],
    zoom: 15,
    pitch: 45,
    bearing: 0,
    bbox: [35.905, 14.430, 35.925, 14.458],
    description: "Suburban growth, villa development",
    active: true,
  },
  {
    id: "rabat-malta",
    name: "Rabat",
    island: "Malta",
    center: [14.3990, 35.8830],
    zoom: 15,
    pitch: 50,
    bearing: -10,
    bbox: [35.874, 14.388, 35.893, 14.412],
    description: "Historic town, adjacent to Mdina",
    active: true,
  },
  {
    id: "mdina",
    name: "Mdina",
    island: "Malta",
    center: [14.4028, 35.8866],
    zoom: 17,
    pitch: 60,
    bearing: -25,
    bbox: [35.884, 14.399, 35.890, 14.407],
    description: "Silent City — fortified medieval capital",
    active: true,
  },
  {
    id: "marsaskala",
    name: "Marsaskala",
    island: "Malta",
    center: [14.5660, 35.8620],
    zoom: 15,
    pitch: 50,
    bearing: 15,
    bbox: [35.852, 14.555, 35.872, 14.578],
    description: "Southeastern coast, growing residential",
    active: true,
  },
  {
    id: "mellieha",
    name: "Mellieha",
    island: "Malta",
    center: [14.3620, 35.9560],
    zoom: 15,
    pitch: 50,
    bearing: -5,
    bbox: [35.945, 14.348, 35.967, 14.378],
    description: "Northern Malta, tourism & coastal development",
    active: true,
  },
  {
    id: "swieqi",
    name: "Swieqi",
    island: "Malta",
    center: [14.4800, 35.9240],
    zoom: 16,
    pitch: 50,
    bearing: 0,
    bbox: [35.917, 14.472, 35.932, 14.490],
    description: "Upscale residential, expat hub",
    active: true,
  },
  // ── Gozo ───────────────────────────────────────
  {
    id: "victoria-gozo",
    name: "Victoria (Rabat)",
    island: "Gozo",
    center: [14.2394, 36.0440],
    zoom: 16,
    pitch: 55,
    bearing: -10,
    bbox: [36.036, 14.230, 36.052, 14.250],
    description: "Gozo capital, Citadella fortress",
    active: true,
  },
  {
    id: "xlendi",
    name: "Xlendi",
    island: "Gozo",
    center: [14.2155, 36.0280],
    zoom: 17,
    pitch: 55,
    bearing: 0,
    bbox: [36.023, 14.210, 36.033, 14.222],
    description: "Coastal village, boutique renovation potential",
    active: true,
  },
  {
    id: "marsalforn",
    name: "Marsalforn",
    island: "Gozo",
    center: [14.2550, 36.0700],
    zoom: 16,
    pitch: 50,
    bearing: 10,
    bbox: [36.063, 14.245, 36.077, 14.265],
    description: "Gozo's main seaside resort",
    active: true,
  },
  {
    id: "nadur",
    name: "Nadur",
    island: "Gozo",
    center: [14.2920, 36.0370],
    zoom: 16,
    pitch: 50,
    bearing: 5,
    bbox: [36.028, 14.282, 36.046, 14.303],
    description: "Eastern Gozo, farmhouse conversion market",
    active: true,
  },
  {
    id: "sannat",
    name: "Sannat",
    island: "Gozo",
    center: [14.2430, 36.0220],
    zoom: 16,
    pitch: 50,
    bearing: 0,
    bbox: [36.014, 14.233, 36.030, 14.253],
    description: "Southern Gozo, Ta' Cenc cliffs area",
    active: true,
  },
  {
    id: "gharb",
    name: "Gharb",
    island: "Gozo",
    center: [14.2080, 36.0590],
    zoom: 16,
    pitch: 50,
    bearing: -5,
    bbox: [36.050, 14.198, 36.068, 14.218],
    description: "Western Gozo, rural heritage properties",
    active: true,
  },
];

export const DEFAULT_CITY =
  PLANO_CITIES.find((c) => c.default) || PLANO_CITIES[0];

export function getCityById(id: string): PlanOCity | undefined {
  return PLANO_CITIES.find((c) => c.id === id);
}

export function getCitiesByIsland(): Record<string, PlanOCity[]> {
  return PLANO_CITIES.reduce(
    (acc, city) => {
      if (!acc[city.island]) acc[city.island] = [];
      acc[city.island].push(city);
      return acc;
    },
    {} as Record<string, PlanOCity[]>,
  );
}
