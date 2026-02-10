declare let require: {
  context(directory: string, useSubdirectories?: boolean, regExp?: RegExp): any;
};

import { CatalogFactory, CatalogFn } from '@archef2000/react-planner';

import Area from './areas/area/planner-element';
import Wall from './lines/wall/planner-element';

// EXACT COPY of PlanO MAIN_SERVICES + SUBSERVICES (source: plano-ui/src/state/plannerState.tsx)
// NOTE: "other" exists in PlanO state, but we DO NOT render it as a catalog tile (per your request).
const PLANO_MAIN_SERVICES = [
  { key: 'electricity', label: 'Electricity' },
  { key: 'plumbing', label: 'Plumbing' },
  { key: 'painting', label: 'Painting' },
  { key: 'flooring', label: 'Flooring' },
  { key: 'plastering', label: 'Plastering' },
  { key: 'boards', label: 'Boards' },
  { key: 'other', label: 'Other' }
] as const;

const PLANO_SUBSERVICES: Record<(typeof PLANO_MAIN_SERVICES)[number]['key'], string[]> = {
  electricity: [
    'Switches & plugs',
    'Overlaps with plumbing',
    'Oven',
    'Hob',
    'Fridge freezer',
    'Microwave',
    'AC'
  ],
  plumbing: [
    'Floor drain',
    'Shower cubical',
    'Bathroom sink',
    'Mixers',
    'Kitchen sink',
    'Water heater',
    'Washing machine',
    'Dishwasher',
    'Tap for water'
  ],
  painting: ['Internal paint', 'External paint'],
  flooring: [
    'Ceramic tiles 60×60',
    'Ceramic tiles 120×60',
    'Ceramic tiles custom',
    'Laminate',
    'Microcement',
    'Polished concrete',
    'Parquet'
  ],
  plastering: [
    'Internal (monacote+finittura)',
    'Internal (microcement)',
    'External (GR1000)',
    'External (silicato)',
    'Stone restoration'
  ],
  boards: ['Flat ceiling', 'L-shape bulkhead', 'U-shape bulkhead', 'Custom shapes'],
  other: ['To be defined', 'Custom request', 'Special works']
};

function safeSlug(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
}

export function createCatalog() {
  const catalog: any = CatalogFactory();

  // Base geometry elements
  CatalogFn.registerElement(catalog, Area);
  CatalogFn.registerElement(catalog, Wall);

  // Load + register holes
  const Holes: any[] = [];
  const holesContext = require.context('./holes/', true, /planner-element\.[tj]sx$/);
  holesContext.keys().forEach((key: string) => {
    const el = holesContext(key).default;
    Holes.push(el);
    CatalogFn.registerElement(catalog, el);
  });

  // Load + register items
  const Items: any[] = [];
  const itemsContext = require.context('./items/', true, /planner-element\.[tj]sx$/);
  itemsContext.keys().forEach((key: string) => {
    const el = itemsContext(key).default;
    Items.push(el);
    CatalogFn.registerElement(catalog, el);
  });

  // Existing catalog categories (unchanged)
  CatalogFn.registerCategory(
    catalog,
    'windows',
    'Windows',
    Holes.filter((h) => h?.info?.tag?.includes('window'))
  );
  CatalogFn.registerCategory(
    catalog,
    'doors',
    'Doors',
    Holes.filter((h) => h?.info?.tag?.includes('door'))
  );

  // ---------------------------------------------------------
  // Append PlanO categories at the END (structure only; no moves)
  // ---------------------------------------------------------

  // Create subcategory without pushing it into root.categories (so it does NOT appear on root page)
  const ensureHiddenSubCategory = (name: string, label: string) => {
    if (!catalog.categories[name]) {
      catalog.categories[name] = { name, label, categories: [], elements: [] };
    }
    return catalog.categories[name];
  };

  for (const svc of PLANO_MAIN_SERVICES) {
    // Per your request: do NOT show "Other" in catalog
    if (svc.key === 'other') continue;

    const mainName = `plano_${svc.key}`;

    // Create main PlanO category tile (this is what appears at root; appended at end)
    if (!catalog.categories[mainName]) {
      CatalogFn.registerCategory(catalog, mainName, svc.label, []);
    }

    const mainCat = catalog.categories[mainName];

    // Create subcategories (empty placeholders for now; no guessing about which items go where)
    const subs = PLANO_SUBSERVICES[svc.key] || [];
    for (const subLabel of subs) {
      const subName = `plano_${svc.key}__${safeSlug(subLabel)}`;
      const subCat = ensureHiddenSubCategory(subName, subLabel);

      if (!mainCat.categories.some((c: any) => c.name === subCat.name)) {
        mainCat.categories.push(subCat);
      }
    }
  }

  return catalog;
}

export default createCatalog();
