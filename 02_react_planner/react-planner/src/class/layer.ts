import { produce } from 'immer';

import { Layer as LayerModel, State } from '../models';
import { ElementPrototypes } from '../types';
import { GeometryUtils, GraphInnerCycles, IDBroker } from '../utils/export';

import { Area, Hole, Item, Line, Project, Vertex } from './export';

const sameSet = (set1: Set<string>, set2: Set<string>) =>
  set1.size === set2.size && set1.isSupersetOf(set2) && set1.isSupersetOf(set2);

class Layer {
  static create(state: State, name: string, altitude: number) {
    return produce(state, (draft) => {
      const layerID = IDBroker.acquireID();
      name = name || `layer ${layerID}`;
      altitude = altitude || 0;

      const layer = LayerModel({ id: layerID, name, altitude });
      draft.scene.selectedLayer = layerID;
      draft.scene.layers[layerID] = layer;
    });
  }

  static select(state: State, layerID: string) {
    return produce(state, (draft) => {
      if (!draft.alterate) {
        draft = Project.unselectAll(draft);
      }
      draft.scene.selectedLayer = layerID;
      return draft;
    });
  }

  static selectElement(
    state: State,
    layerID: string,
    elementPrototype: ElementPrototypes,
    elementID: string
  ) {
    return produce(state, (draft) => {
      const layer: any = draft.scene.layers[layerID];
      if (!layer) return;
      const element = layer[elementPrototype]?.[elementID];
      if (!element) return;

      element.selected = true;

      const list = layer.selected?.[elementPrototype];
      if (!Array.isArray(list)) return;
      if (list.includes(elementID)) return;
      list.push(elementID);
    });
  }

  static unselect(
    state: State,
    layerID: string,
    elementPrototype: ElementPrototypes,
    elementID: string
  ) {
    return produce(state, (draft) => {
      const layer: any = draft.scene.layers[layerID];
      if (!layer) return;

      const list = layer.selected?.[elementPrototype];
      if (Array.isArray(list)) {
        layer.selected[elementPrototype] = list.filter((el: string) => el !== elementID);
      }

      const element = layer[elementPrototype]?.[elementID];
      if (!element) return;
      element.selected = false;
    });
  }

  static unselectAll(state: State, layerID: string) {
    state = produce(state, (draft) => {
      const layer: any = draft.scene.layers[layerID];
      if (!layer) return;

      const { lines, holes, items, areas } = layer;

      Object.values(lines).forEach((line: any) => {
        draft = Line.unselect(draft, layerID, line.id);
      });
      Object.values(holes).forEach((hole: any) => {
        draft = Hole.unselect(draft, layerID, hole.id);
      });
      Object.values(items).forEach((item: any) => {
        draft = Item.unselect(draft, layerID, item.id);
      });
      Object.values(areas).forEach((area: any) => {
        draft = Area.unselect(draft, layerID, area.id);
      });
      return draft;
    });

    return produce(state, (draft) => {
      const layer: any = draft.scene.layers[layerID];
      if (!layer) return;

      layer.selected = {
        lines: [],
        holes: [],
        items: [],
        areas: [],
        vertices: []
      };
    });
  }

  static setProperties(state: State, layerID: string, properties: Partial<LayerModel>) {
    return produce(state, (draft) => {
      const layer: any = draft.scene.layers[layerID];
      if (!layer) return;

      Object.assign(layer, properties);

      const sortedLayers = Object.values(draft.scene.layers).sort((a: any, b: any) =>
        a.altitude !== b.altitude ? a.altitude - b.altitude : a.order - b.order
      );

      draft.scene.layers = sortedLayers.reduce(
        (acc: any, l: any) => ({ ...acc, [l.id]: l }),
        {}
      );
    });
  }

  static remove(state: State, layerID: string) {
    return produce(state, (draft) => {
      delete (draft.scene.layers as any)[layerID];
      if (draft.scene.selectedLayer === layerID) {
        const newSelectedLayer = Object.keys(draft.scene.layers)[0];
        draft.scene.selectedLayer = newSelectedLayer;
      }
    });
  }

  static removeElement(
    state: State,
    layerID: string,
    elementPrototype: ElementPrototypes,
    elementID: string
  ) {
    return produce(state, (draft) => {
      const layer: any = draft.scene.layers[layerID];
      if (layer && layer[elementPrototype]) {
        delete layer[elementPrototype][elementID];
      }
    });
  }

  static detectAndUpdateAreas(state: State, layerID: string) {
    const layer0: any = state.scene.layers[layerID];
    if (!layer0) return state;

    const verticesArray: Array<[number, number]> = [];
    const vertexID_to_verticesArrayIndex: Record<string, number> = {};
    const verticesArrayIndex_to_vertexID: Record<number, string> = {};

    Object.values(layer0.vertices).forEach((vertex: any, i: number) => {
      verticesArray.push([vertex.x, vertex.y]);
      vertexID_to_verticesArrayIndex[vertex.id] = i;
      verticesArrayIndex_to_vertexID[i] = vertex.id;
    });

    const linesArray = Object.values(layer0.lines).map((line: any) =>
      line.vertices.map((vertexID: string) => vertexID_to_verticesArrayIndex[vertexID])
    );

    const innerCyclesByVerticesID1 = GraphInnerCycles.calculateInnerCycles(verticesArray, linesArray);
    const innerCyclesByVerticesID2 = innerCyclesByVerticesID1.map((cycle: any) =>
      cycle.map((vertexIndex: number) => verticesArrayIndex_to_vertexID[vertexIndex])
    );

    const innerCyclesByVerticesID = innerCyclesByVerticesID2.map((area: any) =>
      GraphInnerCycles.isClockWiseOrder(
        area.map((vertexID: string) => layer0.vertices[vertexID])
      )
        ? area.reverse()
        : area
    );

    Object.values((state.scene.layers as any)[layerID].areas).forEach((area: any) => {
      if (
        !innerCyclesByVerticesID.some((vertices: any) =>
          sameSet(new Set(vertices), new Set(area.vertices))
        )
      ) {
        state = Area.remove(state, layerID, area.id);
      }
    });

    let layer: any = (state.scene.layers as any)[layerID];
    const areaIDs: string[] = [];
    const areasToReset: string[] = [];

    innerCyclesByVerticesID.forEach((cycle: any, ind: number) => {
      const areaInUse = Object.values(layer.areas).find((area: any) =>
        sameSet(new Set(area.vertices), new Set(cycle))
      );

      if (areaInUse) {
        areaIDs[ind] = (areaInUse as any).id;
        areasToReset.push((areaInUse as any).id);
      } else {
        const areaVerticesCoords = cycle.map((vertexID: string) => {
          const vertex = layer.vertices[vertexID];
          return { x: vertex.x, y: vertex.y };
        });

        const resultAdd: any = Area.add(state, layerID, 'area', areaVerticesCoords, (state as any).catalog);
        areaIDs[ind] = resultAdd.area.id;
        state = resultAdd.updatedState;
        layer = (state.scene.layers as any)[layerID];
      }
    });

    state = produce(state, (draft) => {
      const lay: any = draft.scene.layers[layerID];

      areasToReset.forEach((id) => {
        if (lay.areas[id]) lay.areas[id].holes = [];
      });

      const verticesCoordsForArea = areaIDs.map((id) => {
        const area = lay.areas[id];
        const vertices = area.vertices.map((vertexID: string) => {
          const { x, y } = lay.vertices[vertexID];
          return [x, y] as [number, number];
        });
        return { id, vertices };
      });

      verticesCoordsForArea.forEach((area1) => {
        const holesList: string[] = [];
        verticesCoordsForArea.forEach((area2) => {
          if (area1.id !== area2.id) {
            if (
              GeometryUtils.ContainsPoint(
                area1.vertices.flat(),
                area2.vertices[0][0],
                area2.vertices[0][1]
              )
            ) {
              holesList.push(area2.id);
            }
          }
        });
        lay.areas[area1.id].holes = holesList;
      });

      areaIDs.forEach((areaID) => {
        const doubleHoles = new Set<string>();
        const areaHoles = lay.areas[areaID].holes;
        areaHoles.forEach((areaHoleID: string) => {
          const holesOfholes = lay.areas[areaHoleID].holes;
          holesOfholes.forEach((holeID: string) => {
            if (areaHoles.indexOf(holeID) !== -1) {
              doubleHoles.add(holeID);
            }
          });
        });

        if (doubleHoles.size) {
          lay.areas[areaID].holes = areaHoles.filter((holeID: string) => !doubleHoles.has(holeID));
        }
      });
    });

    return state;
  }

  static removeZeroLengthLines(state: State, layerID: string) {
    return produce(state, (draft) => {
      const layer: any = draft.scene.layers[layerID];
      if (!layer) return;
      Object.values(layer.lines).forEach((line: any) => {
        const v0 = layer.vertices[line.vertices[0]];
        const v1 = layer.vertices[line.vertices[1]];
        if (GeometryUtils.verticesDistance(v0, v1) === 0) {
          delete layer.lines[line.id];
        }
      });
    });
  }

  static mergeEqualsVertices(state: State, layerID: string, vertexID: string) {
    const layer: any = state.scene.layers[layerID];
    if (!layer) return state;
    const vertex = layer.vertices[vertexID];
    if (!vertex) return state;

    const doubleVertices = Object.values(layer.vertices).filter(
      (v: any) => v.id !== vertexID && GeometryUtils.samePoints(vertex, v)
    );

    doubleVertices.forEach((doubleVertex: any) => {
      doubleVertex.lines.forEach((lineID: string) => {
        const line = layer.lines[lineID];
        if (line) {
          state = produce(state, (draft) => {
            (draft.scene.layers as any)[layerID].lines[lineID].vertices =
              line.vertices.map((v: string) => (v === doubleVertex.id ? vertexID : v)) as [string, string];
          });
          state = Vertex.addElement(state, layerID, vertexID, 'lines', lineID);
        }
      });

      doubleVertex.areas.forEach((areaID: string) => {
        const area = layer.areas[areaID];
        if (area) {
          state = produce(state, (draft) => {
            (draft.scene.layers as any)[layerID].areas[areaID].vertices =
              area.vertices.map((v: string) => (v === doubleVertex.id ? vertexID : v)) as any;
          });
          state = Vertex.addElement(state, layerID, vertexID, 'areas', areaID);
        }
      });

      state = Vertex.remove(state, layerID, doubleVertex.id, null as any, null as any, true);
    });

    return state;
  }

  static setPropertiesOnSelected(state: State, layerID: string, properties: Record<string, any>) {
    return produce(state, (draft) => {
      const selected: any = (draft.scene.layers as any)[layerID].selected;

      selected.lines.forEach((lineID: string) => (draft = Line.setProperties(draft, layerID, lineID, properties)));
      selected.holes.forEach((holeID: string) => (draft = Hole.setProperties(draft, layerID, holeID, properties)));
      selected.areas.forEach((areaID: string) => (draft = Area.setProperties(draft, layerID, areaID, properties)));
      selected.items.forEach((itemID: string) => (draft = Item.setProperties(draft, layerID, itemID, properties)));

      return draft;
    });
  }

  static updatePropertiesOnSelected(state: State, layerID: string, properties: Record<string, any>) {
    return produce(state, (draft) => {
      const selected: any = (draft.scene.layers as any)[layerID].selected;

      selected.lines.forEach((lineID: string) => (draft = Line.updateProperties(draft, layerID, lineID, properties)));
      selected.holes.forEach((holeID: string) => (draft = Hole.updateProperties(draft, layerID, holeID, properties)));
      selected.areas.forEach((areaID: string) => (draft = Area.updateProperties(draft, layerID, areaID, properties)));
      selected.items.forEach((itemID: string) => (draft = Item.updateProperties(draft, layerID, itemID, properties)));

      return draft;
    });
  }

  /**
   * PlanO FIX:
   * - Do NOT call Line.setAttributes inside an Immer producer (it returns a new state).
   * - Apply setAttributes sequentially outside produce.
   * - Fallback to element.selected flags when selection lists are empty (common for converted scenes).
   */
  static setAttributesOnSelected(state: State, layerID: string, attributes: any) {
    const layer: any = (state.scene.layers as any)[layerID];
    if (!layer) return state;

    const selected: any = layer.selected;
    const listCount =
      (selected?.lines?.length || 0) +
      (selected?.holes?.length || 0) +
      (selected?.items?.length || 0) +
      (selected?.areas?.length || 0);

    const useFallback = listCount === 0;

    // 1) Apply to selected lists (normal behavior)
    if (!useFallback) {
      (selected.lines || []).forEach((lineID: string) => {
        state = Line.setAttributes(state, layerID, lineID, attributes);
      });
      (selected.holes || []).forEach((holeID: string) => {
        state = Hole.setAttributes(state, layerID, holeID, attributes);
      });
      (selected.items || []).forEach((itemID: string) => {
        state = Item.setAttributes(state, layerID, itemID, attributes);
      });
      (selected.areas || []).forEach((areaID: string) => {
        state = Area.setAttributes(state, layerID, areaID, attributes);
      });

      // If vertices moved, update areas
      if (attributes?.vertexOne || attributes?.vertexTwo) {
        state = Layer.detectAndUpdateAreas(state, layerID);
      }
      return state;
    }

    // 2) Fallback: apply to elements with .selected === true
    const hasVertexEdit = !!(attributes?.vertexOne || attributes?.vertexTwo);

    // If we are editing vertices, update them directly (works even when vertices are shared)
    if (hasVertexEdit) {
      state = produce(state, (draft) => {
        const lay: any = (draft.scene.layers as any)[layerID];
        if (!lay) return;

        for (const line of Object.values(lay.lines || {}) as any[]) {
          if (!line?.selected) continue;

          if (attributes?.vertexOne && Array.isArray(line.vertices) && line.vertices[0]) {
            const v = lay.vertices?.[line.vertices[0]];
            if (v) {
              if (attributes.vertexOne.x !== undefined) v.x = attributes.vertexOne.x;
              if (attributes.vertexOne.y !== undefined) v.y = attributes.vertexOne.y;
            }
          }
          if (attributes?.vertexTwo && Array.isArray(line.vertices) && line.vertices[1]) {
            const v = lay.vertices?.[line.vertices[1]];
            if (v) {
              if (attributes.vertexTwo.x !== undefined) v.x = attributes.vertexTwo.x;
              if (attributes.vertexTwo.y !== undefined) v.y = attributes.vertexTwo.y;
            }
          }
        }
      });
    }

    // Then apply line/hole/item/area attributes through their normal setters
    const lay2: any = (state.scene.layers as any)[layerID];

    for (const line of Object.values(lay2.lines || {}) as any[]) {
      if (line?.selected) state = Line.setAttributes(state, layerID, line.id, attributes);
    }
    for (const hole of Object.values(lay2.holes || {}) as any[]) {
      if (hole?.selected) state = Hole.setAttributes(state, layerID, hole.id, attributes);
    }
    for (const item of Object.values(lay2.items || {}) as any[]) {
      if (item?.selected) state = Item.setAttributes(state, layerID, item.id, attributes);
    }
    for (const area of Object.values(lay2.areas || {}) as any[]) {
      if (area?.selected) state = Area.setAttributes(state, layerID, area.id, attributes);
    }

    if (hasVertexEdit) {
      state = Layer.detectAndUpdateAreas(state, layerID);
    }

    return state;
  }
}

export { Layer as default };
