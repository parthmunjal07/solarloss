import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import type { ThreeEvent } from "@react-three/fiber";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  BoxGeometry,
  CanvasTexture,
  Color,
  InstancedMesh,
  Matrix4,
  MeshStandardMaterial,
  Object3D,
  SRGBColorSpace,
  Vector3,
} from "three";
import { modules, representativeModule } from "./model";
import type { SceneProps } from "./model";

function CameraControls({
  command,
  reducedMotion,
  onReady,
  onUnavailable,
}: SceneProps) {
  const { camera, gl, invalidate, size } = useThree();
  const controls = useRef<OrbitControls | null>(null);
  const home = useMemo(
    () =>
      new Vector3(4, 7, 10).multiplyScalar(
        Math.max(1, 2.2 / (size.width / size.height)),
      ),
    [size.width, size.height],
  );
  useEffect(() => {
    const orbit = new OrbitControls(camera, gl.domElement);
    controls.current = orbit;
    orbit.target.set(0, 0.8, 0);
    orbit.enablePan = false;
    orbit.minPolarAngle = 0.2;
    orbit.maxPolarAngle = Math.PI / 2.3;
    orbit.minAzimuthAngle = -Math.PI / 2.3;
    orbit.maxAzimuthAngle = Math.PI / 2.3;
    orbit.minDistance = 11;
    orbit.maxDistance = 44;
    orbit.zoomSpeed = 0.65;
    orbit.rotateSpeed = 0.6;
    const changed = () => invalidate();
    orbit.addEventListener("change", changed);
    const lost = (event: Event) => {
      event.preventDefault();
      onUnavailable();
    };
    gl.domElement.addEventListener("webglcontextlost", lost);
    onReady();
    return () => {
      orbit.removeEventListener("change", changed);
      orbit.dispose();
      controls.current = null;
      gl.domElement.removeEventListener("webglcontextlost", lost);
    };
  }, [camera, gl, invalidate, onReady, onUnavailable]);
  useEffect(() => {
    if (controls.current) {
      controls.current.enableDamping = !reducedMotion;
      controls.current.dampingFactor = 0.12;
    }
  }, [reducedMotion]);
  useEffect(() => {
    camera.position.copy(home);
    controls.current?.update();
    invalidate();
  }, [camera, home, invalidate]);
  useEffect(() => {
    const orbit = controls.current;
    if (!orbit) return;
    if (command.action === "reset") {
      camera.position.copy(home);
      orbit.target.set(0, 0.8, 0);
    } else if (command.action === "in" || command.action === "out") {
      const offset = camera.position.clone().sub(orbit.target);
      offset.setLength(
        Math.min(
          44,
          Math.max(
            11,
            offset.length() * (command.action === "in" ? 0.85 : 1.15),
          ),
        ),
      );
      camera.position.copy(orbit.target).add(offset);
    } else {
      const offset = camera.position.clone().sub(orbit.target);
      offset.applyAxisAngle(
        new Vector3(0, 1, 0),
        command.action === "left" ? -0.18 : 0.18,
      );
      camera.position.copy(orbit.target).add(offset);
    }
    orbit.update();
    invalidate();
  }, [camera, command, home, invalidate]);
  useFrame(() => {
    if (controls.current?.update()) invalidate();
  });
  return null;
}
function Panels({
  mode,
  selected,
  highlighted,
  onSelect,
  onHover,
}: SceneProps) {
  const { invalidate } = useThree();
  const frames = useRef<InstancedMesh>(null),
    faces = useRef<InstancedMesh>(null);
  const resources = useMemo(() => {
    // A small procedural cell pattern; no external image, model, sun or scientific data.
    const canvas = document.createElement("canvas");
    canvas.width = 128;
    canvas.height = 256;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = "#cbd8eb";
    ctx.fillRect(0, 0, 128, 256);
    ctx.strokeStyle = "#8296b4";
    ctx.lineWidth = 1.4;
    for (let x = 0; x <= 128; x += 128 / 6) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, 256);
      ctx.stroke();
    }
    for (let y = 0; y <= 256; y += 256 / 12) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(128, y);
      ctx.stroke();
    }
    const texture = new CanvasTexture(canvas);
    texture.colorSpace = SRGBColorSpace;
    const frameGeometry = new BoxGeometry(1.04, 0.07, 1.65),
      faceGeometry = new BoxGeometry(0.96, 0.012, 1.56);
    const frameMaterial = new MeshStandardMaterial({
      color: "white",
      metalness: 0.45,
      roughness: 0.5,
    });
    const faceMaterial = new MeshStandardMaterial({
      color: "white",
      map: texture,
      metalness: 0.18,
      roughness: 0.36,
    });
    return {
      texture,
      frameGeometry,
      faceGeometry,
      frameMaterial,
      faceMaterial,
    };
  }, []);
  useEffect(() => {
    const frameMesh = frames.current,
      faceMesh = faces.current;
    return () => {
      frameMesh?.dispose();
      faceMesh?.dispose();
      resources.texture.dispose();
      resources.frameGeometry.dispose();
      resources.faceGeometry.dispose();
      resources.frameMaterial.dispose();
      resources.faceMaterial.dispose();
    };
  }, [resources]);
  useLayoutEffect(() => {
    if (!frames.current || !faces.current) return;
    const array = new Object3D(),
      panel = new Object3D(),
      matrix = new Matrix4();
    const color = new Color();
    modules.forEach((m, i) => {
      array.position.set(m.inverter === 1 ? -3.85 : 3.85, 1.25, -0.5);
      array.rotation.set((26 * Math.PI) / 180, 0, 0);
      array.updateMatrix();
      panel.position.set(
        ((m.index % 6) - 2.5) * 1.11,
        0,
        (Math.floor(m.index / 6) - 0.5) * 1.9,
      );
      panel.updateMatrix();
      matrix.multiplyMatrices(array.matrix, panel.matrix);
      frames.current!.setMatrixAt(i, matrix);
      panel.position.y = 0.044;
      panel.updateMatrix();
      matrix.multiplyMatrices(array.matrix, panel.matrix);
      faces.current!.setMatrixAt(i, matrix);
      const focus = m.id === selected || m.id === highlighted;
      frames.current!.setColorAt(
        i,
        color.set(
          focus
            ? "#0f766e"
            : mode === "reference" && m.inverter === 2
              ? "#548baa"
              : "#80909f",
        ),
      );
      faces.current!.setColorAt(
        i,
        color.set(
          mode === "shading" && m.id === representativeModule
            ? "#eab04f"
            : focus
              ? "#5289b6"
              : m.inverter === 1
                ? "#244e84"
                : "#31668f",
        ),
      );
    });
    frames.current.instanceMatrix.needsUpdate = true;
    faces.current.instanceMatrix.needsUpdate = true;
    if (frames.current.instanceColor)
      frames.current.instanceColor.needsUpdate = true;
    if (faces.current.instanceColor)
      faces.current.instanceColor.needsUpdate = true;
    frames.current.computeBoundingSphere();
    faces.current.computeBoundingSphere();
    invalidate();
  }, [mode, selected, highlighted, invalidate]);
  const select = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    if (event.instanceId !== undefined) onSelect(modules[event.instanceId].id);
  };
  const hover = (event: ThreeEvent<PointerEvent>) => {
    event.stopPropagation();
    if (event.instanceId !== undefined) onHover(modules[event.instanceId].id);
  };
  return (
    <group>
      <instancedMesh
        dispose={null}
        ref={frames}
        args={[resources.frameGeometry, resources.frameMaterial, 24]}
        onClick={select}
        onPointerMove={hover}
        onPointerOut={() => onHover(null)}
      />
      <instancedMesh
        dispose={null}
        ref={faces}
        args={[resources.faceGeometry, resources.faceMaterial, 24]}
        onClick={select}
        onPointerMove={hover}
        onPointerOut={() => onHover(null)}
      />
      {mode === "shading" && (
        <group
          position={[-3.85, 1.25, -0.5]}
          rotation={[(26 * Math.PI) / 180, 0, 0]}
        >
          {[0, 1, 2].map((i) => (
            <mesh
              key={i}
              position={[-0.555, 0.057, -0.95 + (i - 1) * 0.4]}
              rotation={[0, -0.38, 0]}
            >
              <boxGeometry args={[0.85, 0.004, 0.032]} />
              <meshBasicMaterial color="#92400e" />
            </mesh>
          ))}
        </group>
      )}
    </group>
  );
}
function Structure({ mode }: { mode: SceneProps["mode"] }) {
  return (
    <>
      <mesh position={[0, -0.08, 0]}>
        <boxGeometry args={[16.6, 0.14, 7.4]} />
        <meshStandardMaterial color="#e9e2d7" roughness={0.92} />
      </mesh>
      {[1, 2].map((inverter) => (
        <group key={inverter} position={[inverter === 1 ? -3.85 : 3.85, 0, 0]}>
          <mesh position={[0, 0.045, -0.5]}>
            <boxGeometry args={[7.1, 0.12, 4.9]} />
            <meshStandardMaterial
              color={
                mode === "reference" && inverter === 2 ? "#d7e4ee" : "#ded6c8"
              }
            />
          </mesh>
          {[-2.8, 2.8].flatMap((x) =>
            [-1.8, 0.8].map((z) => (
              <mesh key={`${x}-${z}`} position={[x, z < 0 ? 0.95 : 0.42, z]}>
                <boxGeometry args={[0.09, z < 0 ? 1.8 : 0.8, 0.09]} />
                <meshStandardMaterial
                  color="#82909a"
                  metalness={0.5}
                  roughness={0.4}
                />
              </mesh>
            )),
          )}
          <group
            position={[0, 1.15, -0.5]}
            rotation={[(26 * Math.PI) / 180, 0, 0]}
          >
            {[-1.55, -0.35, 0.35, 1.55].map((z) => (
              <mesh key={z} position={[0, -0.08, z]}>
                <boxGeometry args={[6.85, 0.09, 0.09]} />
                <meshStandardMaterial color="#738291" metalness={0.45} />
              </mesh>
            ))}
          </group>
          <mesh position={[0, 0.32, 2.7]}>
            <boxGeometry args={[0.84, 0.64, 0.38]} />
            <meshStandardMaterial
              color="#d6d8d6"
              metalness={0.2}
              roughness={0.5}
            />
          </mesh>
          <mesh position={[0, 0.38, 2.895]}>
            <boxGeometry args={[0.5, 0.3, 0.008]} />
            <meshStandardMaterial color="#14213d" />
          </mesh>
          <mesh position={[0.17, 0.4, 2.91]}>
            <boxGeometry args={[0.045, 0.05, 0.014]} />
            <meshBasicMaterial color={inverter === 1 ? "#b45309" : "#3b5b8c"} />
          </mesh>
          <mesh position={[0, 0.18, 1.88]}>
            <boxGeometry args={[0.035, 0.035, 1.28]} />
            <meshStandardMaterial color="#626f7c" />
          </mesh>
        </group>
      ))}
    </>
  );
}
export default function SolarArrayScene(props: SceneProps) {
  return (
    <Canvas
      frameloop="demand"
      dpr={[1, 1.5]}
      camera={{ position: [4, 7, 10], fov: 34, near: 0.1, far: 90 }}
      gl={{ antialias: true, alpha: true, powerPreference: "low-power" }}
      fallback={
        <span>
          3D unsupported. Use the accessible module controls and 2D schematic.
        </span>
      }
      aria-hidden="true"
      style={{ touchAction: "none" }}
    >
      <ambientLight intensity={1.15} />
      <hemisphereLight args={["#f5f8ff", "#a59a88", 1.5]} />
      <directionalLight position={[-6, 12, 8]} intensity={2.1} />
      <Structure mode={props.mode} />
      <Panels {...props} />
      <CameraControls {...props} />
    </Canvas>
  );
}
