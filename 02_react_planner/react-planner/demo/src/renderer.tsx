import React, { useEffect, useMemo } from 'react';

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
import ToolbarScreenshotButton from './ui/toolbar-screenshot-button';

// Normalize RasterScan output -> React-Planner scene
import { normalizeSceneFromRaster } from '../../src/utils/scene-normalizer';

// =====================
// Store setup
// =====================

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
const toolbarButtons = [ToolbarScreenshotButton];

// =====================
// PlanO <-> Engine bridge
// =====================

const PROTOCOL_VERSION = 1;

const ALLOWED_PARENT_ORIGINS = new Set([
  'http://localhost:5174',
  'http://localhost:5175',
  'http://localhost:5173'
]);

type EngineMsg =
  | { protocolVersion: number; type: 'PING' }
  | { protocolVersion: number; type: 'CMD'; cmd: string; payload?: any };

function postToParent(msg: any) {
  window.parent?.postMessage(msg, '*');
}

function getPlannerState() {
  const s: any = store.getState();
  return s?.['react-planner'];
}

function dispatchAction(action: any) {
  store.dispatch(action);
}

function handleCmd(cmd: string, payload?: any) {
  switch (cmd) {
    case 'NEW_PROJECT':
      dispatchAction({ type: 'NEW_PROJECT' });
      return;

    case 'OPEN_CATALOG':
      dispatchAction({ type: 'OPEN_CATALOG' });
      return;

    case 'VIEW_2D':
      dispatchAction({ type: 'SET_MODE', mode: 'MODE_IDLE' });
      return;

    case 'SELECT_TOOL_EDIT':
      dispatchAction({ type: 'SELECT_TOOL_EDIT' });
      return;

    case 'VIEW_3D':
      dispatchAction({ type: 'SELECT_TOOL_3D_VIEW' });
      return;

    case 'VIEW_3D_FIRST_PERSON':
      dispatchAction({ type: 'SELECT_TOOL_3D_FIRST_PERSON' });
      return;

    case 'UNDO':
      dispatchAction({ type: 'UNDO' });
      return;

    case 'OPEN_PROJECT_CONFIGURATOR':
      dispatchAction({ type: 'OPEN_PROJECT_CONFIGURATOR' });
      return;

    case 'TOOL_PAN':
      dispatchAction({ type: 'SELECT_TOOL_PAN' });
      return;

    case 'TOOL_ZOOM_IN':
      dispatchAction({ type: 'SELECT_TOOL_ZOOM_IN' });
      return;

    case 'TOOL_ZOOM_OUT':
      dispatchAction({ type: 'SELECT_TOOL_ZOOM_OUT' });
      return;

    case 'UNSELECT_ALL':
      dispatchAction({ type: 'UNSELECT_ALL' });
      return;

    case 'LOAD_PROJECT_JSON': {
      const scene = payload?.scene;
      if (!scene) return;
      dispatchAction({ type: 'LOAD_PROJECT', sceneJSON: scene });
      return;
    }

    case 'LOAD_RASTER_JSON': {
      const raw = payload?.raw;
      if (!raw) return;
      const scene = normalizeSceneFromRaster(raw);
      dispatchAction({ type: 'LOAD_PROJECT', sceneJSON: scene });
      return;
    }

    case 'REQUEST_SCENE_JSON': {
      const planner = getPlannerState();
      const scene = planner?.scene;
      if (!scene) return;

      postToParent({
        protocolVersion: PROTOCOL_VERSION,
        type: 'SCENE_JSON',
        payload: { scene }
      });
      return;
    }

    default:
      return;
  }
}

function usePlanOMessageBridge() {
  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (!ALLOWED_PARENT_ORIGINS.has(event.origin)) return;

      const data = event.data as EngineMsg;
      if (!data || data.protocolVersion !== PROTOCOL_VERSION) return;

      if (data.type === 'PING') return;

      if (data.type === 'CMD') {
        handleCmd(data.cmd, data.payload);
      }
    };

    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, []);
}

function ResponsiveReactPlanner() {
  usePlanOMessageBridge();

  const [ref, bounds] = useMeasure();
  const catalog = useMemo(() => createCatalog(), []);

  return (
    <div ref={ref} style={{ width: '100%', height: '100%' }}>
      {bounds.width > 0 && bounds.height > 0 && (
        <ReactPlanner
          catalog={catalog}
          width={bounds.width}
          height={bounds.height}
          plugins={plugins}
          toolbarButtons={toolbarButtons}
          stateExtractor={(state) => (state as any)['react-planner']}
        />
      )}
    </div>
  );
}

const container = document.getElementById('app');
if (!container) throw new Error('Container element not found');

const globalAny = globalThis as any;
const ROOT_KEY = '__REACT_PLANNER_DEMO_ROOT__';
const root = globalAny[ROOT_KEY] || (globalAny[ROOT_KEY] = createRoot(container));

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
