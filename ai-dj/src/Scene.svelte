<!-- src/Scene.svelte-->
<script>
  import { onDestroy } from "svelte";
  import * as THREE from "three";
  import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader";

  // Variables
  let canvasContainer;
  let renderer, scene, camera, mixer, clock;
  
  // Animation State
  let mixers = []; 
  let actions = {}; 
  let activeAction;
  let model; 
  let danceInterval; 

  // Underwater Elements
  let bubbleSystem;
  let causticTexture;
  let discoLights = [];
  let swimmers = []; 

  const REEF_CONFIG = {
      scale: 5.0,       // Scale it up so the booth fits inside
      x: -2.5,              // Left/Right
      y: -1.0,           // Up/Down (Lower it so the booth sits on the sea floor)
      z: -2.0,           // Forward/Back (Push back so camera is inside too)
      rotationY: 1.5       // Rotate to align opening with camera (in radians)
  };

  // SCENE CONFIG
  const RENDER_WIDTH = 860;
  const RENDER_HEIGHT = 720;
  const BASE_ANIMATION_BPM = 120; 

  // POSITIONS
  const TABLE_HEIGHT = 0.85; 
  const TABLE_Z = 1.2;       
  const TABLE_Y = TABLE_HEIGHT / 2;

  // --- EXPORTED FUNCTIONS ---
  export function triggerTransition(newBpm) {
    if (!mixer || !actions["Spin"]) return;
    const playbackRate = newBpm / BASE_ANIMATION_BPM;
    mixer.timeScale = playbackRate; 

    if (danceInterval) clearInterval(danceInterval);
    fadeToAction("Spin", 0.2);
    const spinDuration = 2000 / playbackRate; 

    setTimeout(() => {
        startDanceRoulette(newBpm);
    }, spinDuration);
  }

  // --- INTERNAL LOGIC ---

  function createScene(node) {
      canvasContainer = node;
      initThree();
      loadAssets();
      animate();

      return {
          destroy() {
              if (renderer) renderer.dispose();
              if (danceInterval) clearInterval(danceInterval);
              if (scene) {
                  scene.traverse((object) => {
                      if (object.geometry) object.geometry.dispose();
                      if (object.material) {
                          if (Array.isArray(object.material)) {
                              object.material.forEach(m => m.dispose());
                          } else {
                              object.material.dispose();
                          }
                      }
                  });
              }
          }
      };
  }

  function startDanceRoulette(bpm) {
    const secondsPerBeat = 60 / bpm;
    const switchTimeMs = (secondsPerBeat * 8) * 1000;
    pickRandomDance();
    danceInterval = setInterval(() => {
        pickRandomDance();
    }, switchTimeMs);
  }

  function pickRandomDance() {
      const moves = ["Dance1", "Dance2", "Dance3", "Dance4"];
      const availableMoves = moves.filter(m => actions[m] !== activeAction);
      const randomMove = availableMoves[Math.floor(Math.random() * availableMoves.length)];
      fadeToAction(randomMove, 0.5); 
  }

  function fadeToAction(name, duration) {
    const previousAction = activeAction;
    activeAction = actions[name];

    if (previousAction !== activeAction) {
      if(previousAction) previousAction.fadeOut(duration);
      if(activeAction) {
          activeAction.reset()
            .setEffectiveTimeScale(1)
            .setEffectiveWeight(1)
            .fadeIn(duration)
            .play();
      }
    }
  }

  function createCausticTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = 'black';
    ctx.fillRect(0,0,512,512);
    
    // Draw noise
    for(let i=0; i<300; i++) {
        const x = Math.random() * 512;
        const y = Math.random() * 512;
        const r = Math.random() * 30 + 10;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI*2);
        ctx.fillStyle = `rgba(0, 255, 255, ${Math.random() * 0.3})`;
        ctx.fill();
    }
    
    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    return texture;
  }

  function initThree() {
    if (!canvasContainer) return; 

    scene = new THREE.Scene();
    
    // Underwater Atmosphere
    const waterColor = 0x004455; 
    scene.background = new THREE.Color(waterColor); 
    scene.fog = new THREE.Fog(waterColor, 1, 15);

    camera = new THREE.PerspectiveCamera(45, RENDER_WIDTH / RENDER_HEIGHT, 0.1, 100);
    camera.position.set(2.5, 2.5, 5); 
    camera.lookAt(0, 0.8, 0);

    const ambientLight = new THREE.AmbientLight(0x404040, 0.5); 
    scene.add(ambientLight);

    // Caustics
    causticTexture = createCausticTexture();
    const causticLight = new THREE.SpotLight(0x00ffff, 4);
    causticLight.position.set(0, 10, 0);
    causticLight.angle = Math.PI / 4;
    causticLight.penumbra = 0.5;
    causticLight.map = causticTexture; 
    causticLight.castShadow = true;
    scene.add(causticLight);
    scene.add(causticLight.target);

    // Disco Lights
    const positions = [[-3, 3, -2], [3, 3, -2], [0, 4, 2]];
    positions.forEach(pos => {
        const light = new THREE.PointLight(0xff00ff, 0, 10);
        light.position.set(pos[0], pos[1], pos[2]);
        scene.add(light);
        discoLights.push(light);
    });

    // DJ Table
    const geometry = new THREE.BoxGeometry(2, TABLE_HEIGHT, 1);
    const material = new THREE.MeshPhongMaterial({ 
        color: 0x222222,
        shininess: 100, 
        specular: 0x111111
    });
    const table = new THREE.Mesh(geometry, material);
    table.position.set(0, TABLE_Y, TABLE_Z); 
    scene.add(table);

    // Bubbles
    const bubblesGeo = new THREE.BufferGeometry();
    const bubbleCount = 200;
    const posArray = new Float32Array(bubbleCount * 3);
    for(let i=0; i<bubbleCount * 3; i++) {
        posArray[i] = (Math.random() - 0.5) * 10; 
    }
    bubblesGeo.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    const bubblesMat = new THREE.PointsMaterial({
        color: 0xffffff,
        size: 0.05,
        transparent: true,
        opacity: 0.6
    });
    bubbleSystem = new THREE.Points(bubblesGeo, bubblesMat);
    scene.add(bubbleSystem);

    renderer = new THREE.WebGLRenderer({ antialias: false });
    renderer.setSize(RENDER_WIDTH, RENDER_HEIGHT, false); 
    renderer.domElement.style.width = "100%"; 
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.imageRendering = "pixelated"; 
    
    canvasContainer.appendChild(renderer.domElement);
    clock = new THREE.Clock();
  }

  function loadAssets() {
    const loader = new GLTFLoader();

    // 1. Load Coral Reef (Environment)
    loader.load("/coral_reef.glb", (gltf) => {
        const reef = gltf.scene;

        // Apply Manual Config
        reef.scale.set(REEF_CONFIG.scale, REEF_CONFIG.scale, REEF_CONFIG.scale);
        reef.position.set(REEF_CONFIG.x, REEF_CONFIG.y, REEF_CONFIG.z);
        reef.rotation.y = REEF_CONFIG.rotationY;

        // Optional: Ensure it renders behind the transparent water bubbles/fog correctly
        reef.traverse((child) => {
            if (child.isMesh) {
                // Helps with underwater lighting interaction
                child.castShadow = true;
                child.receiveShadow = true;
            }
        });

        scene.add(reef);
    }, undefined, (err) => console.error("Error loading reef:", err));

    // 2. Load Frog (Existing)
    loader.load("/frog.glb", (gltf) => {
      model = gltf.scene;
      mixer = new THREE.AnimationMixer(model);
      mixers.push(mixer); 
      gltf.animations.forEach((clip) => {
        actions[clip.name] = mixer.clipAction(clip);
      });
      activeAction = actions["Dance1"];
      if(activeAction) activeAction.play();
      scene.add(model);
      model.position.set(0, 0, 0); 
    });

    // 3. Load Turntable (Existing)
    loader.load("/turntable.glb", (gltf) => {
        const tScene = gltf.scene;
        // ... (keep your existing turntable transform logic here) ...
        tScene.rotation.y = -Math.PI / 2 - 0.05;
        tScene.rotation.x = 0.23;
        tScene.rotation.z = 0.15;
        tScene.updateMatrixWorld(true);

        const box = new THREE.Box3().setFromObject(tScene);
        const size = new THREE.Vector3();
        box.getSize(size);
        const targetWidth = 1.9; 
        const maxDimension = Math.max(size.x, size.z);
        const scaleFactor = targetWidth / maxDimension;
        tScene.scale.set(scaleFactor, scaleFactor, scaleFactor);

        const newBox = new THREE.Box3().setFromObject(tScene);
        const center = new THREE.Vector3();
        newBox.getCenter(center);
        const offsetX = 0 - center.x;
        const offsetZ = TABLE_Z - center.z -0.06;
        const offsetY = TABLE_HEIGHT - newBox.min.y -0.25;

        tScene.position.x += offsetX;
        tScene.position.y += offsetY;
        tScene.position.z += offsetZ;
        scene.add(tScene);
    });

    // 4. Load Swimmers (Existing)
    loadSwimmer("/dolphin.glb", "dolphin", loader, 1.5); 
    loadSwimmer("/orca.glb", "orca", loader, 2.8); 
  }

  function loadSwimmer(path, name, loader, targetSizeInMeters) {
      loader.load(path, (gltf) => {
        const mesh = gltf.scene;
        const swMixer = new THREE.AnimationMixer(mesh);
        mixers.push(swMixer);

        if(gltf.animations.length > 0) {
            const action = swMixer.clipAction(gltf.animations[0]);
            action.timeScale = 0.8; // Slow down the animation itself slightly
            action.play();
        }

        // --- NORMALIZATION (AUTO-SCALE) ---
        mesh.scale.set(1, 1, 1);
        mesh.updateMatrixWorld(true);
        
        const box = new THREE.Box3().setFromObject(mesh);
        const size = new THREE.Vector3();
        box.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z);
        const scaleFactor = targetSizeInMeters / maxDim;
        
        mesh.scale.set(scaleFactor, scaleFactor, scaleFactor);

        // Add a Wrapper to handle rotation cleanly without messing up model axes
        const wrapper = new THREE.Group();
        wrapper.add(mesh);
        
        // Correct Model Orientation inside wrapper (assuming they face +Z)
        // No extra rotation needed if lookAt works on the wrapper.
        // If your models swim backwards, uncomment the line below:
        // mesh.rotation.y = Math.PI; 
        
        wrapper.visible = false; 
        scene.add(wrapper);

        swimmers.push({
            group: wrapper, // We move the group, not the mesh directly
            mesh: mesh,
            mixer: swMixer,
            speed: 0.1, // Progression speed (0 to 1)
            active: false,
            progress: 0,
            curvePath: null, // Will hold start, mid, end vectors
            nextSpawnTime: clock.getElapsedTime() + Math.random() * 5
        });

      }, undefined, (err) => console.error(`Error loading ${name}`, err));
  }

  // --- BEZIER MATH ---
  // Returns point at t (0 to 1) on quadratic bezier
  function getBezierPoint(t, p0, p1, p2, target) {
      const oneMinusT = 1 - t;
      target.x = oneMinusT * oneMinusT * p0.x + 2 * oneMinusT * t * p1.x + t * t * p2.x;
      target.y = oneMinusT * oneMinusT * p0.y + 2 * oneMinusT * t * p1.y + t * t * p2.y;
      target.z = oneMinusT * oneMinusT * p0.z + 2 * oneMinusT * t * p1.z + t * t * p2.z;
  }

  function updateSwimmers(delta, elapsed) {
      const dummyVec = new THREE.Vector3(); // For calculating lookAt target

      swimmers.forEach(s => {
          if (!s.active) {
              if (elapsed > s.nextSpawnTime) {
                  // --- SPAWN LOGIC ---
                  s.active = true;
                  s.group.visible = true;
                  s.progress = 0;
                  
                  // 1. Determine Direction (Left->Right or Right->Left)
                  const ltr = Math.random() > 0.5;

                  // 2. Define visible corridor behind DJ
                  // X: -12 to 12 covers screen width well at Z=-5
                  const startX = ltr ? -12 : 12;
                  const endX   = ltr ? 12 : -12;

                  // 3. Define Z-Depth (BEHIND THE FROG)
                  // Frog is at 0. Table at 1.2. Camera at 5.
                  // We want them swimming between -6 (deep) and 0 (just behind frog)
                  const startZ = -2 - Math.random() * 4; 
                  const endZ   = -2 - Math.random() * 4;
                  // Mid-point Control Z (Curves away or towards)
                  const midZ   = -4 - Math.random() * 3; 

                  // 4. Define Height (Y)
                  // Floor is at 0. Ceiling visible area ~ 5.
                  const startY = -1 + Math.random() * 5;
                  const endY   = -1 + Math.random() * 5;
                  // Arc height (swim up/down in middle)
                  const midY   = 1 + Math.random() * 4;

                  // 5. Store Curve Points
                  s.curvePath = {
                      p0: new THREE.Vector3(startX, startY, startZ), // Start
                      p1: new THREE.Vector3(0, midY, midZ),          // Control Point (Center)
                      p2: new THREE.Vector3(endX, endY, endZ)        // End
                  };

                  // 6. Set Speed (Much slower now)
                  // speed represents "Progress per second". 
                  // 0.1 means it takes 10 seconds to cross.
                  s.speed = 0.08 + Math.random() * 0.06; 
              }
          } else {
              // --- MOVEMENT LOGIC (Bezier Arc) ---
              s.progress += s.speed * delta;

              if (s.progress >= 1) {
                  // Finished
                  s.active = false;
                  s.group.visible = false;
                  s.nextSpawnTime = elapsed + 2 + Math.random() * 6; // Rest period
              } else {
                  // Get current position
                  const currentPos = s.group.position;
                  getBezierPoint(s.progress, s.curvePath.p0, s.curvePath.p1, s.curvePath.p2, currentPos);
                  
                  // Look Ahead logic for smooth rotation
                  // Look 5% ahead in the curve
                  const lookAheadT = Math.min(s.progress + 0.05, 1.0);
                  getBezierPoint(lookAheadT, s.curvePath.p0, s.curvePath.p1, s.curvePath.p2, dummyVec);
                  
                  s.group.lookAt(dummyVec);
              }
          }
      });
  }

  function updateVisuals(delta, elapsed) {
      if(causticTexture) {
          causticTexture.offset.x += 0.05 * delta;
          causticTexture.offset.y += 0.05 * delta;
      }

      if(bubbleSystem) {
          const positions = bubbleSystem.geometry.attributes.position.array;
          for(let i=1; i < positions.length; i+=3) { 
             positions[i] += delta * 1.5; 
             if (positions[i] > 5) {
                 positions[i] = -2; 
             }
          }
          bubbleSystem.geometry.attributes.position.needsUpdate = true;
      }

      const beatSpeed = 10; 
      discoLights.forEach((light, index) => {
          const intensity = (Math.sin(elapsed * beatSpeed + index) + 1) * 2; 
          light.intensity = intensity;
          if (Math.random() < 0.02) {
              light.color.setHSL(Math.random(), 1, 0.5);
          }
      });
  }

  function animate() {
    requestAnimationFrame(animate);
    const delta = clock.getDelta();
    const elapsed = clock.getElapsedTime();

    mixers.forEach(m => m.update(delta));
    updateSwimmers(delta, elapsed);
    updateVisuals(delta, elapsed);

    renderer.render(scene, camera);
  }
</script>

<div class="scene-container" use:createScene></div>

<style>
  .scene-container {
    width: 100%;
    height: 100%;
    image-rendering: pixelated;
  }
</style>