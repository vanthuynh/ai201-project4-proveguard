# ai201-project4-proveguard

**Description**

ProveGuard is a backend API that classifies submitted text as human-written or AI-generated, communicated with transparency, and allow appeals.

---

## Setup

1. Fork this repo and clone your fork locally
2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Mac/Linux
   # or: .venv\Scripts\activate  # Windows
   ```

3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and add your Groq API key
5. Run the app: `python app.py`

---

## File Structure

| Milestone | File | Function | Description |
|-----------|------|----------|-------------|
| 3 | `app.py`, `llm_signal.py` | `submit()` | Holistic classification signal detection|
| 4 | `app.py`, `stylometric_signal.py` | `submit()` | Stylometric Heuristic signal detection |
| 5 | `app.py`, `test_rate_limit.py` | `appeal()` | Label the submission text and log appeals |


---

content = """# System Implementation & Specifications

This document outlines the final implementation details, scoring mechanics, and operational thresholds for the AI text detection system.

---

## 🔍 Detection Signals

### Signal 1: LLM Classification (Groq `llama-3.3-70b-versatile`)
* **Mechanism:** Transmits the submission to Groq with a prompt requesting a qualitative assessment of whether the content reads as human or AI-generated. Captures holistic semantic and stylistic coherence.
* **Output:** Float between `0.0` (definitely human) and `1.0` (definitely AI).
* **Blind Spots:** Susceptible to flagging highly formal or cleanly written human text as AI. Can occasionally be bypassed by lightly edited/humanized AI output.

### Signal 2: Stylometric Heuristics
* **Mechanism:** Computes three core structural properties of the text using pure Python: sentence length variance, type-token ratio (vocabulary diversity), and punctuation density. Human writing typically exhibits higher variance, whereas AI text is syntactically uniform.
* **Output:** Float between `0.0` and `1.0`.
* **Blind Spots:** Inherently struggles with short texts due to a lack of statistical signal. Additionally, formal human writing (which is naturally uniform and structured) often scores similarly to AI output.

---

## 🧮 Confidence Scoring

The two signals are fused using a weighted average:

$$\\text{Confidence} = (0.60 \\times \\text{LLM\_Score}) + (0.40 \\times \\text{Stylo\_Score})$$

**Weighting Rationale:** The LLM signal is weighted higher (60%) because it evaluates contextual meaning and style rather than just rigid structure. The stylometric signal (40%) provides a vital structural cross-check but is generally less reliable on short or highly formal inputs.

### Thresholds

| Range | Classification |
| :--- | :--- |
| `>= 0.75` | **Likely AI-generated** |
| `0.41 - 0.74` | **Uncertain** |
| `<= 0.40` | **Likely human-written** |

> **Note on Asymmetry:** The threshold for AI classification is set high at `0.75` (rather than a simple majority `0.50`) because false positives—falsely accusing a human creator of using AI—are severely detrimental on a creative platform. We prioritize minimizing false positives over catching every AI submission.

### Example Submissions

**Mid-Confidence AI Input:**
> *"The relationship between monetary policy and asset price inflation has been extensively studied in the literature. Central banks face a fundamental tension between their mandate for price stability and the unintended consequences of prolonged low interest rates on equity and real estate valuations."*
* **LLM Score:** `0.8`
* **Stylo Score:** `0.7171`
* **Final Confidence:** `0.5631`
* **Label:** UNCERTAIN

**High-Confidence Human Input:**
> *"The sun dipped below the horizon, painting the sky in hues of amber and rose. I sat on the porch, coffee in hand, watching the neighborhood slowly go quiet."*
* **LLM Score:** `0.42`
* **Stylo Score:** `0.0`
* **Final Confidence:** `0.273`
* **Label:** Likely human-written

---

## 🏷️ Transparency Label Variants

Based on the final confidence score, the UI renders one of the following labels:

* **High-Confidence AI:**
    > *AI-Generated Content — Our system is highly confident (X%) this content was AI-generated. If you are the creator and believe this is incorrect, you can submit an appeal.*
* **High-Confidence Human:**
    > *"✓ Likely Human-Written — Our analysis suggests this content was written by a person (X% confidence). Attribution signals indicate authentic human authorship."*
* **Uncertain:**
    > *" Attribution Unclear — Our system cannot confidently determine whether this content is human- or AI-written (confidence: X%). The creator may appeal if they believe the classification is inaccurate."*

---

## Rate Limiting

* **Limits:** `10 requests / minute` and `100 requests / day` (per IP address).
* **Reasoning:** A legitimate human creator submitting their own original work should rarely exceed a few submissions per minute. The `10/min` limit easily accommodates normal usage while immediately halting automated flooding scripts. The `100/day` limit provides plenty of headroom for power users while mitigating bulk API abuse.

**Rate Limit Test Output (12 rapid requests):**
```
Request  1: 200
Request  2: 200
Request  3: 200
Request  4: 200
Request  5: 200
Request  6: 200
Request  7: 200
Request  8: 200
Request  9: 200
Request 10: 200
Request 11: 429
Request 12: 429

200 200 200 200 200 200 200 200 200 200 429 429

All assertions passed.
```

---

## AI Usage

1. Used Claude to generate the initial Flask app skeleton and llm_signal() function. Reviewed the output and corrected the prompt format to ensure Groq returned clean JSON rather than markdown-wrapped JSON.

2. Used Claude to generate the stylometric_signal() function. The initial version did not normalize scores correctly -- values were going above 1.0 for high-variance text. Corrected the variance normalization formula manually.
