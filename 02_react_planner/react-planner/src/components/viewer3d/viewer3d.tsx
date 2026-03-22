import React, { Component } from 'react';

import convert from 'convert-units';
import * as Three from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass';
import { SMAAPass } from 'three/examples/jsm/postprocessing/SMAAPass';

import { State } from '../../models';
import ReactPlannerContext from '../../react-planner-context';
import * as SharedStyle from '../../shared-style';
import { diff } from '../../utils/history';

import { parseData, PlanData, updateScene } from './scene-creator';
import { disposeScene } from './three-memory-cleaner';

interface Scene3DViewerProps {
  state: State;
  width: number;
  height: number;
}

type HighlightEntry = {
  mesh: Three.Mesh;
  originalMaterial: Three.Material;
};

type SurfaceAppearance = {
  color: string | null;
  textureUri: string | null;
  dimensions: { w: number; h: number } | null;
};

export default class Scene3DViewer extends Component<Scene3DViewerProps, {}> {
  static contextType = ReactPlannerContext;
  declare context: React.ContextType<typeof ReactPlannerContext>;

  lastMousePosition: { x: number; y: number } = { x: 0, y: 0 };
  width: number;
  height: number;
  renderingID = 0;
  renderer: Three.WebGLRenderer;
  composer: EffectComposer | undefined;

  canvasWrapper: React.RefObject<null | HTMLDivElement>;

  camera: Three.PerspectiveCamera | undefined;
  scene3D: Three.Scene | undefined;
  planData: PlanData | undefined;
  orbitController: OrbitControls | undefined;

  highlightedMeshes: Map<string, HighlightEntry>;
  highlightedSurfaceIds: Set<string>;
  appliedSurfaceAppearance: Map<string, SurfaceAppearance>;
  rawOriginalMaterials: Map<string, Three.Material>;
  appliedSurfaceTextures: Map<string, Three.Texture>;
  textureLoader: Three.TextureLoader;

  mouseDownEvent: undefined | ((event: MouseEvent) => void);
  mouseUpEvent: undefined | ((event: MouseEvent) => void);
  restoreHighlightsEvent: undefined | ((event: Event) => void);
  applySurfaceColorsEvent: undefined | ((event: Event) => void);

  constructor(props: Scene3DViewerProps) {
    super(props);

    this.width = props.width;
    this.height = props.height;
    this.canvasWrapper = React.createRef<HTMLDivElement>();
    this.highlightedMeshes = new Map<string, HighlightEntry>();
    this.highlightedSurfaceIds = new Set<string>();
    this.appliedSurfaceAppearance = new Map<string, SurfaceAppearance>();
    this.rawOriginalMaterials = new Map<string, Three.Material>();
    this.appliedSurfaceTextures = new Map<string, Three.Texture>();
    this.textureLoader = new Three.TextureLoader();

    this.renderer =
      (window as any).__threeRenderer ||
      new Three.WebGLRenderer({
        preserveDrawingBuffer: true,
        antialias: true,
      });
    (window as any).__threeRenderer = this.renderer;
  }

  private getMeshKey(mesh: Three.Mesh) {
    return `${mesh.uuid}:${mesh.name}`;
  }

  private isSelectableFace(mesh: Three.Object3D): mesh is Three.Mesh {
    return (
      mesh instanceof Three.Mesh &&
      (mesh.name === 'frontFace' ||
        mesh.name === 'backFace' ||
        mesh.name === 'floor') &&
      !Array.isArray((mesh as Three.Mesh).material)
    );
  }

  private getSurfaceIdForMesh(mesh: Three.Mesh) {
    if (mesh.name === 'floor') {
      const areaId = mesh.userData?.areaId;
      return areaId ? `area::${areaId}` : null;
    }

    const wallId = mesh.userData?.wallId;
    const surfaceType = mesh.userData?.surfaceType;

    if (wallId && surfaceType) {
      return `${wallId}:${surfaceType}`;
    }

    return null;
  }

  private createHighlightMaterial(
    baseMaterial: Three.Material,
    highlightColor: number | string = 0x2196f3
  ) {
    const highlightMaterial = (baseMaterial as any).clone();

    if ('emissive' in highlightMaterial && highlightMaterial.emissive) {
      highlightMaterial.emissive = new Three.Color(highlightColor as any);
      highlightMaterial.emissiveIntensity = 0.28;
    }

    highlightMaterial.needsUpdate = true;
    return highlightMaterial as Three.Material;
  }

  private createAppliedColorMaterial(
    baseMaterial: Three.Material,
    color: string
  ) {
    const appliedMaterial = (baseMaterial as any).clone();

    const textureKeys = [
      'map',
      'normalMap',
      'roughnessMap',
      'metalnessMap',
      'aoMap',
      'bumpMap',
      'alphaMap',
      'displacementMap',
      'emissiveMap',
      'lightMap'
    ];

    textureKeys.forEach((key) => {
      if (key in appliedMaterial) {
        appliedMaterial[key] = null;
      }
    });

    if ('color' in appliedMaterial && appliedMaterial.color) {
      appliedMaterial.color = new Three.Color(color);
    }

    if ('emissive' in appliedMaterial && appliedMaterial.emissive) {
      appliedMaterial.emissive = new Three.Color(0x000000);
      appliedMaterial.emissiveIntensity = 0;
    }

    if ('roughness' in appliedMaterial) {
      appliedMaterial.roughness = 0.88;
    }

    if ('metalness' in appliedMaterial) {
      appliedMaterial.metalness = 0;
    }

    appliedMaterial.needsUpdate = true;
    return appliedMaterial as Three.Material;
  }

  private createAppliedTextureMaterial(
    baseMaterial: Three.Material,
    texture: Three.Texture
  ) {
    const appliedMaterial = (baseMaterial as any).clone();

    const textureKeys = [
      'map',
      'normalMap',
      'roughnessMap',
      'metalnessMap',
      'aoMap',
      'bumpMap',
      'alphaMap',
      'displacementMap',
      'emissiveMap',
      'lightMap'
    ];

    textureKeys.forEach((key) => {
      if (key in appliedMaterial) {
        appliedMaterial[key] = null;
      }
    });

    appliedMaterial.map = texture;

    if ('color' in appliedMaterial && appliedMaterial.color) {
      appliedMaterial.color = new Three.Color(0xffffff);
    }

    if ('emissive' in appliedMaterial && appliedMaterial.emissive) {
      appliedMaterial.emissive = new Three.Color(0x000000);
      appliedMaterial.emissiveIntensity = 0;
    }

    if ('roughness' in appliedMaterial) {
      appliedMaterial.roughness = 0.92;
    }

    if ('metalness' in appliedMaterial) {
      appliedMaterial.metalness = 0;
    }

    appliedMaterial.needsUpdate = true;
    return appliedMaterial as Three.Material;
  }

  private clearAllHighlights(clearSurfaceIds: boolean = true) {
    this.highlightedMeshes.forEach((entry) => {
      entry.mesh.material = entry.originalMaterial;
    });
    this.highlightedMeshes.clear();

    if (clearSurfaceIds) {
      this.highlightedSurfaceIds.clear();
    }
  }

  private removeHighlight(mesh: Three.Mesh) {
    const key = this.getMeshKey(mesh);
    const entry = this.highlightedMeshes.get(key);
    if (!entry) return;

    entry.mesh.material = entry.originalMaterial;
    this.highlightedMeshes.delete(key);

    const surfaceId = this.getSurfaceIdForMesh(mesh);
    if (surfaceId) {
      this.highlightedSurfaceIds.delete(surfaceId);
    }
  }

  private addHighlight(mesh: Three.Mesh) {
    const key = this.getMeshKey(mesh);
    if (this.highlightedMeshes.has(key)) return;

    const baseMaterial = mesh.material;
    if (Array.isArray(baseMaterial) || !baseMaterial) return;

    const highlightMaterial = this.createHighlightMaterial(baseMaterial);

    this.highlightedMeshes.set(key, {
      mesh,
      originalMaterial: baseMaterial
    });

    const surfaceId = this.getSurfaceIdForMesh(mesh);
    if (surfaceId) {
      this.highlightedSurfaceIds.add(surfaceId);
    }

    mesh.material = highlightMaterial;
  }

  private toggleHighlight(mesh: Three.Mesh) {
    const key = this.getMeshKey(mesh);

    if (this.highlightedMeshes.has(key)) {
      this.removeHighlight(mesh);
    } else {
      this.addHighlight(mesh);
    }
  }

  private disposeTextureForSurface(surfaceId: string) {
    const texture = this.appliedSurfaceTextures.get(surfaceId);
    if (texture) {
      texture.dispose();
      this.appliedSurfaceTextures.delete(surfaceId);
    }
  }

  private getMeshSurfaceSizeM(mesh: Three.Mesh) {
    const unit = this.context.catalog.unit;
    const metersPerUnit = convert(1).from(unit).to('m');

    const box = new Three.Box3().setFromObject(mesh);
    const size = new Three.Vector3();
    box.getSize(size);

    const x = Math.abs(size.x) * metersPerUnit;
    const y = Math.abs(size.y) * metersPerUnit;
    const z = Math.abs(size.z) * metersPerUnit;

    if (mesh.name === 'floor') {
      const width = Math.max(x, z);
      const height = Math.min(x, z) || width;
      return { width, height };
    }

    return {
      width: Math.max(x, z),
      height: y
    };
  }

  private applyColorToMesh(mesh: Three.Mesh, surfaceId: string, color: string) {
    const key = this.getMeshKey(mesh);
    const highlightEntry = this.highlightedMeshes.get(key);
    const currentBaseMaterial = highlightEntry?.originalMaterial || mesh.material;

    if (Array.isArray(currentBaseMaterial) || !currentBaseMaterial) return;

    if (!this.rawOriginalMaterials.has(surfaceId)) {
      this.rawOriginalMaterials.set(surfaceId, currentBaseMaterial);
    }

    const rawOriginalMaterial =
      this.rawOriginalMaterials.get(surfaceId) || currentBaseMaterial;

    this.disposeTextureForSurface(surfaceId);

    const appliedMaterial = this.createAppliedColorMaterial(
      rawOriginalMaterial,
      color
    );

    if (highlightEntry) {
      highlightEntry.originalMaterial = appliedMaterial;
      mesh.material = this.createHighlightMaterial(appliedMaterial);
    } else {
      mesh.material = appliedMaterial;
    }
  }

  private applyTextureToMesh(
    mesh: Three.Mesh,
    surfaceId: string,
    textureUri: string,
    dimensions: { w: number; h: number }
  ) {
    const key = this.getMeshKey(mesh);
    const highlightEntry = this.highlightedMeshes.get(key);
    const currentBaseMaterial = highlightEntry?.originalMaterial || mesh.material;

    if (Array.isArray(currentBaseMaterial) || !currentBaseMaterial) return;

    if (!this.rawOriginalMaterials.has(surfaceId)) {
      this.rawOriginalMaterials.set(surfaceId, currentBaseMaterial);
    }

    const rawOriginalMaterial =
      this.rawOriginalMaterials.get(surfaceId) || currentBaseMaterial;

    this.disposeTextureForSurface(surfaceId);

    const texture = this.textureLoader.load(
      textureUri,
      () => {
        if ((mesh.material as any)?.needsUpdate !== undefined) {
          (mesh.material as any).needsUpdate = true;
        }
      },
      undefined,
      () => {
        const appearance = this.appliedSurfaceAppearance.get(surfaceId);
        if (appearance?.color) {
          this.applyColorToMesh(mesh, surfaceId, appearance.color);
        } else {
          this.clearAppliedColorFromMesh(mesh, surfaceId);
        }
      }
    );

    texture.wrapS = Three.RepeatWrapping;
    texture.wrapT = Three.RepeatWrapping;
    texture.colorSpace = Three.SRGBColorSpace;

    if (mesh.name === 'floor') {
      const unit = this.context.catalog.unit;
      const metersPerUnit = convert(1).from(unit).to('m');

      texture.repeat.set(
        Math.max(metersPerUnit / dimensions.w, 0.0001),
        Math.max(metersPerUnit / dimensions.h, 0.0001)
      );
    } else {
      const surfaceSize = this.getMeshSurfaceSizeM(mesh);

      texture.repeat.set(
        Math.max(surfaceSize.width / dimensions.w, 0.01),
        Math.max(surfaceSize.height / dimensions.h, 0.01)
      );
    }

    this.appliedSurfaceTextures.set(surfaceId, texture);

    const appliedMaterial = this.createAppliedTextureMaterial(
      rawOriginalMaterial,
      texture
    );

    if (highlightEntry) {
      highlightEntry.originalMaterial = appliedMaterial;
      mesh.material = this.createHighlightMaterial(appliedMaterial);
    } else {
      mesh.material = appliedMaterial;
    }
  }

  private clearAppliedColorFromMesh(mesh: Three.Mesh, surfaceId: string) {
    const key = this.getMeshKey(mesh);
    const highlightEntry = this.highlightedMeshes.get(key);
    const rawOriginalMaterial = this.rawOriginalMaterials.get(surfaceId);

    this.disposeTextureForSurface(surfaceId);

    if (!rawOriginalMaterial) return;

    if (highlightEntry) {
      highlightEntry.originalMaterial = rawOriginalMaterial;
      mesh.material = this.createHighlightMaterial(rawOriginalMaterial);
    } else {
      mesh.material = rawOriginalMaterial;
    }

    this.rawOriginalMaterials.delete(surfaceId);
  }

  private applyAppearanceToMesh(
    mesh: Three.Mesh,
    surfaceId: string,
    appearance: SurfaceAppearance | null
  ) {
    if (!appearance) {
      this.clearAppliedColorFromMesh(mesh, surfaceId);
      return;
    }

    if (appearance.textureUri && appearance.dimensions) {
      this.applyTextureToMesh(
        mesh,
        surfaceId,
        appearance.textureUri,
        appearance.dimensions
      );
      return;
    }

    if (appearance.color) {
      this.applyColorToMesh(mesh, surfaceId, appearance.color);
      return;
    }

    this.clearAppliedColorFromMesh(mesh, surfaceId);
  }

  private applySurfaceColors(colorMap: Record<string, SurfaceAppearance | null>) {
    if (!this.planData || !this.planData.plan) return;

    Object.entries(colorMap).forEach(([surfaceId, appearance]) => {
      if (appearance) {
        this.appliedSurfaceAppearance.set(surfaceId, appearance);
      } else {
        this.appliedSurfaceAppearance.delete(surfaceId);
      }
    });

    this.planData.plan.traverse((obj) => {
      if (!(obj instanceof Three.Mesh)) return;

      const mesh = obj as Three.Mesh;
      const material = mesh.material as any;
      if (material) {
        mesh.castShadow = true;
        mesh.receiveShadow = mesh.name === 'floor';
      }

      if (!this.isSelectableFace(obj)) return;

      const surfaceId = this.getSurfaceIdForMesh(obj);
      if (!surfaceId) return;

      if (Object.prototype.hasOwnProperty.call(colorMap, surfaceId)) {
        const nextAppearance = colorMap[surfaceId];
        this.applyAppearanceToMesh(obj, surfaceId, nextAppearance);
        return;
      }

      const storedAppearance = this.appliedSurfaceAppearance.get(surfaceId);
      if (storedAppearance) {
        this.applyAppearanceToMesh(obj, surfaceId, storedAppearance);
      }
    });
  }

  private reapplyStoredSurfaceColors() {
    if (!this.planData || !this.planData.plan) return;
    if (!this.appliedSurfaceAppearance.size) return;

    this.planData.plan.traverse((obj) => {
      if (!this.isSelectableFace(obj)) return;

      const surfaceId = this.getSurfaceIdForMesh(obj);
      if (!surfaceId) return;

      const storedAppearance = this.appliedSurfaceAppearance.get(surfaceId);
      if (!storedAppearance) return;

      this.applyAppearanceToMesh(obj, surfaceId, storedAppearance);
    });
  }

  private restoreHighlightsBySurfaceIds(surfaceIds: string[]) {
    this.clearAllHighlights(false);

    if (!this.planData || !this.planData.plan) return;

    this.highlightedSurfaceIds = new Set(surfaceIds);

    if (!surfaceIds.length) return;

    const wanted = new Set(surfaceIds);

    this.planData.plan.traverse((obj) => {
      if (!this.isSelectableFace(obj)) return;

      const surfaceId = this.getSurfaceIdForMesh(obj);
      if (!surfaceId) return;

      if (wanted.has(surfaceId)) {
        this.addHighlight(obj);
      }
    });
  }

  componentDidMount() {
    const { state } = this.props;

    const scene3D = new Three.Scene();

    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.outputColorSpace = Three.SRGBColorSpace;
    this.renderer.toneMapping = Three.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.0;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = Three.PCFSoftShadowMap;
    this.renderer.setClearColor(new Three.Color('#e8e8e8'));
    this.renderer.setSize(this.width, this.height);

    const planData = parseData(state.scene, this.context);

    scene3D.add(planData.plan);
    scene3D.add(planData.grid);

    const aspectRatio = this.width / this.height;
    const camera = new Three.PerspectiveCamera(45, aspectRatio, 1, 300000);

    scene3D.add(camera);

    const cameraPositionX =
      -(planData.boundingBox.max.x - planData.boundingBox.min.x) / 2;
    const cameraPositionY =
      ((planData.boundingBox.max.y - planData.boundingBox.min.y) / 2) * 10;
    const cameraPositionZ =
      (planData.boundingBox.max.z - planData.boundingBox.min.z) / 2;

    camera.position.set(cameraPositionX, cameraPositionY, cameraPositionZ);
    camera.up = new Three.Vector3(0, 1, 0);

    const ambient = new Three.AmbientLight(0xffffff, 0.3);
    scene3D.add(ambient);

    const hemi = new Three.HemisphereLight(0xf0f0ff, 0xb0a090, 0.4);
    scene3D.add(hemi);

    const spotLight1 = new Three.SpotLight(0xffffff, 0.3);
    spotLight1.position.set(cameraPositionX, cameraPositionY, cameraPositionZ);
    spotLight1.angle = Math.PI / 5;
    spotLight1.penumbra = 0.35;
    spotLight1.decay = 1.2;
    scene3D.add(spotLight1);

    const dirLight = new Three.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(
      cameraPositionX + 300,
      cameraPositionY + 400,
      cameraPositionZ + 300
    );
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    dirLight.shadow.camera.near = 1;
    dirLight.shadow.camera.far = Math.max(cameraPositionY * 3, 2000);
    const shadowExtent = Math.max(Math.abs(cameraPositionZ) * 2, 1500);
    (dirLight.shadow.camera as Three.OrthographicCamera).left = -shadowExtent;
    (dirLight.shadow.camera as Three.OrthographicCamera).right = shadowExtent;
    (dirLight.shadow.camera as Three.OrthographicCamera).top = shadowExtent;
    (dirLight.shadow.camera as Three.OrthographicCamera).bottom = -shadowExtent;
    dirLight.shadow.bias = -0.0008;
    scene3D.add(dirLight);

    planData.plan.traverse((obj) => {
      if (!(obj instanceof Three.Mesh)) return;
      obj.castShadow =
        obj.name === 'soul' ||
        obj.name === 'frontFace' ||
        obj.name === 'backFace';
      obj.receiveShadow = obj.name === 'floor';
    });

    const toIntersect = [planData.plan];
    const mouse = new Three.Vector2();
    const raycaster = new Three.Raycaster();

    const notifySurfacesCleared = () => {
      window.parent?.postMessage(
        {
          protocolVersion: 1,
          type: 'SURFACES_CLEARED',
          payload: {}
        },
        '*'
      );
    };

    this.restoreHighlightsEvent = (event: Event) => {
      const customEvent = event as CustomEvent<{ surfaceIds?: string[] }>;
      const surfaceIds = customEvent.detail?.surfaceIds || [];
      this.restoreHighlightsBySurfaceIds(surfaceIds);
    };

    this.applySurfaceColorsEvent = (event: Event) => {
      const customEvent = event as CustomEvent<{
        surfaces?: Record<string, SurfaceAppearance | null>;
      }>;
      const surfaces = customEvent.detail?.surfaces || {};
      this.applySurfaceColors(surfaces);
    };

    window.addEventListener(
      'PLANO_RESTORE_HIGHLIGHTS',
      this.restoreHighlightsEvent as EventListener
    );

    window.addEventListener(
      'PLANO_APPLY_SURFACE_COLORS',
      this.applySurfaceColorsEvent as EventListener
    );

    this.mouseDownEvent = (event: MouseEvent) => {
      this.lastMousePosition.x = (event.offsetX / this.width) * 2 - 1;
      this.lastMousePosition.y = (-event.offsetY / this.height) * 2 + 1;
    };

    this.mouseUpEvent = (event: MouseEvent) => {
      event.preventDefault();

      mouse.x = (event.offsetX / this.width) * 2 - 1;
      mouse.y = -(event.offsetY / this.height) * 2 + 1;

      if (
        Math.abs(mouse.x - this.lastMousePosition.x) <= 0.02 &&
        Math.abs(mouse.y - this.lastMousePosition.y) <= 0.02
      ) {
        raycaster.setFromCamera(mouse, camera);

        const intersects = raycaster.intersectObjects(toIntersect, true);

        if (intersects.length > 0 && !isNaN(intersects[0].distance)) {
          const object = intersects[0].object as any;

          if (this.isSelectableFace(object)) {
            this.toggleHighlight(object);

            const mesh = object as Three.Mesh;
            const unit = this.context.catalog.unit;
            const metersPerUnit = convert(1).from(unit).to('m');

            if (mesh.name === 'floor') {
              const areaId = mesh.userData?.areaId;
              const sceneArea = mesh.userData?.sceneArea;

              if (areaId && typeof sceneArea === 'number') {
                const areaM2 =
                  Math.round(sceneArea * metersPerUnit * metersPerUnit * 100) /
                  100;

                window.parent?.postMessage(
                  {
                    protocolVersion: 1,
                    type: 'SURFACE_SELECTED',
                    payload: {
                      surfaceId: `area::${areaId}`,
                      wallId: areaId,
                      surfaceType: 'floor',
                      areaM2
                    }
                  },
                  '*'
                );
              }

              return;
            }

            const wallId = mesh.userData?.wallId;
            const surfaceType = mesh.userData?.surfaceType;
            const wallLength = mesh.userData?.wallLength;
            const wallHeight = mesh.userData?.wallHeight;

            if (wallId && surfaceType) {
              const surfaceId = `${wallId}:${surfaceType}`;

              let lengthM: number | undefined;
              let heightM: number | undefined;
              let areaM2: number | undefined;

              if (
                typeof wallLength === 'number' &&
                typeof wallHeight === 'number'
              ) {
                lengthM = Math.round(wallLength * metersPerUnit * 100) / 100;
                heightM = Math.round(wallHeight * metersPerUnit * 100) / 100;
                areaM2 = Math.round(lengthM * heightM * 100) / 100;
              }

              window.parent?.postMessage(
                {
                  protocolVersion: 1,
                  type: 'SURFACE_SELECTED',
                  payload: {
                    surfaceId,
                    wallId,
                    surfaceType,
                    lengthM,
                    heightM,
                    areaM2
                  }
                },
                '*'
              );
            }
          } else {
            this.clearAllHighlights();
            notifySurfacesCleared();
            this.context.projectActions.unselectAll();
          }
        } else {
          this.clearAllHighlights();
          notifySurfacesCleared();
          this.context.projectActions.unselectAll();
        }
      }
    };

    if (this.mouseDownEvent) {
      this.renderer.domElement.addEventListener(
        'mousedown',
        this.mouseDownEvent
      );
    }

    if (this.mouseUpEvent) {
      this.renderer.domElement.addEventListener(
        'mouseup',
        this.mouseUpEvent
      );
    }

    this.renderer.domElement.style.display = 'block';

    if (this.canvasWrapper.current) {
      this.canvasWrapper.current.appendChild(this.renderer.domElement);
    }

    const orbitController = new OrbitControls(camera, this.renderer.domElement);
    orbitController.enableDamping = true;
    orbitController.dampingFactor = 0.08;
    orbitController.screenSpacePanning = true;

    const spotLightTarget = new Three.Object3D();
    spotLightTarget.name = 'spotLightTarget';

    spotLightTarget.position.set(
      orbitController.target.x,
      orbitController.target.y,
      orbitController.target.z
    );

    scene3D.add(spotLightTarget);
    spotLight1.target = spotLightTarget;

    const composer = new EffectComposer(this.renderer);
    composer.setSize(this.width, this.height);
    composer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

    const renderPass = new RenderPass(scene3D, camera);
    composer.addPass(renderPass);

    const smaaPass = new SMAAPass();
    composer.addPass(smaaPass);

    const bloomPass = new UnrealBloomPass(
      new Three.Vector2(this.width, this.height),
      0.08,
      0.25,
      0.85
    );
    composer.addPass(bloomPass);

    this.composer = composer;

    const render = () => {
      orbitController.update();

      spotLight1.position.set(
        camera.position.x,
        camera.position.y,
        camera.position.z
      );

      spotLightTarget.position.set(
        orbitController.target.x,
        orbitController.target.y,
        orbitController.target.z
      );

      camera.updateMatrix();
      camera.updateMatrixWorld();

      for (const elemID in planData.sceneGraph.LODs) {
        planData.sceneGraph.LODs[elemID].update(camera);
      }

      this.composer?.render();

      this.renderingID = requestAnimationFrame(render);
    };

    render();

    this.camera = camera;
    this.scene3D = scene3D;
    this.orbitController = orbitController;
    this.planData = planData;
  }

  componentWillUnmount() {
    cancelAnimationFrame(this.renderingID);
    this.orbitController?.dispose();

    this.clearAllHighlights();

    if (this.restoreHighlightsEvent) {
      window.removeEventListener(
        'PLANO_RESTORE_HIGHLIGHTS',
        this.restoreHighlightsEvent as EventListener
      );
    }

    if (this.applySurfaceColorsEvent) {
      window.removeEventListener(
        'PLANO_APPLY_SURFACE_COLORS',
        this.applySurfaceColorsEvent as EventListener
      );
    }

    if (this.mouseDownEvent) {
      this.renderer.domElement.removeEventListener(
        'mousedown',
        this.mouseDownEvent
      );
    }

    if (this.mouseUpEvent) {
      this.renderer.domElement.removeEventListener(
        'mouseup',
        this.mouseUpEvent
      );
    }

    if (this.scene3D) {
      disposeScene(this.scene3D);

      if (this.planData) {
        this.scene3D.remove(this.planData.plan);
        this.scene3D.remove(this.planData.grid);
      }
    }

    this.composer?.dispose();
    this.composer = undefined;
    this.scene3D = undefined;
    this.planData = undefined;
    this.camera = undefined;
    this.orbitController = undefined;
    this.highlightedMeshes.clear();
    this.highlightedSurfaceIds.clear();
    this.appliedSurfaceAppearance.clear();
    this.rawOriginalMaterials.clear();

    this.appliedSurfaceTextures.forEach((texture) => texture.dispose());
    this.appliedSurfaceTextures.clear();

    this.renderer.renderLists.dispose();
  }

  componentDidUpdate(prevProps: Scene3DViewerProps) {
    const { width, height } = this.props;

    this.width = width;
    this.height = height;

    if (this.camera) {
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
    }

    if (prevProps && this.props.state.scene !== prevProps.state.scene) {
      const changedValues = diff(prevProps.state.scene, this.props.state.scene);
      const highlightedSurfaceIds = Array.from(this.highlightedSurfaceIds);

      if (this.planData) {
        updateScene(
          this.planData,
          this.props.state.scene,
          prevProps.state.scene,
          changedValues,
          this.context
        );
      }

      this.highlightedMeshes.clear();
      this.rawOriginalMaterials.clear();
      this.appliedSurfaceTextures.forEach((texture) => texture.dispose());
      this.appliedSurfaceTextures.clear();
      this.reapplyStoredSurfaceColors();

      if (this.planData) {
        this.planData.plan.traverse((obj) => {
          if (!(obj instanceof Three.Mesh)) return;
          obj.castShadow =
            obj.name === 'soul' ||
            obj.name === 'frontFace' ||
            obj.name === 'backFace';
          obj.receiveShadow = obj.name === 'floor';
        });
      }

      if (highlightedSurfaceIds.length) {
        this.restoreHighlightsBySurfaceIds(highlightedSurfaceIds);
      }
    }

    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(width, height);
    this.composer?.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.composer?.setSize(width, height);
  }

  render() {
    return (
      <div style={{ position: 'relative', width: '100%', height: '100%' }}>
        <div ref={this.canvasWrapper} />
      </div>
    );
  }
}