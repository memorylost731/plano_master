import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Building2, ExternalLink, Ruler, Layers, MapPin, Palette } from "lucide-react";
import { usePlannerState, type SelectedBuilding } from "../../state/plannerState.tsx";

interface BuildingPopupProps {
  building: SelectedBuilding;
  onClose: () => void;
}

export default function BuildingPopup({ building, onClose }: BuildingPopupProps) {
  const navigate = useNavigate();
  const { setSelectedBuilding } = usePlannerState();

  const handleOpenInPlano = useCallback(() => {
    setSelectedBuilding(building);
    navigate("/planner");
  }, [building, navigate, setSelectedBuilding]);

  const osmUrl = `https://www.openstreetmap.org/${building.osmType}/${building.osmId}`;

  const rows: Array<{ icon: React.ReactNode; label: string; value: string }> = [];

  if (building.name) {
    rows.push({ icon: <Building2 className="h-3.5 w-3.5" />, label: "Name", value: building.name });
  }
  if (building.buildingType) {
    rows.push({
      icon: <Building2 className="h-3.5 w-3.5" />,
      label: "Type",
      value: building.buildingType.replace(/_/g, " "),
    });
  }
  if (building.levels) {
    rows.push({ icon: <Layers className="h-3.5 w-3.5" />, label: "Levels", value: building.levels });
  }
  if (building.height) {
    rows.push({ icon: <Ruler className="h-3.5 w-3.5" />, label: "Height", value: `${building.height} m` });
  }
  if (building.address) {
    rows.push({ icon: <MapPin className="h-3.5 w-3.5" />, label: "Address", value: building.address });
  }
  if (building.material) {
    rows.push({ icon: <Palette className="h-3.5 w-3.5" />, label: "Material", value: building.material });
  }

  return (
    <div className="w-72 rounded-xl border border-white/30 bg-white/95 shadow-2xl backdrop-blur-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-100 px-4 py-3">
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-blue-600" />
          <h3 className="text-sm font-semibold text-zinc-900">
            {building.name || "Building"}
          </h3>
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 transition-colors"
          aria-label="Close popup"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Properties */}
      <div className="px-4 py-3 space-y-2">
        {rows.length === 0 && (
          <p className="text-xs text-zinc-500 italic">No detailed tags available for this building.</p>
        )}
        {rows.map((row) => (
          <div key={row.label} className="flex items-center gap-2 text-xs">
            <span className="text-zinc-400">{row.icon}</span>
            <span className="font-medium text-zinc-600 w-16 shrink-0">{row.label}</span>
            <span className="text-zinc-900 truncate capitalize">{row.value}</span>
          </div>
        ))}
      </div>

      {/* Coordinates */}
      <div className="px-4 pb-2">
        <p className="text-[10px] text-zinc-400 font-mono">
          {building.lat.toFixed(6)}, {building.lng.toFixed(6)}
        </p>
      </div>

      {/* Actions */}
      <div className="flex gap-2 border-t border-zinc-100 px-4 py-3">
        <button
          onClick={handleOpenInPlano}
          className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-zinc-900 px-3 py-2 text-xs font-medium text-white hover:bg-zinc-800 transition-colors"
        >
          <Building2 className="h-3.5 w-3.5" />
          Open in PlanO
        </button>
        <a
          href={osmUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-1.5 rounded-lg border border-zinc-200 px-3 py-2 text-xs font-medium text-zinc-700 hover:bg-zinc-50 transition-colors"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          OSM
        </a>
      </div>
    </div>
  );
}
