# DJ RAWG 🐸🎧

**The world's first amphibious, autonomous AI DJ.**

## What is this?

This is a fun project that combines 3D visuals with generative AI audio. The concept is simple but technically kind of heavy. A frog named DJ Rawg stands at a turntable in a 3D underwater scene. When people in the connected stream's chat type a prompt (like "play some 80s synthwave" or "sad jazz for a rainy day"), the system actually generates that track from scratch and seamlessy mixes it into the set.

There are no playlists and no pre-recorded MP3s. Every single sound you hear is hallucinated by the AI in real-time.

## How it works

The system is split into two main parts that talk to each other over WebSockets.

**1. The Brain (Backend)**
*   Written in **Python** using **Flask**.
*   It listens to stream chat via a bot.
*   When a request comes in, it feeds the text into **Meta's AudioCraft** (specifically the MelodyFlow model).
*   It generates a 30-second loop and analyzes the BPM using Librosa.
*   It sends the audio URL and the BPM to the frontend.

**2. The Body (Frontend)**
*   Written in **Svelte** and **Three.js**.
*   It renders the 3D scene (the reef, the frog, the fish).
*   When it receives a new track, it handles the audio playback.
*   It syncs the frog's dancing animation speed to match the BPM of the generated track.

## Tech Stack

*   **Language:** Python 3.9+ & JavaScript
*   **AI Model:** AudioCraft (MelodyFlow)
*   **Backend:** Flask, Socket.IO, Pydub, Librosa
*   **Frontend:** Svelte, Three.js, GLTFLoader

## Getting Started

If you want to run this locally, you are going to need a decent GPU. Audio generation is heavy.

### Backend Setup
1.  Navigate to the root folder.
2.  Install the dependencies (requirements.txt coming soon, but you mostly need the dependencies of audiocraft, flask, and flask-socketio).
3.  Run the server:
    ```bash
    python dj_server.py
    ```
4.  The first run will take a while because it has to download the AI models from HuggingFace.

### Frontend Setup
1.  Navigate to the 'ai-dj' folder.
2.  Install dependencies:
    ```bash
    pnpm install
    ```
3.  Start the dev server:
    ```bash
    pnpm run dev
    ```

## Future Plans

I'm working on adding an overlay system so the stream chat messages appear as bubbles inside the 3D scene. I also want to add more dance moves for Rawg depending on the genre (headbanging for metal, swaying for ambient).

## License

MIT License. Feel free to fork this and make your own animal DJ.