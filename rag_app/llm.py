"""Which language model the app talks to, read from .env.

LLM_URL      base URL of any OpenAI-compatible chat endpoint
LLM_API_KEY  its key (may stay empty for a local server such as Ollama)
LLM_MODEL    the model name

Google Gemini stays the default: when none of the three is set, the older
GOOGLE_API_KEY / GOOGLE_MODEL variables and the Google endpoint are used,
so an existing .env keeps working unchanged.
"""
import os
from pathlib import Path
from typing import NamedTuple

import dotenv

ROOT = Path(__file__).resolve().parents[1]
GOOGLE_URL = 'https://generativelanguage.googleapis.com/v1beta/openai/'
GOOGLE_MODEL = 'gemini-3.5-flash-lite'
PLACEHOLDERS = {'', 'your_google_api_key_here', 'your_api_key_here'}


class LLMConfig(NamedTuple):
    url: str
    key: str
    model: str

    @property
    def usable(self):
        """A key is needed, except for a custom LLM_URL (local servers often take none)."""
        return self.key not in PLACEHOLDERS or self.url != GOOGLE_URL


def load_config():
    dotenv.load_dotenv(ROOT / '.env')
    url = (os.getenv('LLM_URL') or '').strip() or GOOGLE_URL
    key = (os.getenv('LLM_API_KEY') or os.getenv('GOOGLE_API_KEY') or '').strip()
    model = (os.getenv('LLM_MODEL') or os.getenv('GOOGLE_MODEL') or '').strip() or GOOGLE_MODEL
    return LLMConfig(url, key, model)


MISSING_KEY = 'Set LLM_API_KEY (or GOOGLE_API_KEY) in .env to generate answers.'


def client(config, timeout=45):
    from openai import OpenAI
    key = config.key if config.key not in PLACEHOLDERS else 'not-needed'
    return OpenAI(api_key=key, base_url=config.url, timeout=timeout, max_retries=0)


def complete_json(config, system, user, timeout=45):
    """One JSON-mode chat call. Returns (text, usage) with usage = model and token counts."""
    response = client(config, timeout).chat.completions.create(
        model=config.model, temperature=0, response_format={'type': 'json_object'},
        messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}])
    usage = response.usage
    return (response.choices[0].message.content or '',
            dict(model=config.model,
                 input_tokens=usage.prompt_tokens if usage else None,
                 output_tokens=usage.completion_tokens if usage else None))
