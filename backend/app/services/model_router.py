from typing import Dict, Any


class ModelRouter:
    """Initial provider abstraction for FlowMind AI.

    This is a starter implementation for Module 3. Replace mock responses with
    actual OpenAI and additional provider integrations.
    """

    def available_models(self) -> Dict[str, list[str]]:
        return {
            "openai": ["gpt-4.1-mini", "gpt-4.1", "gpt-5-mini"],
            "mock": ["mock-basic"],
        }

    async def generate(self, provider: str, model: str, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        if provider == "mock":
            return {
                "provider": provider,
                "model": model,
                "content": f"Mock response for prompt: {prompt}",
                "usage": {"input_tokens": 0, "output_tokens": 0},
            }

        # Placeholder for OpenAI or other providers
        return {
            "provider": provider,
            "model": model,
            "content": "Provider integration not implemented yet.",
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
