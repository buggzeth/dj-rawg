import os
import time
import threading
import queue
import random
import torch
import librosa
import numpy as np
from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit
from audiocraft.models import MelodyFlow
from audiocraft.data.audio import audio_write

# NEW: Import Pydub
from pydub import AudioSegment

# --- CONFIGURATION ---
MODEL_VERSION = "facebook/melodyflow-t24-30secs"
OUTPUT_FOLDER = "generated_tracks"
Target_Duration = 30.0 
Buffer_Size = 2 
FADE_DURATION = 2000 # 2 seconds
TARGET_DBFS = -14.0  # Normalization target

PROMPTS = [
    "This is an 80s-style synthwave track. The tempo is driving and energetic, featuring a classic gated reverb snare drum pattern. A warm, analog synthesizer plays a nostalgic melody over a rolling bassline. The atmosphere is neon-soaked and futuristic, perfect for a night drive scene or a retro video game level.",
    
    "This song is a lo-fi hip hop beat. The tempo is slow and relaxed, featuring a dusty drum break with a heavy swing. A jazz piano sample plays a melancholic chord progression, accompanied by the sound of vinyl crackle and rain in the background. The vibe is chill, nostalgic, and study-focused.",
    
    "This track is a liquid drum and bass instrumental. The tempo is fast, around 170 BPM, featuring a complex, high-energy breakbeat rhythm. A deep, sub-bass wobble underpins ethereal synthesizer pads that float in the background. The mood is soulful yet energetic, suitable for a racing game or a high-speed travel montage.",
    
    "This is a deep house track. The rhythm is a steady four-on-the-floor beat with a grooving hi-hat pattern. A smooth electric piano plays deep, jazzy chords while a soulful vocal chop loops in the distance. The atmosphere is sophisticated and hypnotic, perfect for a late-night lounge or a fashion runway.",
    
    "This instrumental is an industrial techno piece. The tempo is moderate but heavy, featuring distorted kick drums and metallic percussion clangs. A gritty, aggressive bass synthesizer pulses rhythmically, creating a dark and dystopian atmosphere. It sounds like the soundtrack to a cyberpunk action movie or a futuristic underground club.",
    
    "This song is an upbeat funk instrumental. It features a prominent slap bass guitar playing a syncopated groove locked in with tight acoustic drums. A brass section punches in with bright stabs, and a wah-wah guitar adds texture. The vibe is energetic, happy, and danceable, reminiscent of 70s cop shows or a block party.",
    
    "This is an atmospheric ambient track. There are no drums, only layers of washing synthesizer pads and shimmering textures. The sound is wide and expansive, creating a sense of floating in deep space. The mood is serene, mysterious, and meditative, suitable for a sci-fi documentary or a yoga session.",
    
    "This track is a melodic dubstep instrumental. It builds up from a soft piano intro into a heavy, half-time drum beat. The drop features a growling, modulated bass synthesizer and powerful saw waves. The music is emotional yet intense, combining beautiful melodies with aggressive sound design.",
    
    "This is a modern trap beat. The tempo is slow but bouncy, dominated by booming 808 sub-bass glides and sharp, rapid-fire hi-hat rolls. A dark, minor-key bell melody loops hypnotically. The atmosphere is ominous and hard-hitting, typical of modern hip-hop production.",
    
    "This is a jazz fusion performance. The drums are playing a complex, fast-paced rhythm with plenty of cymbal work. A saxophone takes the lead with an intricate, improvised solo over a walking upright bass line. The vibe is sophisticated, chaotic, and energetic, sounding like a live performance in a smoky club."
]

# --- SETUP ---
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

song_queue = queue.Queue(maxsize=Buffer_Size)
current_model = None

# --- AUDIO PROCESSING UTILS ---
def get_key_modifier():
    """Generates a random phrase specifying two musical keys."""
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    scales = ["Major", "Minor"]
    
    # Generate Key 1
    k1 = f"{random.choice(notes)} {random.choice(scales)}"
    
    # Generate Key 2
    k2 = f"{random.choice(notes)} {random.choice(scales)}"
    
    # Create a natural language phrase for the model
    phrases = [
        f" The melody modulates between {k1} and {k2}.",
        f" This piece explores a fusion of {k1} and {k2} tonalities.",
        f" The harmony shifts unpredictably from {k1} to {k2}.",
        f" Written in the keys of {k1} and {k2}."
    ]
    
    return random.choice(phrases)

def match_target_amplitude(sound, target_dBFS):
    change_in_dBFS = target_dBFS - sound.dBFS
    return sound.apply_gain(change_in_dBFS)

def process_audio(file_path):
    """Normalize and Apply Fades using Pydub"""
    try:
        song = AudioSegment.from_wav(file_path)
        
        # 1. Normalize
        song = match_target_amplitude(song, TARGET_DBFS)
        
        # 2. Fade In / Out
        song = song.fade_in(FADE_DURATION).fade_out(FADE_DURATION)
        
        # 3. Overwrite the file with processed version
        song.export(file_path, format="wav")
        return True
    except Exception as e:
        print(f"Pydub Error: {e}")
        return False

# --- AI LOADER ---
def load_model():
    global current_model
    print(f"Loading {MODEL_VERSION}...")
    current_model = MelodyFlow.get_pretrained(MODEL_VERSION)
    current_model.set_generation_params(duration=Target_Duration)
    print("Model Loaded.")

# --- GENERATION WORKER ---
def generate_loop():
    while True:
        if song_queue.full():
            time.sleep(1)
            continue

        base_prompt = random.choice(PROMPTS)
        key_modifier = get_key_modifier() # <--- Generate the keys
        
        # Combine them
        full_prompt = base_prompt + key_modifier
        
        print(f"--- Generating: {full_prompt} ---")
        
        try:
            with torch.no_grad():
                # We send the FULL prompt to the AI
                output = current_model.generate([full_prompt], progress=False)
            
            filename_base = f"track_{int(time.time())}"
            save_path_root = os.path.join(OUTPUT_FOLDER, filename_base)
            
            # Save Raw first
            audio_write(
                save_path_root, 
                output[0].cpu(), 
                current_model.sample_rate, 
                strategy="loudness", 
                loudness_headroom_db=14
            )
            
            final_file_path = save_path_root + ".wav"

            print("Processing Audio (Fades/Norm)...")
            process_audio(final_file_path)

            print("Analyzing BPM...")
            y, sr = librosa.load(final_file_path)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            bpm = float(tempo) if np.isscalar(tempo) else float(tempo[0])
            print(f"Done. BPM: {bpm}")

            song_data = {
                "url": f"http://localhost:5000/tracks/{filename_base}.wav",
                "bpm": bpm,
                # Send the full prompt so the UI shows the specific keys used
                "prompt": full_prompt 
            }
            
            song_queue.put(song_data)
            
        except Exception as e:
            print(f"Generation Error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(1)

# --- FLASK ROUTES ---
@app.route('/tracks/<path:filename>')
def serve_track(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

@socketio.on('connect')
def handle_connect():
    print("Client connected")
    check_and_send_track()

@socketio.on('request_next')
def handle_next_request():
    print("Client requested next track")
    check_and_send_track()

def check_and_send_track():
    if song_queue.empty():
        emit('status', {'msg': 'Buffering...'})
        return
    track = song_queue.get()
    emit('play_track', track)

if __name__ == '__main__':
    load_model()
    t = threading.Thread(target=generate_loop)
    t.daemon = True
    t.start()
    print("Server starting on port 5000...")
    socketio.run(app, port=5000, allow_unsafe_werkzeug=True)