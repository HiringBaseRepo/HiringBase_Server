"""AI provider and model defaults."""

DEFAULT_HF_LLM_MODEL = "Qwen/Qwen3-8B"
HUGGINGFACE_INFERENCE_API_BASE_URL = "https://api-inference.huggingface.co/models"

DEFAULT_GROQ_MODEL = "qwen/qwen3-32b"
DEFAULT_MISTRAL_MODEL = "mistral-ocr-latest"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_SPACY_MODEL = "en_core_web_md"


def build_hf_inference_api_url(model_name: str) -> str:
    """Build Hugging Face inference URL for model name."""
    return f"{HUGGINGFACE_INFERENCE_API_BASE_URL}/{model_name}"
