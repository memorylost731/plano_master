import { Store } from 'redux';

import {
  loadProject,
  newProject,
  openCatalog,
  openProjectConfigurator,
  selectToolEdit,
  undo,
  unselectAll
} from '../actions/project-actions';
import {
  selectTool3DFirstPerson,
  selectTool3DView
} from '../actions/viewer3d-actions';
import {
  selectToolPan,
  selectToolZoomIn,
  selectToolZoomOut
} from '../actions/viewer2d-actions';
import { State } from '../models';

const PROTOCOL_VERSION = 1;

interface BridgeMessage {
  protocolVersion: number;
  type: string;
  cmd?: string;
  payload?: any;
}

function reply(event: MessageEvent, msg: Omit<BridgeMessage, 'protocolVersion'>) {
  const origin = event.origin || '*';
  window.parent.postMessage({ protocolVersion: PROTOCOL_VERSION, ...msg }, origin);
}

export default function postMessageBridge() {
  return (store: Store, stateExtractor: (state: any) => State) => {
    // Track mode changes and notify parent
    let prevMode: string = stateExtractor(store.getState()).mode;

    store.subscribe(() => {
      const newMode = stateExtractor(store.getState()).mode;
      if (newMode !== prevMode) {
        prevMode = newMode;
        window.parent.postMessage(
          { protocolVersion: PROTOCOL_VERSION, type: 'MODE_CHANGED', payload: { mode: newMode } },
          '*'
        );
      }
    });

    // Listen for commands from PlanO UI
    window.addEventListener('message', (event: MessageEvent) => {
      const data = event.data as BridgeMessage;
      if (!data || data.protocolVersion !== PROTOCOL_VERSION) return;

      if (data.type === 'PING') {
        reply(event, { type: 'PONG' });
        return;
      }

      if (data.type !== 'CMD' || !data.cmd) return;

      try {
        switch (data.cmd) {
          case 'NEW_PROJECT':
            store.dispatch(newProject());
            break;
          case 'OPEN_CATALOG':
            store.dispatch(openCatalog());
            break;
          case 'VIEW_2D':
          case 'SELECT_TOOL_EDIT':
            store.dispatch(selectToolEdit());
            break;
          case 'VIEW_3D':
            store.dispatch(selectTool3DView());
            break;
          case 'VIEW_3D_FIRST_PERSON':
            store.dispatch(selectTool3DFirstPerson());
            break;
          case 'UNDO':
            store.dispatch(undo());
            break;
          case 'OPEN_PROJECT_CONFIGURATOR':
            store.dispatch(openProjectConfigurator());
            break;
          case 'UNSELECT_ALL':
            store.dispatch(unselectAll());
            break;
          case 'TOOL_PAN':
            store.dispatch(selectToolPan());
            break;
          case 'TOOL_ZOOM_IN':
            store.dispatch(selectToolZoomIn());
            break;
          case 'TOOL_ZOOM_OUT':
            store.dispatch(selectToolZoomOut());
            break;
          case 'LOAD_PROJECT_JSON':
            if (data.payload?.scene) {
              store.dispatch(loadProject(data.payload.scene));
            }
            break;
          case 'LOAD_RASTER_JSON':
            // Rasta returns a react-planner scene JSON directly
            if (data.payload?.raw) {
              store.dispatch(loadProject(data.payload.raw));
            }
            break;
          case 'REQUEST_SCENE_JSON': {
            const scene = stateExtractor(store.getState()).scene;
            reply(event, { type: 'SCENE_JSON', payload: { scene } });
            break;
          }
          default:
            console.warn(`[PostMessageBridge] Unknown command: ${data.cmd}`);
        }
      } catch (err) {
        console.error(`[PostMessageBridge] Error handling ${data.cmd}:`, err);
        reply(event, {
          type: 'ERROR',
          payload: { message: `Failed to execute ${data.cmd}: ${err}` }
        });
      }
    });
  };
}
