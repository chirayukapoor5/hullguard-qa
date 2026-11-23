import {
  AmbientLight, Box3, Color, DirectionalLight, EdgesGeometry, GridHelper, LineBasicMaterial,
  LineSegments, MeshStandardMaterial, PerspectiveCamera, Raycaster, Scene, Spherical, Vector2,
  Vector3, WebGLRenderer,
} from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';

const finish = { bottom: 0x758da0, side: 0x7194ae, bulkhead: 0x81afbf, stiffener: 0xf0ae76 };

export function mountViewer(host, content, components, onSelect, changedIds = []) {
  const model = new OBJLoader().parse(content);
  const byId = new Map(components.map(part => [part.id, part]));
  model.scale.setScalar(0.001);
  const meshes = model.children.filter(object => object.isMesh);
  if (meshes.length !== byId.size || new Set(meshes.map(mesh => mesh.name)).size !== byId.size ||
      meshes.some(mesh => !byId.has(mesh.name))) {
    throw new Error('The OBJ component inventory differs from the manifest.');
  }
  const center = new Box3().setFromObject(model).getCenter(new Vector3());
  model.position.sub(center);
  const scene = new Scene();
  scene.background = new Color(0x102738);
  scene.add(model, new AmbientLight(0xc6dcee, 2.0));
  const key = new DirectionalLight(0xffffff, 2.0);
  key.position.set(-1, -2, 4);
  scene.add(key);

  const ground = new GridHelper(12, 48, 0x426279, 0x263e51);
  ground.rotation.x = Math.PI / 2;
  ground.position.z = new Box3().setFromObject(model).min.z - 0.022;
  scene.add(ground);
  const renderer = new WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.domElement.tabIndex = 0;
  renderer.domElement.setAttribute('aria-label', 'Interactive OBJ. Arrow keys rotate, plus and minus zoom, Home resets.');
  host.append(renderer.domElement);

  const camera = new PerspectiveCamera(34, 1, 0.01, 70);
  camera.up.set(0, 0, 1);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.minDistance = 1.1;
  controls.maxDistance = 10;
  const changed = new Set(changedIds);
  for (const mesh of meshes) {
    mesh.material.dispose();
    const material = new MeshStandardMaterial({
      color: changed.has(mesh.name) ? 0xeea461 : finish[byId.get(mesh.name).kind],
      roughness: 0.78,
      metalness: 0.06,
    });
    mesh.material = material;
    mesh.userData.baseColor = material.color.getHex();
    const edges = new LineSegments(new EdgesGeometry(mesh.geometry), new LineBasicMaterial({ color: 0x24455a }));
    mesh.add(edges);
  }

  const draw = () => renderer.render(scene, camera);
  const fitDistance = () => (host.clientWidth / Math.max(1, host.clientHeight) < 1.14 ? 1.46 : 1);
  const reset = () => {
    camera.position.set(2.1, -2.6, 2.85).multiplyScalar(fitDistance());
    controls.target.set(0, 0, -0.035);
    controls.update();
    draw();
  };
  const resize = () => {
    camera.aspect = host.clientWidth / Math.max(1, host.clientHeight);
    camera.updateProjectionMatrix();
    renderer.setSize(host.clientWidth, host.clientHeight, false);
    draw();
  };
  const observer = new ResizeObserver(resize);
  observer.observe(host);
  controls.addEventListener('change', draw);
  resize();
  reset();

  const ray = new Raycaster();
  let pointerDown;
  renderer.domElement.addEventListener('pointerdown', event => {
    pointerDown = [event.clientX, event.clientY];
  });
  renderer.domElement.addEventListener('pointerup', event => {
    if (!pointerDown || event.button !== 0 ||
      Math.hypot(event.clientX - pointerDown[0], event.clientY - pointerDown[1]) > 5) return;
    const rect = renderer.domElement.getBoundingClientRect();
    ray.setFromCamera(new Vector2(
      2 * (event.clientX - rect.left) / rect.width - 1,
      1 - 2 * (event.clientY - rect.top) / rect.height,
    ), camera);
    const hit = ray.intersectObjects(meshes, false)[0];
    if (hit) onSelect(hit.object.name);
  });

  function zoom(factor) {
    const offset = camera.position.clone().sub(controls.target);
    offset.setLength(Math.min(controls.maxDistance, Math.max(controls.minDistance, offset.length() * factor)));
    camera.position.copy(controls.target).add(offset);
    controls.update();
    draw();
  }

  renderer.domElement.addEventListener('keydown', event => {
    if (event.key === 'Home') {
      event.preventDefault();
      reset();
      return;
    }
    if (['+', '=', '-'].includes(event.key)) {
      event.preventDefault();
      zoom(event.key === '-' ? 1.16 : 1 / 1.16);
      return;
    }
    const orbit = { ArrowLeft: [-0.14, 0], ArrowRight: [0.14, 0], ArrowUp: [0, -0.1], ArrowDown: [0, 0.1] }[event.key];
    if (!orbit) return;
    event.preventDefault();
    const offset = camera.position.clone().sub(controls.target);
    const orbitPosition = new Spherical().setFromCartesianCoords(offset.x, offset.z, -offset.y);
    orbitPosition.theta += orbit[0];
    orbitPosition.phi += orbit[1];
    orbitPosition.makeSafe();
    const next = new Vector3().setFromSpherical(orbitPosition);
    camera.position.copy(controls.target).add(new Vector3(next.x, -next.z, next.y));
    controls.update();
    draw();
  });
  return {
    reset,
    zoom,
    select(id) {
      for (const mesh of meshes) {
        mesh.material.color.setHex(mesh.name === id ? 0xffcb79 : mesh.userData.baseColor);
        mesh.material.emissive.setHex(mesh.name === id ? 0x372006 : 0);
      }
      draw();
    },
    dispose() {
      observer.disconnect();
      controls.dispose();
      scene.traverse(object => {
        object.geometry?.dispose();
        object.material?.dispose();
      });
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}
