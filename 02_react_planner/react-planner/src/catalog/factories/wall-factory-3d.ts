import {
  BackSide,
  BoxGeometry,
  BufferGeometry,
  DoubleSide,
  Float32BufferAttribute,
  FrontSide,
  Group,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Object3D,
  Object3DEventMap,
  RepeatWrapping,
  SRGBColorSpace,
  Texture,
  TextureLoader,
  Vector2,
  Vector3
} from 'three';
import { CSG } from 'three-csg-ts';

import { Layer, Line, Scene } from '../../models';
import * as SharedStyle from '../../shared-style';
import { CatalogElementTextures } from '../../types';
import { verticesDistance } from '../../utils/geometry';

import { calcLineEnd } from './utils/calcPolygon';

const halfPI = Math.PI / 2;

const baseTextureCache: Record<string, Texture> = {};
const loaderSingleton = new TextureLoader();

function getBaseTexture(uri: string): Texture {
  if (!uri) return null as any;
  if (baseTextureCache[uri]) return baseTextureCache[uri];
  const tex = loaderSingleton.load(uri);
  tex.colorSpace = SRGBColorSpace;
  baseTextureCache[uri] = tex;
  return tex;
}

const applyTexture = (
  texture: CatalogElementTextures[string],
  length: number,
  height: number
) => {
  const material = new MeshStandardMaterial({
    roughness: 0.85,
    metalness: 0,
  });

  const setupMap = (
    base: Texture,
    repeatL: number,
    repeatH: number,
    assign: (t: Texture) => void,
    extra?: (t: Texture) => void
  ) => {
    if (!base) return;

    const cloneAndAssign = () => {
      if (!base.image || !base.image.width) {
        requestAnimationFrame(cloneAndAssign);
        return;
      }
      const map = base.clone();
      map.image = base.image;
      map.wrapS = RepeatWrapping;
      map.wrapT = RepeatWrapping;
      map.repeat.set(repeatL, repeatH);
      map.needsUpdate = true;
      assign(map);
      if (extra) extra(map);
      material.needsUpdate = true;
    };

    cloneAndAssign();
  };

  if (texture) {
    const base = getBaseTexture(texture.uri);
    setupMap(
      base,
      length * texture.lengthRepeatScale,
      height * texture.heightRepeatScale,
      (m) => {
        material.map = m;
      }
    );

    const normal = texture.normal;
    if (normal) {
      const baseNormal = getBaseTexture(normal.uri);
      setupMap(
        baseNormal,
        length * normal.lengthRepeatScale,
        height * normal.heightRepeatScale,
        (m) => {
          material.normalMap = m;
        },
        () => {
          material.normalScale = new Vector2(
            normal.normalScaleX,
            normal.normalScaleY
          );
        }
      );
    }
  }

  return material;
};

export function buildWall(
  element: Line,
  layer: Layer,
  scene: Scene,
  textures: CatalogElementTextures
) {
  let vertex0 = layer.vertices[element.vertices[0]];
  let vertex1 = layer.vertices[element.vertices[1]];
  let inverted = false;

  if (vertex0.x > vertex1.x) {
    const app = vertex0;
    vertex0 = vertex1;
    vertex1 = app;
    inverted = true;
  }

  const height = element.properties.height.length;
  const thickness = element.properties.thickness.length;
  const opacity = element.properties.opacity;
  const faceThickness = 0.2;
  const faceDistance = 0.5;

  const distance = verticesDistance(vertex0, vertex1);

  const points1 = calcLineEnd(
    layer,
    element.id,
    element.vertices[0],
    thickness
  );
  const rawPoints2 = calcLineEnd(
    layer,
    element.id,
    element.vertices[1],
    thickness
  );
  const points2 = rawPoints2.map((p) => ({ x: distance - p.x, y: p.y }));

  const endA = points2[0];
  const endB = points2[points2.length - 1];
  const frontEnd =
    Math.abs(endA.y - points1[0].y) <= Math.abs(endB.y - points1[0].y)
      ? endA
      : endB;
  const backEnd = frontEnd === endA ? endB : endA;

  const frontPoints = [points1[0], frontEnd].map((p) => {
    return { y: p.y * -1, x: p.x };
  });
  const backPoints = [points1[points1.length - 1], backEnd].map((p) => {
    return { y: p.y * -1, x: p.x };
  });

  const halfDistance = distance / 2;

  const fStart = frontPoints[0];
  const fEnd = frontPoints[1];
  const bStart = backPoints[0];
  const bEnd = backPoints[1];

  const bottomY = -height / 2;
  const topY = height / 2;

  const xLocal = (x: number) => x - halfDistance;
  const uFromX = (x: number) => x / distance;

  const v0 = { x: xLocal(fEnd.x), y: bottomY, z: fEnd.y };
  const v1 = { x: xLocal(fStart.x), y: bottomY, z: fStart.y };
  const v2 = { x: xLocal(bStart.x), y: bottomY, z: bStart.y };
  const v3 = { x: xLocal(bEnd.x), y: bottomY, z: bEnd.y };

  const v4 = { x: v0.x, y: topY, z: v0.z };
  const v5 = { x: v1.x, y: topY, z: v1.z };
  const v6 = { x: v2.x, y: topY, z: v2.z };
  const v7 = { x: v3.x, y: topY, z: v3.z };

  const positions: number[] = [];
  const uvs: number[] = [];

  const push = (vx: { x: number; y: number; z: number }, ux = 0, vy = 0) => {
    positions.push(vx.x, vx.y, vx.z);
    uvs.push(ux, vy);
  };

  const tri = (
    a: { x: number; y: number; z: number },
    b: { x: number; y: number; z: number },
    c: { x: number; y: number; z: number },
    au = 0,
    av = 0,
    bu = 0,
    bv = 0,
    cu = 0,
    cv = 0
  ) => {
    push(a, au, av);
    push(b, bu, bv);
    push(c, cu, cv);
  };

  const uF0 = uFromX(fStart.x),
    uF1 = uFromX(fEnd.x);
  tri(v0, v1, v5, uF0, 0, uF1, 0, uF1, 1);
  tri(v0, v5, v4, uF0, 0, uF1, 1, uF0, 1);

  const uB0 = uFromX(bStart.x),
    uB1 = uFromX(bEnd.x);
  tri(v2, v3, v7, uB1, 0, uB0, 0, uB0, 1);
  tri(v2, v7, v6, uB1, 0, uB0, 1, uB1, 1);

  tri(v3, v0, v4);
  tri(v3, v4, v7);

  tri(v1, v2, v6);
  tri(v1, v6, v5);

  tri(v0, v2, v1);
  tri(v0, v3, v2);

  tri(v4, v5, v6);
  tri(v4, v6, v7);

  const soulGeometry = new BufferGeometry();
  soulGeometry.setAttribute(
    'position',
    new Float32BufferAttribute(positions, 3)
  );
  soulGeometry.setAttribute('uv', new Float32BufferAttribute(uvs, 2));
  soulGeometry.computeVertexNormals();

  const frontVertCount = 2 * 3;
  const backVertCount = 2 * 3;
  const remainingVertCount =
    positions.length / 3 - frontVertCount - backVertCount;

  soulGeometry.clearGroups();
  soulGeometry.addGroup(0, frontVertCount, 0);
  soulGeometry.addGroup(frontVertCount, backVertCount, 1);
  soulGeometry.addGroup(frontVertCount + backVertCount, remainingVertCount, 2);

  const frontHiddenMat = new MeshBasicMaterial({
    transparent: true,
    opacity: 0,
    depthWrite: false,
    side: BackSide
  });
  const backHiddenMat = new MeshBasicMaterial({
    transparent: true,
    opacity: 0,
    depthWrite: false,
    side: FrontSide
  });
  const sideVisibleMat = new MeshStandardMaterial({
    color: element.selected ? SharedStyle.MESH_SELECTED : 0xd3d3d3,
    side: DoubleSide,
    opacity,
    transparent: opacity < 1,
    roughness: 0.85,
    metalness: 0,
  });

  let soul: Mesh = new Mesh(soulGeometry, [
    frontHiddenMat,
    backHiddenMat,
    sideVisibleMat
  ]);

  const alpha = Math.asin((vertex1.y - vertex0.y) / distance);

  const sinAlpha = Math.sin(alpha);
  const cosAlpha = Math.cos(alpha);

  element.holes.forEach((holeID) => {
    const holeData = layer.holes[holeID];

    const holeWidth = holeData.properties.width.length;
    const holeHeight = holeData.properties.height.length;
    const holeAltitude = holeData.properties.altitude.length;
    const offset = inverted ? 1 - holeData.offset : holeData.offset;
    const holeDistance = offset * distance;

    const holeGeometry = new BoxGeometry(holeWidth, holeHeight, thickness);
    const holeMesh = new Mesh(holeGeometry);

    holeMesh.position.set(
      holeDistance - distance / 2,
      -(height / 2) + holeAltitude + holeHeight / 2,
      0
    );

    holeMesh.updateMatrix();

    soul = CSG.subtract(soul, holeMesh);
  });

  soul.position.y += height / 2;
  soul.position.x += halfDistance * cosAlpha;
  soul.position.z -= halfDistance * sinAlpha;

  soul.rotation.y = alpha;
  soul.name = 'soul';
  soul.castShadow = true;
  soul.receiveShadow = true;

  const frontMaterial = applyTexture(
    textures[element.properties.textureB],
    distance,
    height
  );
  const backMaterial = applyTexture(
    textures[element.properties.textureA],
    distance,
    height
  );

  [frontMaterial, backMaterial].forEach((mat) => {
    mat.opacity = opacity;
    if (opacity < 1) mat.transparent = true;
  });

  const buildExtrudedQuad = (
    a: { x: number; y: number; z: number },
    b: { x: number; y: number; z: number },
    c: { x: number; y: number; z: number },
    d: { x: number; y: number; z: number },
    thicknessLocal: number,
    uA: number,
    uB: number
  ) => {
    const ax = a.x,
      ay = a.y,
      az = a.z;
    const bx = b.x,
      by = b.y,
      bz = b.z;
    const cx = c.x,
      cy = c.y,
      cz = c.z;
    const dx = d.x,
      dy = d.y,
      dz = d.z;

    const abx = bx - ax,
      aby = by - ay,
      abz = bz - az;
    const adx = dx - ax,
      ady = dy - ay,
      adz = dz - az;
    let nx = aby * adz - abz * ady;
    let ny = abz * adx - abx * adz;
    let nz = abx * ady - aby * adx;
    const nLen = Math.hypot(nx, ny, nz) || 1;
    nx /= nLen;
    ny /= nLen;
    nz /= nLen;

    const halfT = thicknessLocal / 2;

    const aF = [ax + nx * halfT, ay + ny * halfT, az + nz * halfT];
    const bF = [bx + nx * halfT, by + ny * halfT, bz + nz * halfT];
    const cF = [cx + nx * halfT, cy + ny * halfT, cz + nz * halfT];
    const dF = [dx + nx * halfT, dy + ny * halfT, dz + nz * halfT];

    const aB = [ax - nx * halfT, ay - ny * halfT, az - nz * halfT];
    const bB = [bx - nx * halfT, by - ny * halfT, bz - nz * halfT];
    const cB = [cx - nx * halfT, cy - ny * halfT, cz - nz * halfT];
    const dB = [dx - nx * halfT, dy - ny * halfT, dz - nz * halfT];

    const pos: number[] = [];
    const uv: number[] = [];

    const pushV = (v: number[], u = 0, vT = 0) => {
      pos.push(v[0], v[1], v[2]);
      uv.push(u, vT);
    };
    const triV = (
      A: number[],
      B: number[],
      C: number[],
      Au = 0,
      Av = 0,
      Bu = 0,
      Bv = 0,
      Cu = 0,
      Cv = 0
    ) => {
      pushV(A, Au, Av);
      pushV(B, Bu, Bv);
      pushV(C, Cu, Cv);
    };

    triV(aF, bF, cF, uA, 0, uB, 0, uB, 1);
    triV(aF, cF, dF, uA, 0, uB, 1, uA, 1);

    triV(bB, aB, dB);
    triV(bB, dB, cB);

    triV(aB, aF, bF);
    triV(aB, bF, bB);
    triV(bB, bF, cF);
    triV(bB, cF, cB);
    triV(cB, cF, dF);
    triV(cB, dF, dB);
    triV(dB, dF, aF);
    triV(dB, aF, aB);

    const g = new BufferGeometry();
    g.setAttribute('position', new Float32BufferAttribute(pos, 3));
    g.setAttribute('uv', new Float32BufferAttribute(uv, 2));
    g.computeVertexNormals();
    return g;
  };

  const uFrontA = uFromX(fStart.x),
    uFrontB = uFromX(fEnd.x);
  const frontGeom = buildExtrudedQuad(
    v0,
    v1,
    v5,
    v4,
    faceThickness,
    uFrontA,
    uFrontB
  );

  const uBackA = uFromX(bStart.x),
    uBackB = uFromX(bEnd.x);
  const backGeom = buildExtrudedQuad(
    v2,
    v3,
    v7,
    v6,
    faceThickness,
    uBackB,
    uBackA
  );

  let frontFace: Mesh = new Mesh(frontGeom, frontMaterial);
  let backFace: Mesh = new Mesh(backGeom, backMaterial);

  const frontCenter = new Vector3(
    (v0.x + v1.x + v5.x + v4.x) / 4,
    (v0.y + v1.y + v5.y + v4.y) / 4,
    (v0.z + v1.z + v5.z + v4.z) / 4
  );
  const backCenter = new Vector3(
    (v2.x + v3.x + v7.x + v6.x) / 4,
    (v2.y + v3.y + v7.y + v6.y) / 4,
    (v2.z + v3.z + v7.z + v6.z) / 4
  );
  const centerVector = new Vector3().subVectors(backCenter, frontCenter);
  const thicknessDir = centerVector.clone().normalize();
  const frontOutward = thicknessDir.clone();
  const backOutward = thicknessDir.clone().multiplyScalar(1);
  const outwardShift = faceThickness / 2 + faceDistance;
  const inwardShift = faceThickness / 2 - faceDistance;

  element.holes.forEach((holeID) => {
    const holeData = layer.holes[holeID];

    const holeWidth = holeData.properties.width.length;
    const holeHeight = holeData.properties.height.length;
    const holeAltitude = holeData.properties.altitude.length;
    const offset = inverted ? 1 - holeData.offset : holeData.offset;
    const holeDistance = offset * distance;

    const holeGeometry = new BoxGeometry(
      holeWidth,
      holeHeight,
      thickness + faceThickness * 2 + faceDistance * 2
    );
    const holeMesh = new Mesh(holeGeometry);

    holeMesh.position.set(
      holeDistance - distance / 2,
      -(height / 2) + holeAltitude + holeHeight / 2,
      0
    );

    holeMesh.updateMatrix();

    frontFace = CSG.subtract(frontFace, holeMesh);
    backFace = CSG.subtract(backFace, holeMesh);
  });

  [frontFace, backFace].forEach((face) => {
    face.position.y += height / 2;
    face.position.x += halfDistance * cosAlpha;
    face.position.z -= halfDistance * sinAlpha;
    face.rotation.y = alpha;
    face.castShadow = true;
    face.receiveShadow = true;
  });

  frontFace.translateOnAxis(frontOutward, inwardShift);
  backFace.translateOnAxis(backOutward, outwardShift);

  frontFace.name = 'frontFace';
  backFace.name = 'backFace';

  (frontFace as any).userData = {
    surfaceType: 'front',
    wallId: element.id,
    wallLength: distance,
    wallHeight: height,
  };

  (backFace as any).userData = {
    surfaceType: 'back',
    wallId: element.id,
    wallLength: distance,
    wallHeight: height,
  };

  const merged = new Group();
  merged.add(soul, frontFace, backFace);

  return merged;
}

export function updatedWall(
  element: Line,
  layer: Layer,
  scene: Scene,
  textures: CatalogElementTextures,
  mesh: Object3D<Object3DEventMap>,
  oldElement: Line,
  differences: string[],
  selfDestroy: () => void,
  selfBuild: () => void
) {
  const noPerf = () => {
    selfDestroy();
    return selfBuild();
  };

  const soul = mesh.getObjectByName('soul') as Mesh;
  const frontFace = mesh.getObjectByName('frontFace') as Mesh;
  const backFace = mesh.getObjectByName('backFace') as Mesh;

  if (differences[0] == 'selected') {
    const soulMesh = soul as Mesh;
    if (Array.isArray(soulMesh.material)) {
      const sideMat = soulMesh.material[2] as MeshStandardMaterial;
      sideMat.color.set(
        element.selected ? SharedStyle.MESH_SELECTED : 0xd3d3d3
      );
      sideMat.needsUpdate = true;
    }
  } else if (differences[0] == 'properties') {
    if (differences[1] == 'thickness') {
      const newThickness = element.properties.thickness.length;
      const oldThickness = oldElement.properties.thickness.length;
      const halfNewThickness = newThickness / 2;
      const texturedFaceDistance = halfNewThickness + 1;
      const originalThickness = oldThickness / soul.scale.z;
      const alpha = soul.rotation.y;

      const xTemp = texturedFaceDistance * Math.cos(alpha - halfPI);
      const zTemp = texturedFaceDistance * Math.sin(alpha - halfPI);

      soul.scale.set(1, 1, newThickness / originalThickness);

      frontFace.position.x = soul.position.x + xTemp;
      frontFace.position.z = soul.position.z + zTemp;

      backFace.position.x = soul.position.x - xTemp;
      backFace.position.z = soul.position.z - zTemp;
      return noPerf();
    } else return noPerf();
  } else return noPerf();

  return mesh;
}