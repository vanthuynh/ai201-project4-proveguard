import os
from groq import Groq

_client = None

SYSTEM_PROMPT = """You are an AI content detection classifier. Your sole task is to analyze text and output a single floating-point number representing the probability that the text was AI-generated.

Rules:
- Output ONLY a single float between 0.0 and 1.0. No explanation, no other text.
- 0.0 means definitely human-written. 1.0 means definitely AI-generated.
- Look for: uniform sentence length, lack of personal voice, predictable structure, over-polished transitions, hedging language, and absence of authentic human idiosyncrasies."""


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _client


def get_llm_score(text: str) -> float:
    """Returns AI-generated probability (0.0–1.0) via Groq llama-3.3-70b-versatile."""
    client = _get_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this text:\n\n{text}"},
        ],
        temperature=0.1,  # low temp for near-deterministic scoring
        max_tokens=10,
    )
    raw = response.choices[0].message.content.strip()
    score = float(raw)
    return max(0.0, min(1.0, score))
