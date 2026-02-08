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

// ------- Protocol (must match PlanO PlannerFrame.tsx) -------
const PROTOCOL_VERSION = 1;

// ------- Import action creators + constants from local source -------
import * as constants from '../../src/constants';
import { normalizeSceneFromRaster } from '../../src/utils/scene-normalizer';

import * as projectActions from '../../src/actions/project-actions';
import * as viewer2DActions from '../../src/actions/viewer2d-actions';
import * as viewer3DActions from '../../src/actions/viewer3d-actions';
import * as linesActions from '../../src/actions/lines-actions';
import * as holesActions from '../../src/actions/holes-actions';
import * as itemsActions from '../../src/actions/items-actions';

//define state
const AppState = {
  'react-planner': PlannerModels.State()
};

//define reducer
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

// ---- helpers to talk to parent (PlanO) ----
function postToParent(msg: any) {
  try {
    // targetOrigin '*' is OK; parent verifies origin is http://localhost:5173
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

// Component that uses useMeasure hook
function ResponsiveReactPlanner() {
  const [ref, bounds] = useMeasure();
  const catalog = createCatalog();

  useEffect(() => {
    // Send initial mode to PlanO as soon as possible
    const st: any = store.getState()['react-planner'];
    if (st?.mode) emitModeChanged(String(st.mode));

    // Subscribe to mode changes
    let lastMode = st?.mode;
    const unsubscribe = store.subscribe(() => {
      const cur: any = store.getState()['react-planner'];
      const mode = cur?.mode;
      if (mode && mode !== lastMode) {
        lastMode = mode;
        emitModeChanged(String(mode));
      }
    });

    // Listen for PlanO commands
    const onMessage = (event: MessageEvent) => {
      // PlanO uses '*' targetOrigin, so accept but validate message shape
      const data: any = event.data;
      if (!data || data.protocolVersion !== PROTOCOL_VERSION) return;

      // Basic ping (PlanO sends on iframe load)
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
          // ----- toolbar equivalents -----
          case 'NEW_PROJECT':
            store.dispatch(projectActions.newProject());
            break;

          case 'OPEN_CATALOG':
            store.dispatch(projectActions.openCatalog());
            break;

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

          // ----- 2D tools -----
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

          // ----- loading -----
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

          // ----- export -----
          case 'REQUEST_SCENE_JSON': {
            const st2: any = store.getState()['react-planner'];
            const scene = st2?.scene;
            if (!scene) throw new Error('REQUEST_SCENE_JSON: scene not available');
            emitSceneJson(scene);
            break;
          }

          default:
            // Unknown command: ignore but report to parent
            emitError(`Unknown CMD: ${cmd}`);
            break;
        }

        // After any command, inform parent of current mode (helps keep UI in sync)
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
          // Keep toolbarButtons empty; PlanO is the toolbar.
          toolbarButtons={[]}
          stateExtractor={(state) => state['react-planner']}
        />
      )}
    </div>
  );
}

//render
const container = document.getElementById('app');
if (!container) {
  throw new Error('Container element not found');
}

// Reuse a single React root across HMR updates
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
