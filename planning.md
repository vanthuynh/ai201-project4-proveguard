# ProveGuard - planning.md

AI content attribution system for a writing platform. This is a pre-implementation planning document.

---

## Architecture

### Submission Flow (`POST /submit`)

When a submission is initiated, the endpoint receives the `raw text` and its associated `creator_id`. The text is then pushed through a two-stage detection pipeline:

* **Signal 1 (LLM Analysis):** The text is evaluated by the Groq `llama-3.3-70b-versatile` model, which outputs a probability score (a float between `0.0` and `1.0`).
* **Signal 2 (Stylometric Analysis):** The text is simultaneously evaluated by a pure Python stylometric module, which returns a second probability score (a float between `0.0` and `1.0`).

**Aggregation & Finalization:**
1.  **Confidence Scoring:** The two signal scores are combined via a weighted average into a single, unified confidence score.
2.  **Label Mapping:** This combined score is mapped to a designated transparency label.
3.  **Data Persistence:** An entry containing the results is written to the SQLite audit log.
4.  **Response:** The system returns a final JSON payload to the caller.

---

### Appeal Flow (`POST /appeal`)

If a classification is contested, the appeal endpoint receives the specific `content_id` alongside the `creator_reasoning`.

**Review Process:**
* **Database Update:** The system locates the corresponding SQLite audit log entry, appends the creator's reasoning, and updates the entry's status to `under_review`.
* **Human Review:** Reviewers can then access these flagged entries, complete with the creator's attached context, via the `GET /log` endpoint.

```
===============================================================================
                               SUBMISSION FLOW
===============================================================================

                                 [ Creator ]
                                      │
                                      │ raw text + creator_id
                                      ▼
                           ┌─────────────────────┐
                           │    POST /submit     │
                           │       (route)       │
                           └──────────┬──────────┘
                                      │
                 raw text ┌───────────┴───────────┐ raw text
                          ▼                       ▼
               ┌─────────────────────┐ ┌─────────────────────┐
               │    Signal 1: LLM    │ │Signal 2: Stylometric│
               │(Groq llama-3.3-70b) │ │    (pure Python)    │
               └──────────┬──────────┘ └──────────┬──────────┘
             signal score │                       │ signal score
              (0.0 - 1.0) │                       │ (0.0 - 1.0)
                          └───────────┬───────────┘
                                      │ both signal scores
                                      ▼
                           ┌─────────────────────┐
                           │ Confidence Scoring  │
                           │    weighted avg     │
                           │(0.65 LLM/0.35 styl) │
                           └──────────┬──────────┘
                                      │ combined confidence (0.0 - 1.0)
                                      ▼
                           ┌─────────────────────┐
                           │ Transparency Label  │
                           │(score → label text) │
                           └──────────┬──────────┘
                                      │ label text + confidence
                                      │ + signal scores
                                      ▼
                           ┌─────────────────────┐
                           │ Audit Log (append)  │
                           │ status="classified" │
                           └──────────┬──────────┘
                                      │ content_id
                                      ▼
                           ┌─────────────────────┐
                           │    JSON Response    │
                           └─────────────────────┘
         {content_id, attribution, confidence, label, signal_scores}


===============================================================================
                                 APPEAL FLOW
===============================================================================

                                 [ Creator ]
                                      │
                                      │ content_id + creator_reasoning
                                      ▼
                           ┌─────────────────────┐
                           │    POST /appeal     │
                           │       (route)       │
                           └──────────┬──────────┘
                                      │
                                      │ content_id
                                      ▼
                           ┌─────────────────────┐
                           │ Audit Log (update)  │
                           ├─────────────────────┤
                           │ status: classified  │
                           │   → under_review    │
                           │ + appeal_reasoning  │
                           │ + appeal_timestamp  │
                           └──────────┬──────────┘
                                      │
                                      │ content_id
                                      ▼
                           ┌─────────────────────┐
                           │    JSON Response    │
                           └─────────────────────┘
                              {status, message}
```

---

## Detection Signals (How We Catch the Bots)

To figure out if text is AI-generated, this system runs a two-pronged approach. We combine a stochastic LLM inference call with some deterministic NLP heuristics.

### Signal 1: The LLM Holistic Classifier (Groq, `llama-3.3-70b-versatile`)

**The Concept:** We ping the Groq API and ask the Llama-3.3-70b model to evaluate the holistic semantic structure of the text. It's looking for that classic AI "flavor"—stuff like predictive flow and lack of human authorial voice that you can't easily catch with simple regex. 
**Output:** A float between **0.0** and **1.0** (predicted probability of being AI-generated).
**Known Blind Spots:** LLMs are non-deterministic, so the same prompt might yield slightly different results across runs. It also struggles with heavily prompted/edited AI text (false negatives) or super rigid human academic writing (false positives).

### Signal 2: Stylometric Heuristics (pure Python)

**The Concept:** Instead of importing heavy libraries like NLTK or spaCy, this runs lightweight, pure Python string analysis to calculate three heuristics:
* **Sentence length variance:** AI models usually generate text with very uniform syntax. Low variance heavily implies AI.
* **Type-token ratio (TTR):** This measures lexical diversity. AI loves to reuse the same vocabulary, so a low TTR pushes the score toward AI.
* **Punctuation density:** AI text is usually too "clean" and lacks chaotic, informal punctuation. Low density implies AI.

**Output:** A combined float between **0.0** and **1.0**.
**Known Blind Spots:** Formal human writing naturally has low TTR and variance, which can trip up the algorithm. It also doesn't understand context or creativity.

### Signal Fusion (Weighted Average)

We combine both signals to get the final score. The LLM gets a higher weight because it actually understands semantics, but the Python stylometrics act as a deterministic anchor in case the API is acting weird.

$$	ext{Confidence} = (0.65 \times 	ext{LLM\_Score}) + (0.35 \times 	ext{Stylometric\_Score})$$

---

## Confidence Thresholds & Uncertainty

In machine learning applications, false positives (Type I errors) can ruin the user experience. On a writing platform, mislabeling a real human's hard work as AI is a disaster. Because of this, our uncertainty threshold is intentionally skewed to be conservative.

| Confidence Score | Classification |
| :--- | :--- |
| `>= 0.75` | **"Likely AI-generated"** (High-confidence AI) |
| `>= 0.45` and `< 0.75` | **"Uncertain — could be either"** (Wide safety net) |
| `< 0.45` | **"Likely human-written"** (High-confidence human) |

*Example:* A score of **0.51** lands in the "Uncertain" zone, triggering a cautious label. A score of **0.92** gives a definitive AI label. We'd rather say "we aren't sure" than accuse a real writer.

---

## Transparency Labels (Frontend UI)

Here is the exact copy we render on the frontend for the users (where **X%** is the confidence variable parsed as an integer):

> **HIGH-CONFIDENCE AI:** > ⚠️ AI-Generated Content — Our system is highly confident (X%) this content was AI-generated. If you are the creator and believe this is incorrect, you can submit an appeal.

> **HIGH-CONFIDENCE HUMAN:** > ✓ Likely Human-Written — Our analysis suggests this content was written by a person (X% confidence). Attribution signals indicate authentic human authorship.

> **UNCERTAIN:** > ? Attribution Unclear — Our system cannot confidently determine whether this content is human- or AI-written (confidence: X%). The creator may appeal if they believe the classification is inaccurate.

---

## The Appeals System (Human-in-the-Loop)

We never want the algorithm to have the final say without recourse. 

**Who can appeal:** Any `creator_id` matching the flagged `content_id`.

**Payload:** The `content_id` and a `creator_reasoning` string (their defense).

**State Change:** The backend updates the database audit log, flipping the status from `classified` to `under_review`. It also appends the reasoning and a timestamp.

**Admin View:** When an admin hits `GET /log`, they see all `under_review` entries with the raw scores and the user's defense. 
**Strict Rule:** No automated re-classification. This is strictly a human-in-the-loop review process.

---

## Anticipated Edge Cases

**Heavily edited AI output:** If a human significantly rewrites AI-generated text, the LLM signal may not catch it and stylometrics will reflect the human edits.

**Non-Native English Speakers:** Writing highly formal English as a second language often mimics AI patterns (standardized vocabulary, predictable syntax). Both signals might generate false positives here. This is a known limitation.

---

## 🔌 API Endpoints

| Method & Route | Request Body | Response Payload |
| :--- | :--- | :--- |
| `POST /submit` | `{text, creator_id}` | `{content_id, attribution, confidence, label, signal_scores}` |
| `POST /appeal` | `{content_id, creator_reasoning}` | `{status, message}` |
| `GET /log` | *None* | `{entries: [...]}` (Array of the last 50 DB logs) |

---

## AI Tooling

I'm using LLM-assisted generation to build out the boilerplate faster. Here are the development milestones:

**M3 — Submit Route & LLM Integration**
**Context:** Provide the AI with the Architecture and Signals docs.
**Task:** Generate a Flask app skeleton with a `POST /submit` stub and write the Groq API call function.
**Testing:** Manually pass 3 test strings to ensure the float output is parsing correctly before wiring it to the route.

**M4 — Stylometrics & Math Logic**
**Context:** Provide the AI with the Signals and Uncertainty docs.
**Task:** Write the pure Python NLP functions (variance, TTR, punctuation) and implement the weighted average equation.
**Testing:** Run 4 diverse strings (clear AI, clear human, 2 borderline) to ensure the standard deviation makes sense.

**M5 — Production UI Logic & CRUD**
**Context:** Provide the AI with the Labels and Appeals docs.
**Task:** Write the mapping function that converts the float score to the frontend label strings, and build out the `POST /appeal` route.
**Testing:** Verify the database state correctly mutates to `under_review` when a valid request is pushed.