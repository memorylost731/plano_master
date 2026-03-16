import { useEffect, useRef } from "react";

const ENGINE_URL = import.meta.env.VITE_ENGINE_URL || "http://localhost:5173";
const ENGINE_ORIGIN = new URL(ENGINE_URL).origin;
const PROTOCOL_VERSION = 1;

const RASTER_URL =
  import.meta.env.VITE_RASTER_URL || "http://localhost:8000/upload-plan";

export type PlannerCmd =
  | "NEW_PROJECT"
  | "OPEN_CATALOG"
  | "CHANGE_CATALOG_PAGE"
  | "VIEW_2D"
  | "VIEW_3D"
  | "VIEW_3D_FIRST_PERSON"
  | "UNDO"
  | "OPEN_PROJECT_CONFIGURATOR"
  | "TOOL_PAN"
  | "TOOL_ZOOM_IN"
  | "TOOL_ZOOM_OUT"
  | "SELECT_TOOL_EDIT"
  | "UNSELECT_ALL"
  | "LOAD_PROJECT_JSON"
  | "LOAD_RASTER_JSON"
  | "REQUEST_SCENE_JSON";

export type SurfaceSelectedPayload = {
  surfaceId: string;
  wallId: string;
  surfaceType: "front" | "back" | "floor";
  lengthM?: number;
  heightM?: number;
  areaM2?: number;
};

export type CatalogServiceSelectedPayload = {
  mainService: string;
  subService: string;
  materialKey: string;
  materialLabel: string;
  color: string | null;
};

export type PlannerApi = {
  cmd: (c: PlannerCmd, payload?: any) => void;
  loadProjectPicker: () => void;
  saveProjectDownload: () => void;
};

type Props = {
  onApi?: (api: PlannerApi) => void;
  onModeChange?: (mode: string) => void;
  onSurfaceSelected?: (payload: SurfaceSelectedPayload) => void;
  onSurfacesCleared?: () => void;
  onCatalogServiceSelected?: (payload: CatalogServiceSelectedPayload) => void;
};

function downloadJson(filename: string, data: any) {
  const dataStr = JSON.stringify(data, null, 2);
  const blob = new Blob([dataStr], { type: "application/json" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();

  URL.revokeObjectURL(url);
}

export default function PlannerFrame({
  onApi,
  onModeChange,
  onSurfaceSelected,
  onSurfacesCleared,
  onCatalogServiceSelected,
}: Props) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  const postToEngine = (msg: any) => {
    const w = iframeRef.current?.contentWindow;
    if (!w) return;
    w.postMessage(msg, "*");
  };

  const cmd = (c: PlannerCmd, payload?: any) => {
    postToEngine({
      protocolVersion: PROTOCOL_VERSION,
      type: "CMD",
      cmd: c,
      payload,
    });
  };

  const loadProjectPicker = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json,application/json,.png,.jpg,.jpeg,application/pdf";

    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;

      try {
        if (file.name.toLowerCase().endsWith(".json")) {
          const text = await file.text();
          const scene = JSON.parse(text);
          cmd("LOAD_PROJECT_JSON", { scene });
          return;
        }

        const form = new FormData();
        form.append("file", file);

        const resp = await fetch(RASTER_URL, { method: "POST", body: form });
        if (!resp.ok) {
          const msg = await resp.text();
          throw new Error(`Raster upload failed (${resp.status}): ${msg}`);
        }

        const raw = await resp.json();
        cmd("LOAD_RASTER_JSON", { raw });
      } catch (e: any) {
        alert(e?.message || String(e));
        console.error(e);
      }
    };

    input.click();
  };

  const saveProjectDownload = () => {
    cmd("REQUEST_SCENE_JSON");
  };

  useEffect(() => {
    onApi?.({ cmd, loadProjectPicker, saveProjectDownload });

    const onMessage = (event: MessageEvent) => {
      if (event.origin !== ENGINE_ORIGIN) return;

      const data: any = event.data;
      if (!data || data.protocolVersion !== PROTOCOL_VERSION) return;

      if (data.type === "ERROR") {
        console.error("[ENGINE ERROR]", data.message);
        return;
      }

      if (data.type === "MODE_CHANGED") {
        const mode = data?.payload?.mode;
        if (typeof mode === "string") onModeChange?.(mode);
        return;
      }

      if (data.type === "SURFACE_SELECTED") {
        const payload = data?.payload;
        if (
          payload &&
          typeof payload.surfaceId === "string" &&
          typeof payload.wallId === "string" &&
          (
            payload.surfaceType === "front" ||
            payload.surfaceType === "back" ||
            payload.surfaceType === "floor"
          )
        ) {
          onSurfaceSelected?.(payload);
        }
        return;
      }

      if (data.type === "SURFACES_CLEARED") {
        onSurfacesCleared?.();
        return;
      }

      if (data.type === "CATALOG_SERVICE_SELECTED") {
        const payload = data?.payload;
        if (
          payload &&
          typeof payload.mainService === "string" &&
          typeof payload.subService === "string" &&
          typeof payload.materialKey === "string" &&
          typeof payload.materialLabel === "string"
        ) {
          onCatalogServiceSelected?.(payload);
        }
        return;
      }

      if (data.type === "SCENE_JSON") {
        const scene = data?.payload?.scene;
        if (scene) downloadJson("plano_scene.json", scene);
      }
    };

    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [
    onApi,
    onModeChange,
    onSurfaceSelected,
    onSurfacesCleared,
    onCatalogServiceSelected,
  ]);

  return (
    <iframe
      ref={iframeRef}
      src={ENGINE_URL}
      title="React Planner Engine"
      allow="clipboard-read; clipboard-write"
      style={{
        position: "fixed",
        inset: 0,
        width: "100vw",
        height: "100vh",
        border: 0,
        zIndex: 1,
        background: "#fff",
      }}
      onLoad={() =>
        postToEngine({ protocolVersion: PROTOCOL_VERSION, type: "PING" })
      }
    />
  );
}