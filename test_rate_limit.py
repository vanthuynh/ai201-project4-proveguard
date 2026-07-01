"""
Rate-limit smoke test: 12 rapid POST /submit requests against the Flask test client.
Signal functions are patched so no real Groq API calls are made.
Expected output: 10 × 200, then 2 × 429.
"""
import os
os.environ.setdefault("GROQ_API_KEY", "test-key")

from unittest.mock import patch

# Patch at the module level before app resolves the imports
with patch("signals.llm_signal.get_llm_score", return_value=0.5), \
     patch("signals.stylometric_signal.get_stylometric_score", return_value=0.5):
    from app import app, init_db

init_db()

PAYLOAD = {"text": "This is a test submission.", "creator_id": "rate-limit-tester"}

codes = []
with app.test_client() as client:
    for i in range(12):
        # Patch the names as bound in app's namespace
        with patch("app.get_llm_score", return_value=0.5), \
             patch("app.get_stylometric_score", return_value=0.5):
            resp = client.post("/submit", json=PAYLOAD)
        codes.append(resp.status_code)
        print(f"Request {i + 1:2d}: {resp.status_code}")

print()
print(" ".join(str(c) for c in codes))

allowed = codes[:10]
blocked = codes[10:]
assert all(c == 200 for c in allowed), f"Expected 200s, got {allowed}"
assert all(c == 429 for c in blocked), f"Expected 429s, got {blocked}"
print("\nAll assertions passed.")
