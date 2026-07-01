import os
import uuid
import sqlite3
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from signals.llm_signal import get_llm_score
from signals.stylometric_signal import get_stylometric_score

load_dotenv()

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")
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


def classify(confidence: float) -> tuple[str, str]:
    """Maps a confidence score to (attribution, label) per the spec thresholds."""
    pct = int(confidence * 100)
    if confidence >= 0.75:
        return (
            "AI",
            f"⚠️ AI-Generated Content — Our system is highly confident ({pct}%) "
            "this content was AI-generated. If you are the creator and believe "
            "this is incorrect, you can submit an appeal.",
        )
    if confidence >= 0.45:
        return (
            "UNCERTAIN",
            f"? Attribution Unclear — Our system cannot confidently determine "
            f"whether this content is human- or AI-written (confidence: {pct}%). "
            "The creator may appeal if they believe the classification is inaccurate.",
        )
    return (
        "HUMAN",
        f"✓ Likely Human-Written — Our analysis suggests this content was written "
        f"by a person ({pct}% confidence). Attribution signals indicate authentic "
        "human authorship.",
    )


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    creator_id = (data.get("creator_id") or "").strip()

    if not text or not creator_id:
        return jsonify({"error": "text and creator_id are required"}), 400

    # Signal 1: LLM holistic classifier
    llm_score = get_llm_score(text)

    # Signal 2: Stylometric heuristics
    stylometric_score = get_stylometric_score(text)

    confidence = round(
        (LLM_WEIGHT * llm_score) + (STYLOMETRIC_WEIGHT * stylometric_score), 4
    )

    attribution, label = classify(confidence)
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
    data = request.get_json(silent=True) or {}
    content_id = (data.get("content_id") or "").strip()
    creator_reasoning = (data.get("creator_reasoning") or "").strip()

    if not content_id or not creator_reasoning:
        return jsonify({"error": "content_id and creator_reasoning are required"}), 400

    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT status FROM audit_log WHERE content_id = ?", (content_id,)
    ).fetchone()

    if row is None:
        conn.close()
        return jsonify({"error": "content_id not found"}), 404

    if row[0] != "classified":
        conn.close()
        return jsonify({"error": f"entry is already '{row[0]}' and cannot be appealed"}), 409

    timestamp = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """UPDATE audit_log
           SET status = 'under_review',
               appeal_reasoning = ?,
               appeal_timestamp = ?
           WHERE content_id = ?""",
        (creator_reasoning, timestamp, content_id),
    )
    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": f"Appeal received. Entry {content_id} is now under_review.",
    })


def get_log() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT content_id, creator_id, llm_score, stylometric_score,
                  confidence, attribution, label, status,
                  appeal_reasoning, appeal_timestamp, created_at
           FROM audit_log
           ORDER BY created_at DESC
           LIMIT 50"""
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.route("/log", methods=["GET"])
def log():
    return jsonify({"entries": get_log()})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
