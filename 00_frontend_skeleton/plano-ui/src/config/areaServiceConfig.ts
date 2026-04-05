import type { AreaService } from "../state/plannerState";

export type MaterialSwatchShape = "circle" | "square" | "rect";

export type MaterialOption = {
  materialKey: string;
  materialLabel: string;
  color: string | null;
  textureUri?: string | null;
  swatch?: MaterialSwatchShape;
  dimensions?: { w: number; h: number };
};

export type SubServiceGroup = {
  groupKey: string;
  groupLabel: string;
  variant: "immediate" | "submenu";
  defaultColor?: string | null;
  dimensions?: { w: number; h: number };
  materials: MaterialOption[];
};

export const AREA_SERVICE_CONFIG: Record<AreaService, SubServiceGroup[]> = {
  painting: [
    {
      groupKey: "Internal paint",
      groupLabel: "Internal paint",
      variant: "submenu",
      defaultColor: "#f5f5f5",
      materials: [
        {
          materialKey: "paint-white",
          materialLabel: "White",
          color: "#f5f5f5",
          swatch: "circle",
        },
        {
          materialKey: "paint-off-white",
          materialLabel: "Off white",
          color: "#ece7de",
          swatch: "circle",
        },
        {
          materialKey: "paint-light-grey",
          materialLabel: "Light grey",
          color: "#d9d9d9",
          swatch: "circle",
        },
        {
          materialKey: "paint-grey",
          materialLabel: "Grey",
          color: "#b3b3b3",
          swatch: "circle",
        },
        {
          materialKey: "paint-charcoal",
          materialLabel: "Charcoal",
          color: "#555555",
          swatch: "circle",
        },
        {
          materialKey: "paint-black",
          materialLabel: "Black",
          color: "#1f1f1f",
          swatch: "circle",
        },
        {
          materialKey: "paint-beige",
          materialLabel: "Beige",
          color: "#d8c3a5",
          swatch: "circle",
        },
        {
          materialKey: "paint-sand",
          materialLabel: "Sand",
          color: "#cbb89d",
          swatch: "circle",
        },
        {
          materialKey: "paint-cream",
          materialLabel: "Cream",
          color: "#ede5d8",
          swatch: "circle",
        },
        {
          materialKey: "paint-taupe",
          materialLabel: "Taupe",
          color: "#a39281",
          swatch: "circle",
        },
        {
          materialKey: "paint-sage",
          materialLabel: "Sage",
          color: "#a8b19a",
          swatch: "circle",
        },
        {
          materialKey: "paint-olive",
          materialLabel: "Olive",
          color: "#7c8450",
          swatch: "circle",
        },
        {
          materialKey: "paint-dusty-blue",
          materialLabel: "Dusty blue",
          color: "#7f97ad",
          swatch: "circle",
        },
        {
          materialKey: "paint-navy",
          materialLabel: "Navy",
          color: "#31445a",
          swatch: "circle",
        },
        {
          materialKey: "paint-terracotta",
          materialLabel: "Terracotta",
          color: "#b86f4b",
          swatch: "circle",
        },
      ],
    },
    {
      groupKey: "External paint",
      groupLabel: "External paint",
      variant: "submenu",
      defaultColor: "#ece7de",
      materials: [
        {
          materialKey: "paint-external-offwhite",
          materialLabel: "Off white",
          color: "#ece7de",
          swatch: "circle",
        },
        {
          materialKey: "paint-external-cream",
          materialLabel: "Cream",
          color: "#ede5d8",
          swatch: "circle",
        },
        {
          materialKey: "paint-external-stone",
          materialLabel: "Stone",
          color: "#c9c1b2",
          swatch: "circle",
        },
        {
          materialKey: "paint-external-sand",
          materialLabel: "Sand",
          color: "#d5c2a3",
          swatch: "circle",
        },
        {
          materialKey: "paint-external-grey",
          materialLabel: "Grey",
          color: "#a7a4a0",
          swatch: "circle",
        },
        {
          materialKey: "paint-external-charcoal",
          materialLabel: "Charcoal",
          color: "#5f5c57",
          swatch: "circle",
        },
      ],
    },
  ],
  flooring: [
    {
      groupKey: "Ceramic tiles 60×60",
      groupLabel: "60×60",
      variant: "submenu",
      defaultColor: "#d8d5cf",
      dimensions: { w: 0.6, h: 0.6 },
      materials: [
        {
          materialKey: "flooring-ceramic-60x60-carara",
          materialLabel: "Carara marble",
          color: "#d8d5cf",
          textureUri: "/textures/60x60.carara.marble.png",
          swatch: "square",
          dimensions: { w: 0.6, h: 0.6 },
        },
        {
          materialKey: "flooring-ceramic-60x60-cream",
          materialLabel: "Cream",
          color: "#d9d1c2",
          textureUri: "/textures/60x60.creame.png",
          swatch: "square",
          dimensions: { w: 0.6, h: 0.6 },
        },
      ],
    },
    {
      groupKey: "Ceramic tiles 120×60",
      groupLabel: "120×60",
      variant: "submenu",
      defaultColor: "#d3cec5",
      dimensions: { w: 1.2, h: 0.6 },
      materials: [
        {
          materialKey: "flooring-ceramic-120x60-carara",
          materialLabel: "Carara marble",
          color: "#d3cec5",
          textureUri: "/textures/120x60.carara.marble.png",
          swatch: "rect",
          dimensions: { w: 1.2, h: 0.6 },
        },
        {
          materialKey: "flooring-ceramic-120x60-cream",
          materialLabel: "Cream",
          color: "#d8cfbf",
          textureUri: "/textures/120x60.creame.png",
          swatch: "rect",
          dimensions: { w: 1.2, h: 0.6 },
        },
      ],
    },
    {
      groupKey: "Ceramic tiles custom",
      groupLabel: "Custom tiles",
      variant: "submenu",
      materials: [
        {
          materialKey: "flooring-ceramic-75x75",
          materialLabel: "75×75",
          color: "#d9d4cb",
          swatch: "square",
          dimensions: { w: 0.75, h: 0.75 },
        },
        {
          materialKey: "flooring-ceramic-90x90",
          materialLabel: "90×90",
          color: "#cfc9bf",
          swatch: "square",
          dimensions: { w: 0.9, h: 0.9 },
        },
        {
          materialKey: "flooring-ceramic-120x120",
          materialLabel: "120×120",
          color: "#c8c2b9",
          swatch: "square",
          dimensions: { w: 1.2, h: 1.2 },
        },
      ],
    },
    {
      groupKey: "Laminate",
      groupLabel: "Laminate",
      variant: "immediate",
      materials: [
        {
          materialKey: "flooring-laminate",
          materialLabel: "Laminate",
          color: "#9a7b5f",
          swatch: "rect",
        },
      ],
    },
    {
      groupKey: "Microcement",
      groupLabel: "Microcement",
      variant: "submenu",
      defaultColor: "#9a9a96",
      materials: [
        {
          materialKey: "flooring-microcement-grey",
          materialLabel: "Grey",
          color: "#9a9a96",
          swatch: "circle",
        },
        {
          materialKey: "flooring-microcement-charcoal",
          materialLabel: "Charcoal",
          color: "#555555",
          swatch: "circle",
        },
        {
          materialKey: "flooring-microcement-sand",
          materialLabel: "Sand",
          color: "#c7b7a0",
          swatch: "circle",
        },
      ],
    },
    {
      groupKey: "Polished concrete",
      groupLabel: "Concrete",
      variant: "immediate",
      materials: [
        {
          materialKey: "flooring-polished-concrete",
          materialLabel: "Polished concrete",
          color: "#8d8f93",
          swatch: "rect",
        },
      ],
    },
    {
      groupKey: "Parquet",
      groupLabel: "Parquet",
      variant: "immediate",
      defaultColor: "#8a6447",
      dimensions: { w: 1.2, h: 0.2 },
      materials: [
        {
          materialKey: "flooring-parquet-120x20",
          materialLabel: "Parquet 120×20",
          color: "#8a6447",
          textureUri: "/textures/120x20.parquet.png",
          swatch: "rect",
          dimensions: { w: 1.2, h: 0.2 },
        },
      ],
    },
  ],
  plastering: [
    {
      groupKey: "Internal (monacote+finittura)",
      groupLabel: "Internal monacote",
      variant: "immediate",
      defaultColor: "#c8c0b8",
      materials: [
        {
          materialKey: "plastering-monacote",
          materialLabel: "Monacote",
          color: "#c8c0b8",
          swatch: "circle",
        },
      ],
    },
    {
      groupKey: "Internal (microcement)",
      groupLabel: "Microcement",
      variant: "submenu",
      defaultColor: "#999999",
      materials: [
        {
          materialKey: "plastering-microcement-grey",
          materialLabel: "Grey",
          color: "#999999",
          swatch: "circle",
        },
        {
          materialKey: "plastering-microcement-charcoal",
          materialLabel: "Charcoal",
          color: "#4a4a4a",
          swatch: "circle",
        },
        {
          materialKey: "plastering-microcement-sand",
          materialLabel: "Sand",
          color: "#c9b99a",
          swatch: "circle",
        },
      ],
    },
    {
      groupKey: "External (GR1000)",
      groupLabel: "External GR1000",
      variant: "submenu",
      defaultColor: "#d7d0c6",
      materials: [
        {
          materialKey: "plastering-gr1000-offwhite",
          materialLabel: "Off white",
          color: "#d7d0c6",
          swatch: "circle",
        },
        {
          materialKey: "plastering-gr1000-stone",
          materialLabel: "Stone",
          color: "#bdb3a5",
          swatch: "circle",
        },
        {
          materialKey: "plastering-gr1000-grey",
          materialLabel: "Grey",
          color: "#9c9791",
          swatch: "circle",
        },
      ],
    },
    {
      groupKey: "External (silicato)",
      groupLabel: "External silicato",
      variant: "submenu",
      defaultColor: "#ede5d8",
      materials: [
        {
          materialKey: "plastering-silicato-cream",
          materialLabel: "Cream",
          color: "#ede5d8",
          swatch: "circle",
        },
        {
          materialKey: "plastering-silicato-sand",
          materialLabel: "Sand",
          color: "#d5c2a3",
          swatch: "circle",
        },
        {
          materialKey: "plastering-silicato-grey",
          materialLabel: "Grey",
          color: "#b0aca5",
          swatch: "circle",
        },
      ],
    },
    {
      groupKey: "Stone restoration",
      groupLabel: "Stone restoration",
      variant: "immediate",
      defaultColor: "#d4b853",
      materials: [
        {
          materialKey: "plastering-stone-restoration",
          materialLabel: "Stone restoration",
          color: "#d4b853",
          swatch: "circle",
        },
      ],
    },
  ],
  boards: [
    {
      groupKey: "Flat ceiling",
      groupLabel: "Gypsum board",
      variant: "immediate",
      defaultColor: "#dcdcdc",
      dimensions: { w: 2.4, h: 1.2 },
      materials: [
        {
          materialKey: "boards-flat-ceiling",
          materialLabel: "Gypsum board 2.4×1.2",
          color: "#dcdcdc",
          swatch: "rect",
          dimensions: { w: 2.4, h: 1.2 },
        },
      ],
    },
  ],
};