'use strict';

import React from 'react';
import * as Three from 'three';

import { State } from '../../models';
import ReactPlannerContext from '../../react-planner-context';
import * as SharedStyle from '../../shared-style';
import { diff } from '../../utils/history';

import {
  firstPersonOnKeyDown,
  firstPersonOnKeyUp
} from './libs/first-person-controls';
import PointerLockControls from './libs/pointer-lock-controls';
import { initPointerLock } from './pointer-lock-navigation';
import { parseData, PlanData, updateScene } from './scene-creator';
import { disposeScene } from './three-memory-cleaner';

interface Viewer3DFirstPersonProps {
  state: State;
  width: number;
  height: number;
}

class Viewer3DFirstPerson extends React.Component<Viewer3DFirstPersonProps> {
  static contextType = ReactPlannerContext;
  declare context: React.ContextType<typeof ReactPlannerContext>;

  private renderer: Three.WebGLRenderer;
  private stopRendering = false;
  private scene3D: Three.Scene | null = null;
  private sceneOnTop: Three.Scene | null = null;
  private camera: Three.PerspectiveCamera | null = null;
  private planData: PlanData | null = null;
  private controls: PointerLockControls | null = null;
  private pointerlockChangeEvent: any = null;
  private requestPointerLockEvent: any = null;
  private keyDownEvent: any = null;
  private keyUpEvent: any = null;
  private mouseDownEvent: any = null;
  private canvasWrapper = React.createRef<HTMLDivElement>();

  // === STEP 1: shading state (single surface only) ===
  private shadedMesh: Three.Mesh | null = null;
  private originalMaterial: Three.Material | null = null;

  constructor(props: Viewer3DFirstPersonProps) {
    super(props);
    this.renderer =
      (window as any).__threeRenderer ||
      new Three.WebGLRenderer({ preserveDrawingBuffer: true });
    (window as any).__threeRenderer = this.renderer;
  }

  private clearShading() {
    if (this.shadedMesh && this.originalMaterial) {
      this.shadedMesh.material = this.originalMaterial;
    }
    this.shadedMesh = null;
    this.originalMaterial = null;
  }

  private shadeMesh(mesh: Three.Mesh) {
    if (this.shadedMesh === mesh) return;

    this.clearShading();

    this.shadedMesh = mesh;
    this.originalMaterial = mesh.material as Three.Material;

    const shadedMaterial = (mesh.material as Three.Material).clone();
    shadedMaterial.transparent = true;
    shadedMaterial.opacity = 0.3;
    shadedMaterial.depthWrite = false;

    mesh.material = shadedMaterial;
  }

  componentDidMount() {
    let prevTime = performance.now();
    const velocity = new Three.Vector3();
    const direction = new Three.Vector3();
    let moveForward = false;
    let moveBackward = false;
    let moveLeft = false;
    let moveRight = false;
    let canJump = false;

    const { width, height, state } = this.props;
    const { projectActions } = this.context;

    this.renderer.setClearColor(new Three.Color(SharedStyle.COLORS.white));
    this.renderer.setSize(width, height);

    const scene3D = new Three.Scene();
    const sceneOnTop = new Three.Scene();
    const planData = parseData(state.scene, this.context);
    scene3D.add(planData.plan);

    const camera = new Three.PerspectiveCamera(45, width / height, 0.1, 300000);
    sceneOnTop.add(camera);
    camera.position.set(0, 0, 0);
    camera.up = new Three.Vector3(0, 1, 0);

    scene3D.add(new Three.AmbientLight(0xafafaf));
    scene3D.add(new Three.HemisphereLight(0xffffff, 0x666666, 0.5));

    const pointLight = new Three.PointLight(SharedStyle.COLORS.white, 0.4, 1000);
    scene3D.add(pointLight);

    const dirLight = new Three.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(300, 400, 300);
    scene3D.add(dirLight);

    document.body.requestPointerLock?.();

    const humanHeight = 170;
    let yInitialPosition =
      planData.boundingBox.min.y +
      (planData.boundingBox.min.y - planData.boundingBox.max.y) / 2 +
      humanHeight;

    const { controls, pointerlockChangeEvent, requestPointerLockEvent } =
      initPointerLock(camera, this.renderer.domElement);

    controls.getObject().position.set(-50, yInitialPosition, -100);
    sceneOnTop.add(controls.getObject());

    this.keyDownEvent = (e: KeyboardEvent) => {
      ({ moveForward, moveLeft, moveBackward, moveRight, canJump } =
        firstPersonOnKeyDown(
          e,
          moveForward,
          moveLeft,
          moveBackward,
          moveRight,
          canJump,
          velocity
        ));
    };

    this.keyUpEvent = (e: KeyboardEvent) => {
      ({ moveForward, moveLeft, moveBackward, moveRight, canJump } =
        firstPersonOnKeyUp(
          e,
          moveForward,
          moveLeft,
          moveBackward,
          moveRight,
          canJump
        ));
    };

    document.addEventListener('keydown', this.keyDownEvent);
    document.addEventListener('keyup', this.keyUpEvent);

    const raycaster = new Three.Raycaster();
    const mouseVector = new Three.Vector2(0, 0);
    const toIntersect = [planData.plan];

    this.mouseDownEvent = (event: MouseEvent) => {
      if (!controls.enabled) return;

      event.preventDefault();
      raycaster.setFromCamera(mouseVector, camera);
      const intersects = raycaster.intersectObjects(toIntersect, true);

      if (intersects.length > 0 && intersects[0].object instanceof Three.Mesh) {
        const mesh = intersects[0].object;
        this.shadeMesh(mesh);
        (mesh as any).interact && (mesh as any).interact();
      } else {
        this.clearShading();
        projectActions.unselectAll();
      }
    };

    document.addEventListener('mousedown', this.mouseDownEvent, false);

    this.renderer.domElement.style.display = 'block';
    this.canvasWrapper.current!.appendChild(this.renderer.domElement);
    this.renderer.autoClear = false;

    const render = () => {
      if (!this.stopRendering && planData) {
        yInitialPosition = planData.boundingBox.min.y + humanHeight;
        const time = performance.now();
        const delta = (time - prevTime) / 1000;

        velocity.x -= velocity.x * 10 * delta;
        velocity.z -= velocity.z * 10 * delta;
        velocity.y -= 9.8 * 100 * delta;

        direction.z = Number(moveForward) - Number(moveBackward);
        direction.x = Number(moveLeft) - Number(moveRight);
        direction.normalize();

        if (moveForward || moveBackward)
          velocity.z -= direction.z * 400 * delta;
        if (moveLeft || moveRight)
          velocity.x -= direction.x * 400 * delta;

        controls.getObject().translateX(velocity.x * delta);
        controls.getObject().translateY(velocity.y * delta);
        controls.getObject().translateZ(velocity.z * delta);

        if (controls.getObject().position.y < yInitialPosition) {
          velocity.y = 0;
          controls.getObject().position.y = yInitialPosition;
          canJump = true;
        }

        prevTime = time;
        const p = controls.getObject().position;
        pointLight.position.set(p.x, p.y, p.z);

        for (const id in planData.sceneGraph.LODs)
          planData.sceneGraph.LODs[id].update(camera);

        this.renderer.clear();
        this.renderer.render(scene3D, camera);
        this.renderer.clearDepth();
        this.renderer.render(sceneOnTop, camera);

        requestAnimationFrame(render);
      }
    };

    render();

    this.scene3D = scene3D;
    this.sceneOnTop = sceneOnTop;
    this.camera = camera;
    this.planData = planData;
    this.controls = controls;
    this.pointerlockChangeEvent = pointerlockChangeEvent;
    this.requestPointerLockEvent = requestPointerLockEvent;
  }

  componentWillUnmount() {
    this.stopRendering = true;
    this.renderer.autoClear = true;

    document.removeEventListener('mousedown', this.mouseDownEvent);
    document.removeEventListener('keydown', this.keyDownEvent);
    document.removeEventListener('keyup', this.keyUpEvent);

    document.removeEventListener('pointerlockchange', this.pointerlockChangeEvent);
    document.removeEventListener(
      'mozpointerlockchange',
      this.pointerlockChangeEvent
    );
    document.removeEventListener(
      'webkitpointerlockchange',
      this.pointerlockChangeEvent
    );

    this.renderer.domElement.removeEventListener(
      'click',
      this.requestPointerLockEvent
    );

    if (this.scene3D && this.planData) {
      disposeScene(this.scene3D);
      this.scene3D.remove(this.planData.plan);
    }

    this.scene3D = null;
    this.planData = null;
    this.renderer.renderLists.dispose();
  }

  render() {
    return <div ref={this.canvasWrapper} />;
  }
}

export default Viewer3DFirstPerson;
