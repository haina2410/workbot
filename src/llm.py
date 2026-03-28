from openai import OpenAI


class LLMClient:
    """Thin wrapper around OpenAI SDK with configurable base_url."""

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def invoke(self, prompt: str) -> str:
        """Send a single user message, return the assistant's text response."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        return response.choices[0].message.content
