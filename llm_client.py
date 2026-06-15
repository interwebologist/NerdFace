import os
from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("OPENAI_API_BASE", "http://192.168.1.33:8080/v1"),
    api_key=os.getenv("OPENAI_API_KEY", "not-needed"),
)

DEFAULT_MODEL = os.getenv(
    "MODEL_NAME", "NVIDIA-Nemotron-3-Super-120B-A12B-UD-Q4_K_XL.gguf"
)
