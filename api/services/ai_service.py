from __future__ import annotations

import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

from .models import ChatResult


class AiService:
    def __init__(self) -> None:
        self.use_fake_ai = os.getenv("USE_FAKE_AI", "true").lower() == "true"
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

    def send_chat_message(self, message: str, max_output_tokens: int) -> ChatResult:
        if self.use_fake_ai:
            return self._fake_response(message)

        endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if api_key:
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=self.api_version,
            )
        else:
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(managed_identity_client_id=os.getenv("AZURE_CLIENT_ID")),
                "https://cognitiveservices.azure.com/.default",
            )
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider,
                api_version=self.api_version,
            )

        response = client.chat.completions.create(
            model=self.deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You are a concise assistant for an Azure budget guardrails demo.",
                },
                {"role": "user", "content": message},
            ],
            max_tokens=max_output_tokens,
        )

        choice = response.choices[0]
        usage = response.usage
        return ChatResult(
            text=choice.message.content or "",
            model=self.deployment,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
        )

    def _fake_response(self, message: str) -> ChatResult:
        text = (
            "Fake AI response: this request passed the current budget guardrails. "
            f"You asked: {message}"
        )
        prompt_tokens = max(1, len(message.split()) * 2)
        completion_tokens = max(1, len(text.split()) * 2)
        return ChatResult(
            text=text,
            model="fake-demo-model",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
