<!-- src/App.svelte-->
<script>
  import { onMount } from "svelte";
  import io from "socket.io-client";
  import Scene from "./Scene.svelte";

  let socket;
  let currentTrack = null;
  let status = "Connecting to AI...";
  let audioPlayer;
  let sceneComponent; // Reference to the 3D scene

  // Audio Processing State
  let isPlaying = false;

  onMount(() => {
    socket = io("http://localhost:5000");

    socket.on("connect", () => {
      status = "Connected. Waiting for generation...";
    });

    socket.on("status", (data) => {
      status = data.msg;
    });

    socket.on("play_track", (track) => {
      console.log("Received track:", track);
      playNewTrack(track);
    });
  });

  function playNewTrack(track) {
    status = `Playing: ${track.prompt} (${Math.round(track.bpm)} BPM)`;
    
    // 1. Trigger the Visual Spin/Transition
    if (sceneComponent) {
      sceneComponent.triggerTransition(track.bpm);
    }

    // 2. Audio Setup
    // Minimal crossfade logic could go here, but for now hard cut/play
    audioPlayer.src = track.url;
    audioPlayer.load();
    
    // Wait for spin to mostly finish or just start immediately? 
    // Let's start immediately for synch tightness.
    audioPlayer.play().catch(e => console.error("Autoplay blocked", e));
  }

  function handleAudioEnded() {
    console.log("Track ended, requesting next...");
    socket.emit("request_next");
  }
</script>

<main>
  <div class="overlay">
    <div class="status-box">
      <h1>AI DJ SYSTEM</h1>
      <p>{status}</p>
      {#if !isPlaying}
        <!-- Chrome blocks audio unless user interacts first -->
        <button on:click={() => { isPlaying=true; handleAudioEnded(); }}>START STREAM</button>
      {/if}
    </div>
  </div>

  <!-- Hidden Audio Player -->
  <audio 
    bind:this={audioPlayer} 
    on:ended={handleAudioEnded}
  ></audio>

  <!-- The 3D World -->
  <div class="viewport">
    <Scene bind:this={sceneComponent} />
  </div>
</main>

<style>
  :global(body) { margin: 0; background: #000; overflow: hidden; font-family: monospace; }
  
  .viewport {
    width: 100vw;
    height: 100vh;
    /* This is crucial for the PS2 Look - handled in Scene, but container needs to fit */
  }

  .overlay {
    position: absolute;
    top: 20px;
    left: 20px;
    z-index: 10;
    pointer-events: none; /* Let clicks pass through to 3d if needed */
  }

  .status-box {
    background: rgba(0, 0, 0, 0.7);
    color: #0f0;
    padding: 20px;
    border: 2px solid #0f0;
    pointer-events: auto;
    max-width: 400px;
  }

  button {
    background: #0f0;
    color: #000;
    border: none;
    padding: 10px 20px;
    font-weight: bold;
    cursor: pointer;
    font-family: monospace;
    font-size: 1.2rem;
  }
</style>