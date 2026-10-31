import { Canvas, useFrame, useLoader, useThree } from "@react-three/fiber";
import { EffectComposer, Bloom, Vignette, Noise } from "@react-three/postprocessing";
import { Suspense, useMemo, useRef } from "react";
import * as THREE from "three";
import { scrollState } from "../lib/scroll";

const T = (n: string) => `${import.meta.env.BASE_URL}textures/${n}`;
const SUN = new THREE.Vector3(-4, 1.4, 2.5).normalize();
const smooth = (a: number, b: number, x: number) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

// ---------------------------------------------------------------- Earth (day/night shader)
const earthVert = /* glsl */ `
varying vec2 vUv; varying vec3 vNormalW; varying vec3 vPosW;
void main(){ vUv = uv; vNormalW = normalize(mat3(modelMatrix) * normal);
  vec4 w = modelMatrix * vec4(position,1.0); vPosW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`;
const earthFrag = /* glsl */ `
uniform sampler2D dayMap; uniform sampler2D nightMap; uniform sampler2D specMap; uniform vec3 sunDir; uniform float mourning;
varying vec2 vUv; varying vec3 vNormalW; varying vec3 vPosW;
void main(){
  vec3 n = normalize(vNormalW); float d = dot(n, sunDir);
  float dayMix = smoothstep(-0.18, 0.28, d);
  vec3 day = texture2D(dayMap, vUv).rgb; vec3 night = texture2D(nightMap, vUv).rgb;
  night *= vec3(1.0, 0.72, 0.38) * 2.2;                        // city lights rendered as candlelight
  vec3 viewDir = normalize(cameraPosition - vPosW);
  float spec = pow(max(dot(reflect(-sunDir, n), viewDir), 0.0), 28.0) * texture2D(specMap, vUv).r * 0.55;
  vec3 col = mix(night, day * (0.25 + 0.95 * max(d, 0.0)), dayMix) + spec * vec3(1.0, 0.86, 0.6) * dayMix;
  float rim = pow(1.0 - max(dot(n, viewDir), 0.0), 2.6);
  col += rim * mix(vec3(0.32,0.62,0.7), vec3(0.95,0.58,0.2), mourning) * (0.25 + 0.75 * dayMix);
  col = mix(col, col * vec3(1.05, 0.9, 0.78), mourning * 0.6);  // the world warms as the satellite falls
  gl_FragColor = vec4(col, 1.0);
}`;
const atmoFrag = /* glsl */ `
varying vec3 vNormalW; varying vec3 vPosW; uniform vec3 sunDir; uniform float mourning;
void main(){ vec3 n = normalize(vNormalW); vec3 v = normalize(cameraPosition - vPosW);
  float i = pow(max(0.0, 0.66 - dot(n, v)), 2.4) * 0.9; float lit = smoothstep(-0.4, 0.6, dot(n, sunDir));
  vec3 c = mix(vec3(0.35,0.7,0.85), vec3(1.0,0.62,0.22), mourning);
  gl_FragColor = vec4(c, 1.0) * i * (0.35 + 0.9 * lit); }`;

function Earth() {
  const [day, night, clouds, spec] = useLoader(THREE.TextureLoader, [T("earth_day.jpg"), T("earth_lights.jpg"), T("earth_clouds.jpg"), T("earth_spec.jpg")]);
  [day, night].forEach((t) => (t.colorSpace = THREE.SRGBColorSpace));
  const group = useRef<THREE.Group>(null!); const cloudRef = useRef<THREE.Mesh>(null!);
  const uniforms = useMemo(() => ({ dayMap: { value: day }, nightMap: { value: night }, specMap: { value: spec }, sunDir: { value: SUN }, mourning: { value: 0 } }), [day, night, spec]);
  const atmoUniforms = useMemo(() => ({ sunDir: { value: SUN }, mourning: { value: 0 } }), []);
  useFrame((_, dt) => {
    group.current.rotation.y += dt * 0.035;
    cloudRef.current.rotation.y += dt * 0.012;
    const m = smooth(0.55, 0.95, scrollState.progress);
    uniforms.mourning.value = m; atmoUniforms.mourning.value = m;
  });
  return (
    <group rotation={[0.38, 0, 0.12]}>
      <group ref={group}>
        <mesh><sphereGeometry args={[2, 128, 128]} /><shaderMaterial vertexShader={earthVert} fragmentShader={earthFrag} uniforms={uniforms} /></mesh>
        <mesh ref={cloudRef} scale={1.012}><sphereGeometry args={[2, 96, 96]} />
          <meshStandardMaterial alphaMap={clouds} transparent opacity={0.55} depthWrite={false} color="#f2ece2" /></mesh>
      </group>
      <mesh scale={1.075}><sphereGeometry args={[2, 64, 64]} />
        <shaderMaterial vertexShader={earthVert} fragmentShader={atmoFrag} uniforms={atmoUniforms} blending={THREE.AdditiveBlending} side={THREE.BackSide} transparent depthWrite={false} /></mesh>
    </group>
  );
}

// ---------------------------------------------------------------- Stars
function Stars() {
  const tex = useLoader(THREE.TextureLoader, T("stars.jpg")); tex.colorSpace = THREE.SRGBColorSpace;
  const pts = useMemo(() => {
    const n = 2600, p = new Float32Array(n * 3), c = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const r = 40 + Math.random() * 40, th = Math.random() * Math.PI * 2, ph = Math.acos(2 * Math.random() - 1);
      p.set([r * Math.sin(ph) * Math.cos(th), r * Math.cos(ph), r * Math.sin(ph) * Math.sin(th)], i * 3);
      const warm = Math.random() < 0.18; c.set(warm ? [1, 0.78, 0.45] : [0.85, 0.88, 0.95], i * 3);
    }
    return { p, c };
  }, []);
  const ref = useRef<THREE.Points>(null!);
  useFrame((_, dt) => { ref.current.rotation.y += dt * 0.004; });
  return (
    <>
      <mesh scale={-1}><sphereGeometry args={[95, 48, 48]} /><meshBasicMaterial map={tex} color="#5a5560" side={THREE.BackSide} /></mesh>
      <points ref={ref}>
        <bufferGeometry><bufferAttribute attach="attributes-position" args={[pts.p, 3]} /><bufferAttribute attach="attributes-color" args={[pts.c, 3]} /></bufferGeometry>
        <pointsMaterial size={0.09} vertexColors transparent opacity={0.9} sizeAttenuation depthWrite={false} />
      </points>
    </>
  );
}

// ---------------------------------------------------------------- CubeSat + decaying orbit + re-entry
function CubeSat() {
  const panel = (x: number) => (
    <mesh position={[x, 0, 0]}><boxGeometry args={[0.16, 0.005, 0.07]} />
      <meshStandardMaterial color="#1c2a4a" metalness={0.6} roughness={0.35} emissive="#0d1d3a" /></mesh>);
  return (
    <group scale={0.55}>
      <mesh><boxGeometry args={[0.05, 0.05, 0.11]} /><meshStandardMaterial color="#c9c2b4" metalness={0.85} roughness={0.3} /></mesh>
      {panel(0.11)}{panel(-0.11)}
      <pointLight color="#ffd28a" intensity={0.6} distance={0.6} />
    </group>
  );
}

const TRAIL = 220;
function Orbit() {
  const sat = useRef<THREE.Group>(null!); const streak = useRef<THREE.Mesh>(null!);
  const trailGeo = useMemo(() => { const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(TRAIL * 3), 3)); return g; }, []);
  const trailMat = useMemo(() => new THREE.LineBasicMaterial({ color: "#e8a33d", transparent: true, opacity: 0.55 }), []);
  const hist = useRef<THREE.Vector3[]>([]);
  const ang = useRef(0);
  const trailLine = useMemo(() => new THREE.Line(trailGeo, trailMat), [trailGeo, trailMat]);
  useFrame((_, dt) => {
    const p = scrollState.progress;
    const decay = smooth(0.12, 0.92, p);                     // the orbit decays as the story is scrolled
    const radius = THREE.MathUtils.lerp(3.15, 2.08, decay);
    ang.current += dt * (0.32 + decay * 1.1);
    const tilt = 0.52;
    const pos = new THREE.Vector3(Math.cos(ang.current) * radius, Math.sin(ang.current) * radius * Math.sin(tilt) * 0.5, Math.sin(ang.current) * radius * Math.cos(tilt));
    sat.current.position.copy(pos);
    sat.current.rotation.set(ang.current * 0.7, ang.current, 0.3);
    const burn = smooth(0.84, 0.97, p);
    sat.current.visible = p < 0.985;
    hist.current.unshift(pos.clone()); if (hist.current.length > TRAIL) hist.current.pop();
    const arr = trailGeo.attributes.position.array as Float32Array;
    for (let i = 0; i < TRAIL; i++) { const v = hist.current[Math.min(i, hist.current.length - 1)]; arr[i * 3] = v.x; arr[i * 3 + 1] = v.y; arr[i * 3 + 2] = v.z; }
    trailGeo.attributes.position.needsUpdate = true;
    trailMat.color.set(burn > 0 ? "#ff7a2e" : "#e8a33d"); trailMat.opacity = 0.35 + burn * 0.6;
    streak.current.position.copy(pos); streak.current.scale.setScalar(0.001 + burn * 0.12);
    (streak.current.material as THREE.MeshBasicMaterial).opacity = burn;
  });
  return (
    <group rotation={[0.38, 0, 0.12]}>
      <primitive object={trailLine} />
      <group ref={sat}><CubeSat /></group>
      <mesh ref={streak}><sphereGeometry args={[1, 24, 24]} /><meshBasicMaterial color="#ff8a3a" transparent toneMapped={false} /></mesh>
    </group>
  );
}

// ---------------------------------------------------------------- Camera choreography
function Rig() {
  const { camera, size } = useThree();
  const target = useMemo(() => new THREE.Vector3(), []);
  const look = useMemo(() => new THREE.Vector3(), []);
  useFrame((state) => {
    const p = scrollState.progress;
    const mobile = size.width < 768;
    const narrow = mobile ? 1.5 : 1;
    // hero: Earth sits right of the title; story: it recedes; finale: we fall towards it
    const z = THREE.MathUtils.lerp(9.4, 15, smooth(0.03, 0.3, p)) - smooth(0.78, 0.98, p) * 8;
    const x = mobile ? 0 : THREE.MathUtils.lerp(-3.1, 6.2, smooth(0.03, 0.3, p)) - smooth(0.78, 0.98, p) * 6.2;
    const y = Math.sin(state.clock.elapsedTime * 0.12) * 0.15 + smooth(0.3, 0.8, p) * 0.8;
    target.set(x, y, z * narrow);
    camera.position.lerp(target, 0.06);
    look.set(camera.position.x * 0.92, camera.position.y * 0.5, 0);   // parallel shift: the planet slides aside
    camera.lookAt(look);
  });
  return null;
}

export default function Scene() {
  return (
    <Canvas dpr={[1, 1.75]} camera={{ fov: 38, position: [0, 0, 7.2], near: 0.1, far: 300 }} gl={{ antialias: true, powerPreference: "high-performance" }}
      style={{ position: "fixed", inset: 0, zIndex: 0 }}>
      <color attach="background" args={["#050507"]} />
      <ambientLight intensity={0.15} />
      <directionalLight position={SUN.clone().multiplyScalar(10)} intensity={2.2} color="#fff1dc" />
      <Suspense fallback={null}>
        <Stars /><Earth /><Orbit />
      </Suspense>
      <Rig />
      <EffectComposer>
        <Bloom intensity={0.9} luminanceThreshold={0.62} luminanceSmoothing={0.25} mipmapBlur />
        <Noise opacity={0.025} />
        <Vignette eskil={false} offset={0.22} darkness={0.85} />
      </EffectComposer>
    </Canvas>
  );
}
