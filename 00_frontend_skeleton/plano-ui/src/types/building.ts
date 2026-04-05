export interface SelectedBuilding {
  osmId: string;
  osmType: "way" | "relation" | "node";
  name?: string;
  buildingType?: string;
  levels?: string;
  height?: string;
  address?: string;
  material?: string;
  lat: number;
  lng: number;
  properties: Record<string, unknown>;
}
