// src/utils/scene-normalizer.ts
type AnyScene = any;

const toNum = (v: any): number | null => {
  const n = typeof v === 'number' ? v : typeof v === 'string' ? Number(v) : NaN;
  return Number.isFinite(n) ? n : null;
};

export function normalizeSceneFromRaster(raw: AnyScene): AnyScene {
  try {
    if (!raw || typeof raw !== 'object') return raw;

    const scene: AnyScene = { ...raw };

    const width = toNum(scene.width);
    const height = toNum(scene.height);

    // If we don't have height, we can't Y-flip safely → return original
    if (!height || height <= 0) return raw;

    const mirrorY = (y: any) => {
      const ny = toNum(y);
      return ny === null ? y : height - ny;
    };

    if (scene.layers && typeof scene.layers === 'object') {
      const newLayers: AnyScene = {};
      for (const [layerId, layer] of Object.entries(scene.layers)) {
        const L: AnyScene = { ...(layer as AnyScene) };

        if (L.vertices && typeof L.vertices === 'object') {
          const newVertices: AnyScene = {};
          for (const [vid, v] of Object.entries(L.vertices)) {
            const V: AnyScene = { ...(v as AnyScene) };
            V.y = mirrorY(V.y);
            newVertices[vid] = V;
          }
          L.vertices = newVertices;
        }

        if (L.items && typeof L.items === 'object') {
          const newItems: AnyScene = {};
          for (const [iid, it] of Object.entries(L.items)) {
            const I: AnyScene = { ...(it as AnyScene) };
            I.y = mirrorY(I.y);
            newItems[iid] = I;
          }
          L.items = newItems;
        }

        newLayers[layerId] = L;
      }
      scene.layers = newLayers;
    }

    if (scene.guides && typeof scene.guides === 'object') {
      const g: AnyScene = { ...scene.guides };

      if (g.circular && typeof g.circular === 'object') {
        const newCirc: AnyScene = {};
        for (const [gid, c] of Object.entries(g.circular)) {
          const C: AnyScene = { ...(c as AnyScene) };
          C.y = mirrorY(C.y);
          newCirc[gid] = C;
        }
        g.circular = newCirc;
      }

      if (g.horizontal && typeof g.horizontal === 'object') {
        const newH: AnyScene = {};
        for (const [hid, y] of Object.entries(g.horizontal)) {
          newH[hid] = mirrorY(y);
        }
        g.horizontal = newH;
      }

      scene.guides = g;
    }

    if (scene.groups && typeof scene.groups === 'object') {
      const newGroups: AnyScene = {};
      for (const [gid, gr] of Object.entries(scene.groups)) {
        const G: AnyScene = { ...(gr as AnyScene) };
        G.y = mirrorY(G.y);
        newGroups[gid] = G;
      }
      scene.groups = newGroups;
    }

    scene.meta = {
      ...(scene.meta || {}),
      __normalized: true,
      __normalized_mode: 'mirrorY',
      __normalized_dims: { width, height }
    };

    return scene;
  } catch (e) {
    // absolutely never block loading
    console.error('scene-normalizer failed:', e);
    return raw;
  }
}
