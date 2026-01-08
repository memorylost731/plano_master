import React from 'react';

import { State } from '../../models';
import * as SharedStyle from '../../shared-style';
import { ComponentType } from '../../types';

import PanelElementEditor from './panel-element-editor/panel-element-editor';
import PanelMultiElementsEditor from './panel-element-editor/panel-multi-elements-editor';
import PanelGroupEditor from './panel-group-editor';

/**
 * PlanO placement:
 * - top-right corner
 * - below PlanO header (header is in parent app overlay)
 * Adjust TOP_OFFSET_PX if your header height changes.
 */
const TOP_OFFSET_PX = 78;

const FIXED_WIDTH_PX = 300;
const FIXED_HEIGHT_PX = 520;

const FLOAT_SIDEBAR_STYLE: React.CSSProperties = {
  position: 'fixed',
  top: TOP_OFFSET_PX,
  right: 12,
  width: FIXED_WIDTH_PX,
  height: FIXED_HEIGHT_PX,
  overflow: 'auto',
  zIndex: 9999,

  // PlanO glass style
  background: 'rgba(20, 20, 24, 0.62)',
  backdropFilter: 'blur(24px) saturate(140%)',
  WebkitBackdropFilter: 'blur(24px) saturate(140%)',
  border: '1px solid rgba(255,255,255,0.14)',
  borderRadius: 14,
  boxShadow: '0 18px 50px rgba(0,0,0,0.45)'
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
  sidebarComponents: ComponentType[]; // kept for API compatibility; not used
}

export default function Sidebar({ state }: SidebarProps) {
  const selectedLayer = state.scene.selectedLayer;
  if (!selectedLayer) return null;

  const selected = state.scene.layers[selectedLayer].selected;

  const multiselected =
    selected.lines.length > 1 ||
    selected.items.length > 1 ||
    selected.holes.length > 1 ||
    selected.areas.length > 1 ||
    selected.lines.length + selected.items.length + selected.holes.length + selected.areas.length > 1;

  const selectedGroup = Object.values(state.scene.groups).find((g) => g.selected);

  return (
    <aside
      style={{ ...STYLE, ...FLOAT_SIDEBAR_STYLE }}
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
