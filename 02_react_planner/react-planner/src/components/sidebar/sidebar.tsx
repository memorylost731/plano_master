import React from 'react';

import {
  MODE_VIEWING_CATALOG,
  MODE_3D_VIEW,
  MODE_3D_FIRST_PERSON
} from '../../constants';
import { State } from '../../models';
import * as SharedStyle from '../../shared-style';
import { ComponentType } from '../../types';

import PanelElementEditor from './panel-element-editor/panel-element-editor';
import PanelMultiElementsEditor from './panel-element-editor/panel-multi-elements-editor';
import PanelGroupEditor from './panel-group-editor';

const FLOAT_SIDEBAR_STYLE: React.CSSProperties = {
  position: 'fixed',
  top: 72,
  right: 12,
  width: 220,
  maxHeight: 320,
  overflow: 'auto',
  zIndex: 9999,
  background: '#1f1f1f',
  borderRadius: 10,
  boxShadow: '0 10px 30px rgba(0,0,0,0.35)'
};

const STYLE = {
  backgroundColor: SharedStyle.PRIMARY_COLOR.main,
  display: 'block',
  overflowY: 'auto',
  overflowX: 'hidden',
  paddingBottom: '12px'
} as const;

interface SidebarProps {
  state: State;
  width: number;
  height: number;
  sidebarComponents: ComponentType[];
}

export default function Sidebar({ state, width, height }: SidebarProps) {
  if (
    state.mode === MODE_VIEWING_CATALOG ||
    state.mode === MODE_3D_VIEW ||
    state.mode === MODE_3D_FIRST_PERSON
  ) {
    return null;
  }

  const selectedLayer = state.scene.selectedLayer;
  if (!selectedLayer) return null;

  const selected = state.scene.layers[selectedLayer].selected;

  const multiselected =
    selected.lines.length > 1 ||
    selected.items.length > 1 ||
    selected.holes.length > 1 ||
    selected.areas.length > 1 ||
    selected.lines.length +
      selected.items.length +
      selected.holes.length +
      selected.areas.length >
      1;

  const selectedGroup = Object.values(state.scene.groups).find((g) => g.selected);

  return (
    <aside
      style={{ width, height, ...STYLE, ...FLOAT_SIDEBAR_STYLE }}
      onKeyDown={(event) => event.stopPropagation()}
      onKeyUp={(event) => event.stopPropagation()}
      className="sidebar sidebar--floating"
    >
      {!multiselected && <PanelElementEditor state={state} />}
      {multiselected && <PanelMultiElementsEditor state={state} />}

      {!!selectedGroup && <PanelGroupEditor state={state} groupID={selectedGroup.id} />}
    </aside>
  );
}