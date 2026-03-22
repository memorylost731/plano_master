import type { AreaService } from "../../state/plannerState";
import type { SubServiceGroup, MaterialOption } from "../../config/areaServiceConfig";

type Props = {
  service: AreaService;
  groups: SubServiceGroup[];
  openSubGroup: string | null;
  activeSubService: string | null;
  activeMaterialKey: string | null;
  committedEntries: any[];
  selectedCount: number;
  totalM2: number;
  canComplete: boolean;
  onGroupClick: (service: AreaService, group: SubServiceGroup) => void;
  onMaterialClick: (service: AreaService, group: SubServiceGroup, material: MaterialOption) => void;
  onComplete: () => void;
  onEntryClick: (entry: any) => void;
};

function getSwatchShapeClass(material: MaterialOption) {
  if (material.swatch === "square") return "h-6 w-6 rounded-[4px]";
  if (material.swatch === "rect") return "h-4 w-10 rounded-[4px]";
  return "h-6 w-6 rounded-full";
}

function getGroupPreviewShapeClass(group: SubServiceGroup) {
  const first = group.materials[0];
  if (!first) return "h-3 w-3 rounded-full";
  if (first.swatch === "square") return "h-3 w-3 rounded-[3px]";
  if (first.swatch === "rect") return "h-2.5 w-6 rounded-[3px]";
  return "h-3 w-3 rounded-full";
}

export default function ServicePanel({
  service,
  groups,
  openSubGroup,
  activeSubService,
  activeMaterialKey,
  committedEntries,
  selectedCount,
  totalM2,
  canComplete,
  onGroupClick,
  onMaterialClick,
  onComplete,
  onEntryClick,
}: Props) {
  const openGroup = groups.find((g) => g.groupKey === openSubGroup) || null;

  return (
    <div className="pointer-events-none absolute right-4 top-20 z-40">
      <div className="pointer-events-auto w-[300px] max-h-[75vh] overflow-y-auto rounded-xl bg-white/95 shadow-lg p-4">
        <div className="text-sm font-semibold capitalize mb-3">
          {service}
        </div>

        <div className="flex flex-col gap-2">
          {groups.map((group) => {
            const isActive = activeSubService === group.groupKey;
            const isOpen = openSubGroup === group.groupKey;
            const isDisabled = group.materials.length === 0;
            const first = group.materials[0];

            return (
              <button
                key={group.groupKey}
                onClick={() => onGroupClick(service, group)}
                disabled={isDisabled}
                className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm ${
                  isActive || isOpen ? "ring-2 ring-black" : ""
                } ${isDisabled ? "opacity-40" : "hover:bg-gray-100"}`}
              >
                <div className="flex items-center gap-2">
                  {first?.textureUri ? (
                    <img
                      src={first.textureUri}
                      alt={first.materialLabel}
                      className={`border object-cover ${getGroupPreviewShapeClass(group)}`}
                    />
                  ) : group.defaultColor ? (
                    <span
                      className={`border ${getGroupPreviewShapeClass(group)}`}
                      style={{ backgroundColor: group.defaultColor }}
                    />
                  ) : null}
                  <span>{group.groupLabel}</span>
                </div>

                {group.variant === "submenu" && (
                  <span>{isOpen ? "-" : "+"}</span>
                )}
              </button>
            );
          })}
        </div>

        {openGroup && openGroup.materials.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {openGroup.materials.map((mat) => {
              const isActive =
                activeSubService === openGroup.groupKey &&
                activeMaterialKey === mat.materialKey;

              return (
                <button
                  key={mat.materialKey}
                  onClick={() => onMaterialClick(service, openGroup, mat)}
                  className={`flex items-center gap-2 px-2 py-1 rounded ${
                    isActive ? "ring-2 ring-black" : "hover:bg-gray-100"
                  }`}
                >
                  {mat.textureUri ? (
                    <img
                      src={mat.textureUri}
                      alt={mat.materialLabel}
                      className={`border object-cover ${getSwatchShapeClass(mat)}`}
                    />
                  ) : mat.color ? (
                    <span
                      className={`border ${getSwatchShapeClass(mat)}`}
                      style={{ backgroundColor: mat.color }}
                    />
                  ) : (
                    <span
                      className={`border bg-gray-200 ${getSwatchShapeClass(mat)}`}
                    />
                  )}
                  <span className="text-xs">{mat.materialLabel}</span>
                </button>
              );
            })}
          </div>
        )}

        <div className="mt-4 text-sm">
          <div>{selectedCount} faces</div>
          <div>{totalM2} m²</div>
        </div>

        <button
          onClick={onComplete}
          disabled={!canComplete}
          className={`mt-3 w-full py-2 rounded-lg text-sm font-semibold ${
            canComplete
              ? "bg-black text-white"
              : "bg-gray-300 text-gray-500"
          }`}
        >
          Complete Service
        </button>

        {committedEntries.length > 0 && (
          <div className="mt-4 border-t pt-3">
            <div className="text-xs font-semibold mb-2">Committed</div>

            {committedEntries.map((entry, i) => (
              <button
                key={i}
                onClick={() => onEntryClick(entry)}
                className="flex justify-between w-full text-xs py-1 hover:bg-gray-100"
              >
                <span>{entry.materialLabel}</span>
                <span>{entry.totalM2} m²</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}