import React from 'react';

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

const plugins = [
  PlannerPlugins.Keyboard(),
  PlannerPlugins.ConsoleDebugger(),
  PlannerPlugins.PostMessageBridge()
];

const toolbarButtons = [ToolbarScreenshotButton];

// Component that uses useMeasure hook
function ResponsiveReactPlanner() {
  const [ref, bounds] = useMeasure();

  const catalog = createCatalog();

  return (
    <div ref={ref} style={{ width: '100%', height: '100%' }}>
      {bounds.width > 0 && bounds.height > 0 && (
        <ReactPlanner
          catalog={catalog}
          width={bounds.width}
          height={bounds.height}
          plugins={plugins}
          toolbarButtons={toolbarButtons}
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
