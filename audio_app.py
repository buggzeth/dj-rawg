import modal
import os

# 1. Define the Custom Image
image = (
    modal.Image.debian_slim()
    .apt_install("git", "ffmpeg")
    .pip_install("huggingface_hub")
    # FIX: Use python -c instead of huggingface-cli to avoid PATH issues
    .run_commands(
        "python -c \"from huggingface_hub import snapshot_download; snapshot_download(repo_id='facebook/MelodyFlow', repo_type='space', local_dir='/root/melodyflow_src')\""
    )
    # Install the library from the downloaded source
    .run_commands(
        "cd /root/melodyflow_src && pip install ."
    )
    # Explicitly install torch/torchaudio (overriding whatever setup.py might have tried to do)
    .pip_install("torch", "torchaudio")
)

app = modal.App("melody-flow-custom", image=image)

# 2. Define the Model Class
@app.cls(gpu="any", timeout=600)
class AudioModel:
    @modal.enter()
    def load_model(self):
        # Import inside the function to ensure the container is fully built
        from audiocraft.models import MelodyFlow
        
        print("Loading MelodyFlow model...")
        self.model = MelodyFlow.get_pretrained('facebook/melodyflow-t24-30secs')
        self.model.set_generation_params(duration=30)

    @modal.method()
    def generate(self, descriptions: list[str]):
        from audiocraft.data.audio import audio_write
        
        print(f"Generating audio for: {descriptions}")
        wav = self.model.generate(descriptions)
        
        results = []
        for idx, one_wav in enumerate(wav):
            file_path = f"/tmp/output_{idx}"
            
            # Save to /tmp
            audio_write(
                file_path, 
                one_wav.cpu(), 
                self.model.sample_rate, 
                strategy="loudness", 
                loudness_compressor=True
            )
            
            # Read back bytes
            with open(f"{file_path}.wav", "rb") as f:
                results.append(f.read())
                
        return results

# 3. Local Entrypoint
@app.local_entrypoint()
def main():
    model = AudioModel()
    descriptions = ['disco beat', 'energetic EDM', 'funky groove']
    
    print("Sending request to Modal GPU...")
    audio_bytes_list = model.generate.remote(descriptions)
    
    for idx, audio_data in enumerate(audio_bytes_list):
        filename = f"melody_{idx}.wav"
        with open(filename, "wb") as f:
            f.write(audio_data)
        print(f"Saved: {filename}")