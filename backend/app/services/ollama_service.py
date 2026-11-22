import ollama
from app.core.config import settings

class OllamaService:
    def __init__(self):
        self.client = ollama.Client(host=settings.ollama_base_url)

    def chat(self, system: str, prompt: str) -> str:
        response = self.client.chat(
            model=settings.ollama_chat_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.1},
        )
        return response["message"]["content"].strip()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embed(model=settings.ollama_embed_model, input=texts)
        return response["embeddings"]

ollama_service = OllamaService()
