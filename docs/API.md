# PlanO API Reference

## Raster Backend API (FastAPI, port 8010)

Base URL: `http://localhost:8010`

Interactive docs (Swagger UI): `http://localhost:8010/docs`

### POST /upload-plan

Upload a floor plan image or PDF for AI-powered recognition and conversion to an editable scene.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` — image (PNG, JPG, BMP) or PDF file

```bash
curl -X POST http://localhost:8010/upload-plan \
  -F "file=@/path/to/floorplan.png"
```

**Response (200 OK):**
```json
{
  "unit": "cm",
  "layers": {
    "layer-1": {
      "id": "layer-1",
      "altitude": 0,
      "order": 0,
      "opacity": 1,
      "name": "default",
      "visible": true,
      "vertices": {
        "a1b2c3d4": {
          "id": "a1b2c3d4",
          "x": 200,
          "y": 1606,
          "lines": ["e5f6g7h8"],
          "areas": ["i9j0k1l2"]
        }
      },
      "lines": {
        "e5f6g7h8": {
          "id": "e5f6g7h8",
          "type": "wall",
          "vertices": ["a1b2c3d4", "m3n4o5p6"],
          "properties": {
            "height": { "length": 300 },
            "thickness": { "length": 20 },
            "textureA": "bricks",
            "textureB": "bricks"
          },
          "holes": []
        }
      },
      "areas": {
        "i9j0k1l2": {
          "id": "i9j0k1l2",
          "type": "area",
          "vertices": ["a1b2c3d4", "m3n4o5p6", "q7r8s9t0"],
          "properties": {
            "patternColor": "#F5F4F4",
            "texture": "none"
          }
        }
      },
      "holes": {},
      "items": {}
    }
  },
  "grids": {
    "h1": { "id": "h1", "type": "horizontal-streak", "properties": { "step": 20 } },
    "v1": { "id": "v1", "type": "vertical-streak", "properties": { "step": 20 } }
  },
  "width": 3000,
  "height": 2000
}
```

**Error Responses:**

| Status | Reason                                      |
|--------|---------------------------------------------|
| 400    | No file provided or unsupported file type   |
| 500    | RasterScan API failure or conversion error  |
| 500    | `RASTERSCAN_API_KEY is not set in environment` |

**Timing:** Expect 10-60 seconds depending on image complexity. The RasterScan API is the bottleneck.

## iframe postMessage Protocol (v1)

Communication between the PlanO frontend (parent window) and the React-Planner engine (iframe).

### Parent to Planner

All messages follow this format:
```javascript
iframe.contentWindow.postMessage({
  type: 'CMD',
  cmd: '<COMMAND>',
  payload: <data>
}, '*')
```

#### Commands

| Command           | Payload        | Description                              |
|-------------------|----------------|------------------------------------------|
| `NEW_PROJECT`     | none           | Clear scene, start fresh                 |
| `LOAD_SCENE`      | scene JSON     | Load a saved scene                       |
| `LOAD_RASTER_JSON`| scene JSON     | Load a raster-converted scene            |
| `GET_SCENE`       | none           | Request current scene data               |

### Planner to Parent

```javascript
window.parent.postMessage({
  type: 'SCENE_JSON',
  payload: sceneJSON
}, '*')
```

### Usage Example (PlannerFrame.tsx pattern)

```typescript
// Send command to planner
const sendToPlanner = (cmd: string, payload?: any) => {
  const iframe = iframeRef.current;
  if (iframe?.contentWindow) {
    iframe.contentWindow.postMessage({ type: 'CMD', cmd, payload }, '*');
  }
};

// Listen for responses
useEffect(() => {
  const handler = (event: MessageEvent) => {
    if (event.data?.type === 'SCENE_JSON') {
      const scene = event.data.payload;
      // Use scene data
    }
  };
  window.addEventListener('message', handler);
  return () => window.removeEventListener('message', handler);
}, []);

// Load a scene
sendToPlanner('LOAD_SCENE', savedScene);

// Get current scene for saving
sendToPlanner('GET_SCENE');
```

## React-Planner Scene JSON Schema

The scene JSON is the central data format exchanged between all components.

### Top-level Structure

```typescript
interface Scene {
  unit: 'cm' | 'mm' | 'm' | 'in' | 'ft';
  width: number;          // Scene width in unit
  height: number;         // Scene height in unit
  selectedLayer: string;  // Active layer ID
  layers: Record<string, Layer>;
  grids: Record<string, Grid>;
  guides: {
    horizontal: Record<string, Guide>;
    vertical: Record<string, Guide>;
    circular: Record<string, Guide>;
  };
  groups: Record<string, Group>;
  meta: Record<string, any>;
}
```

### Layer

```typescript
interface Layer {
  id: string;
  name: string;
  altitude: number;
  order: number;
  opacity: number;
  visible: boolean;
  vertices: Record<string, Vertex>;
  lines: Record<string, Line>;
  areas: Record<string, Area>;
  holes: Record<string, Hole>;
  items: Record<string, Item>;
  selected: {
    vertices: string[];
    lines: string[];
    areas: string[];
    holes: string[];
    items: string[];
  };
}
```

### Vertex (Point)

```typescript
interface Vertex {
  id: string;
  x: number;              // X coordinate in scene units
  y: number;              // Y coordinate in scene units
  type: string;
  name: string;
  lines: string[];        // IDs of connected lines
  areas: string[];        // IDs of connected areas
  selected: boolean;
  visible: boolean;
}
```

### Line (Wall)

```typescript
interface Line {
  id: string;
  type: 'wall';           // Element type from catalog
  vertices: [string, string]; // Start and end vertex IDs
  holes: string[];        // IDs of doors/windows on this wall
  properties: {
    height: { length: number };     // Wall height (default 300cm)
    thickness: { length: number };  // Wall thickness (default 20cm)
    opacity: number;
    textureA: string;     // Inner face texture
    textureB: string;     // Outer face texture
  };
  selected: boolean;
  visible: boolean;
}
```

### Area (Room)

```typescript
interface Area {
  id: string;
  type: 'area';
  vertices: string[];     // Ordered vertex IDs forming polygon
  holes: string[];
  properties: {
    patternColor: string; // Floor color (hex)
    thickness: { length: number };
    texture: string;      // Floor texture name
  };
  selected: boolean;
  visible: boolean;
}
```

### Hole (Door/Window)

```typescript
interface Hole {
  id: string;
  type: 'door' | 'window' | 'sliding-door' | 'gate';
  line: string;           // ID of the wall this hole is in
  offset: number;         // Position along wall (0-1)
  properties: {
    width: { length: number };
    height: { length: number };
    altitude: { length: number }; // Height from floor
  };
  selected: boolean;
  visible: boolean;
}
```

### Item (Furniture)

```typescript
interface Item {
  id: string;
  type: string;           // Element type from catalog (e.g., 'sofa', 'bed')
  x: number;              // X position
  y: number;              // Y position
  rotation: number;       // Rotation in degrees
  properties: Record<string, any>; // Element-specific properties
  selected: boolean;
  visible: boolean;
}
```

## RasterScan External API

**Endpoint**: `https://backend.rasterscan.com/raster-to-vector-raw`
**Method**: POST
**Auth**: `x-api-key` header

**Request:**
```bash
curl -X POST https://backend.rasterscan.com/raster-to-vector-raw \
  -H "x-api-key: sk-your-key-here" \
  -F "image=@floorplan.png"
```

**Response:**
```json
{
  "message": "Raster to vector conversion successful",
  "data": {
    "area": 266728,
    "doors": [
      { "bbox": [x1, y1, x2, y2] },
      ...
    ],
    "walls": [
      { "start": [x, y], "end": [x, y], "thickness": 20 },
      ...
    ],
    "rooms": [
      { "vertices": [[x1,y1], [x2,y2], ...], "label": "Kitchen" },
      ...
    ]
  },
  "image": "data:image/jpeg;base64,..."
}
```

**Rate Limits**: Retry on HTTP 429 with exponential backoff.
**Timeout**: Recommended 180 seconds (large PDFs can take time).
