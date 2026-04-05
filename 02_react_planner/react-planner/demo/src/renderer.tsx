import React, { useEffect } from 'react';

import {
  Models as PlannerModels,
  Plugins as PlannerPlugins,
  reducer as PlannerReducer,
  ReactPlanner
} from '@archef2000/react-planner';
import { configureStore } from '@reduxjs/toolkit';
import { produce } from 'immer';
import { createRoot } from 'react-dom/client';
import { Provider } from 'react-redux';
import useMeasure from 'react-use-measure';

import { createCatalog } from './catalog_custom/mycatalog';

/**
 * We wire PlanO UI -> React-Planner engine via postMessage.
 * PlanO sends messages from:
 * /00_frontend_skeleton/plano-ui/src/components/planner/PlannerFrame.tsx
 *
 * This engine:
 * - listens for CMD messages
 * - dispatches the same Redux actions that the React-Planner toolbar would call
 * - reports MODE_CHANGED + SCENE_JSON back to the parent
 */

const PROTOCOL_VERSION = 1;

import * as constants from '../../src/constants';
import { normalizeSceneFromRaster } from '../../src/utils/scene-normalizer';

import * as projectActions from '../../src/actions/project-actions';
import * as viewer2DActions from '../../src/actions/viewer2d-actions';
import * as viewer3DActions from '../../src/actions/viewer3d-actions';
import * as linesActions from '../../src/actions/lines-actions';
import * as holesActions from '../../src/actions/holes-actions';
import * as itemsActions from '../../src/actions/items-actions';

const AppState = {
  'react-planner': PlannerModels.State()
};

const reducer = (state: { [key: string]: any } | undefined, action: any) => {
  state = state || AppState;
  state = produce(state, (draft) => {
    draft['react-planner'] = PlannerReducer(draft['react-planner'], action);
  });
  return state;
};

const store = configureStore({
  reducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      thunk: true,
      immutableCheck: true,
      serializableCheck: false,
      actionCreatorCheck: true
    }).concat()
});

const plugins = [PlannerPlugins.Keyboard(), PlannerPlugins.ConsoleDebugger()];

function postToParent(msg: any) {
  try {
    window.parent?.postMessage(msg, '*');
  } catch (e: any) {
    // ignore
  }
}

function emitModeChanged(mode: string) {
  postToParent({
    protocolVersion: PROTOCOL_VERSION,
    type: 'MODE_CHANGED',
    payload: { mode }
  });
}

function emitError(message: string) {
  postToParent({
    protocolVersion: PROTOCOL_VERSION,
    type: 'ERROR',
    message
  });
}

function emitSceneJson(scene: any) {
  postToParent({
    protocolVersion: PROTOCOL_VERSION,
    type: 'SCENE_JSON',
    payload: { scene }
  });
}

function ResponsiveReactPlanner() {
  const [ref, bounds] = useMeasure();
  const catalog = createCatalog();

  useEffect(() => {
    const st: any = store.getState()['react-planner'];
    if (st?.mode) emitModeChanged(String(st.mode));

    let lastMode = st?.mode;
    const unsubscribe = store.subscribe(() => {
      const cur: any = store.getState()['react-planner'];
      const mode = cur?.mode;
      if (mode && mode !== lastMode) {
        lastMode = mode;
        emitModeChanged(String(mode));
      }
    });

    const onMessage = (event: MessageEvent) => {
      const data: any = event.data;
      if (!data || data.protocolVersion !== PROTOCOL_VERSION) return;

      if (data.type === 'PING') {
        const cur: any = store.getState()['react-planner'];
        if (cur?.mode) emitModeChanged(String(cur.mode));
        return;
      }

      if (data.type !== 'CMD') return;

      const cmd: string = data.cmd;
      const payload: any = data.payload || {};

      try {
        const planner: any = store.getState()['react-planner'];

        switch (cmd) {
          case 'NEW_PROJECT':
            store.dispatch(projectActions.newProject());
            break;

          case 'OPEN_CATALOG':
            store.dispatch(projectActions.openCatalog());
            break;

          case 'CHANGE_CATALOG_PAGE': {
            const newPage = payload?.newPage;
            const oldPage = payload?.oldPage ?? 'root';
            if (!newPage) throw new Error('CHANGE_CATALOG_PAGE: missing payload.newPage');
            store.dispatch(projectActions.changeCatalogPage(newPage, oldPage));
            break;
          }

          case 'VIEW_2D':
            store.dispatch(projectActions.setMode(constants.MODE_IDLE));
            break;

          case 'VIEW_3D':
            store.dispatch(viewer3DActions.selectTool3DView());
            break;

          case 'VIEW_3D_FIRST_PERSON':
            store.dispatch(viewer3DActions.selectTool3DFirstPerson());
            break;

          case 'UNDO':
            store.dispatch(projectActions.undo());
            break;

          case 'OPEN_PROJECT_CONFIGURATOR':
            store.dispatch(projectActions.openProjectConfigurator());
            break;

          case 'TOOL_PAN':
            store.dispatch(viewer2DActions.selectToolPan());
            break;

          case 'TOOL_ZOOM_IN':
            store.dispatch(viewer2DActions.selectToolZoomIn());
            break;

          case 'TOOL_ZOOM_OUT':
            store.dispatch(viewer2DActions.selectToolZoomOut());
            break;

          case 'SELECT_TOOL_EDIT':
            store.dispatch(projectActions.selectToolEdit());
            break;

          case 'UNSELECT_ALL':
            store.dispatch(projectActions.unselectAll());
            break;

          case 'LOAD_PROJECT_JSON': {
            const scene = payload?.scene;
            if (!scene) throw new Error('LOAD_PROJECT_JSON: missing payload.scene');
            store.dispatch(projectActions.loadProject(scene));
            break;
          }

          case 'LOAD_RASTER_JSON': {
            const raw = payload?.raw;
            if (!raw) throw new Error('LOAD_RASTER_JSON: missing payload.raw');
            const scene = normalizeSceneFromRaster(raw);
            store.dispatch(projectActions.loadProject(scene));
            break;
          }

          case 'REQUEST_SCENE_JSON': {
            const st2: any = store.getState()['react-planner'];
            const scene = st2?.scene;
            if (!scene) throw new Error('REQUEST_SCENE_JSON: scene not available');
            emitSceneJson(scene);
            break;
          }

          case 'RESTORE_SURFACE_HIGHLIGHTS': {
            const surfaceIds = payload?.surfaceIds || [];

            window.dispatchEvent(
              new CustomEvent('PLANO_RESTORE_HIGHLIGHTS', {
                detail: { surfaceIds }
              })
            );

            break;
          }

          case 'APPLY_SURFACE_COLORS': {
            const surfaces = payload?.surfaces || {};

            window.dispatchEvent(
              new CustomEvent('PLANO_APPLY_SURFACE_COLORS', {
                detail: { surfaces }
              })
            );

            break;
          }

          default:
            emitError(`Unknown CMD: ${cmd}`);
            break;
        }

        const after: any = store.getState()['react-planner'];
        if (after?.mode) emitModeChanged(String(after.mode));
      } catch (e: any) {
        emitError(e?.message || String(e));
      }
    };

    window.addEventListener('message', onMessage);
    return () => {
      window.removeEventListener('message', onMessage);
      unsubscribe();
    };
  }, []);

  return (
    <div ref={ref} style={{ width: '100%', height: '100%' }}>
      {bounds.width > 0 && bounds.height > 0 && (
        <ReactPlanner
          catalog={catalog}
          width={bounds.width}
          height={bounds.height}
          plugins={plugins}
          toolbarButtons={[]}
          stateExtractor={(state) => state['react-planner']}
        />
      )}
    </div>
  );
}

const container = document.getElementById('app');
if (!container) {
  throw new Error('Container element not found');
}

const globalAny = globalThis as any;
const ROOT_KEY = '__REACT_PLANNER_DEMO_ROOT__';
const root =
  globalAny[ROOT_KEY] || (globalAny[ROOT_KEY] = createRoot(container));

root.render(
  <Provider store={store}>
    <ResponsiveReactPlanner />
  </Provider>
);

if ((module as any)?.hot) {
  try {
    (module as any).hot.dispose(() => {
      root.unmount();
      delete globalAny[ROOT_KEY];
    });
  } catch {}
}