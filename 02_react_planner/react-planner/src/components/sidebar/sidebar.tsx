import React from 'react';

import * as constants from '../../constants';
import { State } from '../../models';
import * as SharedStyle from '../../shared-style';
import { ComponentType } from '../../types';

import PanelElementEditor from './panel-element-editor/panel-element-editor';
import PanelMultiElementsEditor from './panel-element-editor/panel-multi-elements-editor';
import PanelGroupEditor from './panel-group-editor';

const TOP_OFFSET_PX = 78;

// smaller width, fixed height
const FIXED_WIDTH_PX = 240;
const FIXED_HEIGHT_PX = 520;

const FLOAT_SIDEBAR_STYLE: React.CSSProperties = {
  position: 'fixed',
  top: TOP_OFFSET_PX,
  right: 12,
  width: FIXED_WIDTH_PX,
  height: FIXED_HEIGHT_PX,
  zIndex: 9999,

  // IMPORTANT: make it OPAQUE so the grid does NOT show through
  background: '#141418',
  border: '1px solid rgba(255,255,255,0.14)',
  borderRadius: 14,

  // tight shadow (no grey slab)
  boxShadow: '0 10px 26px rgba(0,0,0,0.38)',

  // fixed panel (scroll inside)
  overflow: 'hidden'
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

function EmptyState() {
  return (
    <div style={{ padding: '12px 14px', color: 'rgba(255,255,255,0.9)', fontSize: 13 }}>
      <div style={{ fontWeight: 800, marginBottom: 6 }}>PlanO</div>
      <div style={{ opacity: 0.85, lineHeight: 1.35 }}>
        Select a wall / area / item to edit properties.
      </div>
    </div>
  );
}

export default function Sidebar({ state }: SidebarProps) {
  // ONLY CHANGE: hide the right specs box while Catalog is open.
  if (state.mode === constants.MODE_VIEWING_CATALOG) return null;

  const selectedLayer = state.scene.selectedLayer;

  // Always show the box even if nothing is selected or no layer exists.
  if (!selectedLayer || !state.scene.layers[selectedLayer]) {
    return (
      <aside
        style={{ ...STYLE, ...FLOAT_SIDEBAR_STYLE }}
        onKeyDown={(event) => event.stopPropagation()}
        onKeyUp={(event) => event.stopPropagation()}
        className="sidebar sidebar--floating"
      >
        <EmptyState />
      </aside>
    );
  }

  const layer = state.scene.layers[selectedLayer];
  const selected = layer.selected;

  const selectedCount =
    selected.lines.length +
    selected.holes.length +
    selected.items.length +
    selected.areas.length;

  const multiselected =
    selected.lines.length > 1 ||
    selected.items.length > 1 ||
    selected.holes.length > 1 ||
    selected.areas.length > 1 ||
    selectedCount > 1;

  const selectedGroup = Object.values(state.scene.groups).find((g) => g.selected);

  const showEmpty = selectedCount === 0 && !selectedGroup;

  return (
    <aside
      style={{ ...STYLE, ...FLOAT_SIDEBAR_STYLE }}
      onKeyDown={(event) => event.stopPropagation()}
      onKeyUp={(event) => event.stopPropagation()}
      className="sidebar sidebar--floating"
    >
      {showEmpty ? (
        <EmptyState />
      ) : (
        <>
          {!multiselected && <PanelElementEditor state={state} />}
          {multiselected && <PanelMultiElementsEditor state={state} />}
          {!!selectedGroup && <PanelGroupEditor state={state} groupID={selectedGroup.id} />}
        </>
      )}
    </aside>
  );
}
