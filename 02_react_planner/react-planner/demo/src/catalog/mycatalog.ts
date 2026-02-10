declare let require: {
  context(directory: string, useSubdirectories?: boolean, regExp?: RegExp): any;
};

import { CatalogFactory, CatalogFn } from '@archef2000/react-planner';

import Area from './areas/area/planner-element';
import Wall from './lines/wall/planner-element';

type CatalogElementAny = any;

function hasAnyTag(el: CatalogElementAny, tags: readonly string[]) {
  const t: string[] = el?.info?.tag || [];
  return tags.some((x) => t.includes(x));
}

function uniqByName(list: CatalogElementAny[]) {
  const seen = new Set<string>();
  const out: CatalogElementAny[] = [];
  for (const el of list) {
    const name = String(el?.name || '');
    if (!name || seen.has(name)) continue;
    seen.add(name);
    out.push(el);
  }
  return out;
}

// ---- PlanO -> tag mapping (adjust anytime) ----
const PLAN_O = {
  electricity: {
    label: 'Electricity',
    tagsAny: [
      'electronics',
      'telecomunication', // note: this is the tag used in your router-wifi element
      'electric',
      'panel'
    ]
  },
  plumbing: {
    label: 'Plumbing',
    tagsAny: ['sanitary', 'bathroom', 'plumbing', 'water']
  },
  painting: {
    label: 'Painting',
    tagsAny: ['paint', 'painting', 'painted']
  },
  flooring: {
    label: 'Flooring',
    tagsAny: ['floor', 'flooring', 'tile', 'tiles', 'parquet', 'laminate']
  },
  plastering: {
    label: 'Plastering',
    tagsAny: ['plaster', 'plastering']
  },
  boards: {
    label: 'Boards',
    tagsAny: ['board', 'boards', 'gypsum', 'drywall', 'ceiling']
  },
  other: {
    label: 'Other',
    tagsAny: []
  }
} as const;

// Optional sub-service grouping (coarse)
const SUBSERVICE_TAGS: Record<string, readonly string[]> = {
  // Electricity
  'Electrical panels': ['panel', 'electric'],
  'WiFi / Telecom': ['telecomunication'],
  'Smoke detector': ['smoke', 'detector'],
  AC: ['air-conditioner'],

  // Plumbing
  Toilet: ['toilet', 'sanitary', 'bathroom'],
  Sink: ['sink', 'sanitary', 'bathroom'],

  // Flooring
  Tiles: ['tile', 'tiles'],
  Parquet: ['parquet'],
  Laminate: ['laminate']
};

export function createCatalog() {
  const catalog = CatalogFactory();

  // Base geometry elements
  CatalogFn.registerElement(catalog, Area);
  CatalogFn.registerElement(catalog, Wall);

  // Load + register all holes
  const Holes: CatalogElementAny[] = [];
  const holesContext = require.context('./holes/', true, /planner-element\.[tj]sx$/);
  holesContext.keys().forEach((key: string) => {
    const element = holesContext(key).default;
    Holes.push(element);
    CatalogFn.registerElement(catalog, element);
  });

  // Load + register all items
  const Items: CatalogElementAny[] = [];
  const itemsContext = require.context('./items/', true, /planner-element\.[tj]sx$/);
  itemsContext.keys().forEach((key: string) => {
    const element = itemsContext(key).default;
    Items.push(element);
    CatalogFn.registerElement(catalog, element);
  });

  // Keep your existing categories
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

  // ---- PlanO categories ----
  const allCatalogItems = uniqByName([...Items, ...Holes]);

  const serviceBuckets: Record<string, CatalogElementAny[]> = {};
  for (const key of Object.keys(PLAN_O)) serviceBuckets[key] = [];

  for (const el of allCatalogItems) {
    let placed = false;

    for (const [serviceKey, def] of Object.entries(PLAN_O)) {
      if (serviceKey === 'other') continue;
      if (def.tagsAny.length && hasAnyTag(el, def.tagsAny)) {
        serviceBuckets[serviceKey].push(el);
        placed = true;
      }
    }

    if (!placed) serviceBuckets.other.push(el);
  }

  for (const [serviceKey, def] of Object.entries(PLAN_O)) {
    const label = def.label;
    const bucket = uniqByName(serviceBuckets[serviceKey]);

    // Create main category (top-level visible)
    CatalogFn.registerCategory(catalog, `plano_${serviceKey}`, `PlanO • ${label}`, []);

    // Create sub-categories if they match
    const used = new Set<string>();

    for (const [subLabel, tags] of Object.entries(SUBSERVICE_TAGS)) {
      const matches = bucket.filter((el) => hasAnyTag(el, tags));
      if (!matches.length) continue;

      const subName = `plano_${serviceKey}_${subLabel
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')}`;

      CatalogFn.registerCategory(catalog, subName, subLabel, uniqByName(matches));

      // Nest subcategory under the main PlanO category
      CatalogFn.addToCategory(
        catalog,
        `plano_${serviceKey}`,
        (catalog as any).categories[subName]
      );

      matches.forEach((m) => used.add(String(m.name)));
    }

    // Add remaining elements directly under the main category
    const rest = bucket.filter((el) => !used.has(String(el.name)));
    rest.forEach((el) => CatalogFn.addToCategory(catalog, `plano_${serviceKey}`, el));
  }

  return catalog;
}

export default createCatalog();
