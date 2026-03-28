import React, { useContext } from 'react';
import { normalizeSceneFromRaster } from '../../utils/scene-normalizer';

import { FaFolderOpen as IconLoad } from 'react-icons/fa';

import { State } from '../../models';
import ReactPlannerContext from '../../react-planner-context';

import ToolbarButton from './toolbar-button';

interface ToolbarLoadButtonProps {
  state: State;
}

export default function ToolbarLoadButton({ state }: ToolbarLoadButtonProps) {
  const { projectActions, translator } = useContext(ReactPlannerContext);

  const loadProjectFromFile = async (
    event: React.MouseEvent<HTMLDivElement>
  ) => {
    event.preventDefault();

    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,application/json,.png,.jpg,.jpeg,application/pdf';

    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;

      try {
        /* ===============================
           CASE 1: JSON (classic project)
           =============================== */
        if (file.name.toLowerCase().endsWith('.json')) {
          const text = await file.text();
          projectActions.loadProject(JSON.parse(text));
          return;
        }

        /* =====================================
           CASE 2: PDF / PNG / JPG → RasterScan
           ===================================== */
        const form = new FormData();
        form.append('file', file);

        // Rasta API: use relative path for production, env var for dev
        const rastaUrl = (window as any).__PLANO_RASTA_URL__
          || (window.location.hostname === 'hacking.eu' ? '/plano-api' : 'http://localhost:8011');
        const resp = await fetch(`${rastaUrl}/upload-plan`, {
          method: 'POST',
          body: form
        });

        if (!resp.ok) {
          const msg = await resp.text();
          throw new Error(`Raster pipeline failed (${resp.status}): ${msg}`);
        }

        const rawScene = await resp.json();
        const scene = normalizeSceneFromRaster(rawScene);
        projectActions.loadProject(scene);

      } catch (e: any) {
        alert(e?.message || String(e));
        console.error(e);
      }
    };

    input.click();
  };

  return (
    <ToolbarButton
      active={false}
      tooltip={translator.t('Load project')}
      onClick={loadProjectFromFile}
    >
      <IconLoad />
    </ToolbarButton>
  );
}
