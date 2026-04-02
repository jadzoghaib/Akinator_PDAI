from transformers import pipeline
import torch

# Load the local Whisper model for ASR
ASR_MODEL_ID = "openai/whisper-tiny"

# Initialize the pipeline
# Using CPU by default, switch device to 0 if CUDA is available
device = 0 if torch.cuda.is_available() else -1
transcribe_pipeline = pipeline("automatic-speech-recognition", model=ASR_MODEL_ID, device=device)

def transcribe_audio(file_path: str) -> str:
    """
    Transcribes the given audio file using the local Whisper model.
    """
    result = transcribe_pipeline(file_path)
    return result["text"].strip()
