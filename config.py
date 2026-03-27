import torch

MODEL_ID = "microsoft/Phi-3-mini-4k-instruct"

def get_device():
    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return "cuda"
    return "cpu"

DEVICE = get_device()

# Generation defaults
MAX_NEW_TOKENS = 512
TEMPERATURE = 0.7
DO_SAMPLE = True

# Backend: "transformers" or "ollama"
BACKEND = "ollama" ## transformers
OLLAMA_MODEL = "phi3:mini"
