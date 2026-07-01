import os
import uuid
import sqlite3
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from signals.llm_signal import get_llm_score

load_dotenv()

app = Flask(__name__)
DB_PATH = "audit_log.db"

LLM_WEIGHT = 0.65
STYLOMETRIC_WEIGHT = 0.35


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            content_id        TEXT PRIMARY KEY,
            creator_id        TEXT NOT NULL,
            text              TEXT NOT NULL,
            llm_score         REAL,
            stylometric_score REAL,
            confidence        REAL,
            attribution       TEXT,
            label             TEXT,
            status            TEXT DEFAULT 'classified',
            appeal_reasoning  TEXT,
            appeal_timestamp  TEXT,
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def map_label(attribution: str, confidence: float) -> str:
    pct = int(confidence * 100)
    if attribution == "AI":
        return (
            f"⚠️ AI-Generated Content — Our system is highly confident ({pct}%) "
            "this content was AI-generated. If you are the creator and believe "
            "this is incorrect, you can submit an appeal."
        )
    if attribution == "UNCERTAIN":
        return (
            f"? Attribution Unclear — Our system cannot confidently determine "
            f"whether this content is human- or AI-written (confidence: {pct}%). "
            "The creator may appeal if they believe the classification is inaccurate."
        )
    return (
        f"✓ Likely Human-Written — Our analysis suggests this content was written "
        f"by a person ({pct}% confidence). Attribution signals indicate authentic "
        "human authorship."
    )


@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    creator_id = (data.get("creator_id") or "").strip()

    if not text or not creator_id:
        return jsonify({"error": "text and creator_id are required"}), 400

    # Signal 1: LLM holistic classifier
    llm_score = get_llm_score(text)

    # Signal 2: Stylometric heuristics (wired in M4)
    stylometric_score = 0.0

    confidence = round(
        (LLM_WEIGHT * llm_score) + (STYLOMETRIC_WEIGHT * stylometric_score), 4
    )

    if confidence >= 0.75:
        attribution = "AI"
    elif confidence >= 0.45:
        attribution = "UNCERTAIN"
    else:
        attribution = "HUMAN"

    label = map_label(attribution, confidence)
    content_id = str(uuid.uuid4())

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO audit_log
           (content_id, creator_id, text, llm_score, stylometric_score,
            confidence, attribution, label, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'classified')""",
        (content_id, creator_id, text, llm_score, stylometric_score,
         confidence, attribution, label),
    )
    conn.commit()
    conn.close()

    return jsonify({
        "content_id": content_id,
        "attribution": attribution,
        "confidence": confidence,
        "label": label,
        "signal_scores": {
            "llm": llm_score,
            "stylometric": stylometric_score,
        },
    })


@app.route("/appeal", methods=["POST"])
def appeal():
    # M5: update audit_log status to 'under_review', append reasoning + timestamp
    pass


@app.route("/log", methods=["GET"])
def log():
    # M5: return last 50 'under_review' entries for human review
    pass


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
