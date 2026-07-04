"""
Database Layer
==============
SQLite database for logging predictions and user feedback.
Enables monitoring, analytics, and future retraining.
"""

import sqlite3
import hashlib
import time
import os
from datetime import datetime
from typing import Optional


class Database:
    """
    Manages SQLite database for prediction logging
    and user feedback collection.
    """

    def __init__(self, db_path: str = "predictions.db"):
        self.db_path = os.path.join(
            os.path.dirname(__file__), db_path)
        self._init_db()

    def _get_connection(self):
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create tables if they do not exist."""
        conn = self._get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT    NOT NULL,
                    source          TEXT,
                    text_hash       TEXT,
                    text_length     INTEGER,
                    prediction      INTEGER,
                    confidence      REAL,
                    tier            TEXT,
                    model_used      TEXT,
                    processing_ms   REAL
                );

                CREATE TABLE IF NOT EXISTS feedback (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_id   INTEGER NOT NULL,
                    timestamp       TEXT    NOT NULL,
                    correct         INTEGER NOT NULL,
                    comment         TEXT,
                    FOREIGN KEY (prediction_id)
                        REFERENCES predictions(id)
                );

                CREATE INDEX IF NOT EXISTS
                    idx_predictions_timestamp
                    ON predictions(timestamp);

                CREATE INDEX IF NOT EXISTS
                    idx_predictions_tier
                    ON predictions(tier);
            """)
            conn.commit()
        finally:
            conn.close()

    def log_prediction(self,
                       source      : str,
                       text_length : int,
                       prediction  : int,
                       confidence  : float,
                       tier        : str,
                       model_used  : str,
                       processing_ms: float) -> int:
        """
        Log a prediction to the database.
        Stores a hash of the source, not the raw text,
        to protect user privacy.
        Returns the prediction ID.
        """
        text_hash = hashlib.sha256(
            source.encode()).hexdigest()[:16]

        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO predictions
                    (timestamp, source, text_hash,
                     text_length, prediction, confidence,
                     tier, model_used, processing_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat(),
                source[:200],
                text_hash,
                text_length,
                prediction,
                confidence,
                tier,
                model_used,
                processing_ms
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def log_feedback(self,
                     prediction_id: int,
                     correct      : bool,
                     comment      : Optional[str] = None) -> bool:
        """
        Log user feedback for a prediction.
        Returns True if prediction_id exists, False otherwise.
        """
        conn = self._get_connection()
        try:
            # Check prediction exists
            row = conn.execute(
                "SELECT id FROM predictions WHERE id = ?",
                (prediction_id,)
            ).fetchone()

            if not row:
                return False

            conn.execute("""
                INSERT INTO feedback
                    (prediction_id, timestamp, correct, comment)
                VALUES (?, ?, ?, ?)
            """, (
                prediction_id,
                datetime.utcnow().isoformat(),
                1 if correct else 0,
                comment
            ))
            conn.commit()
            return True
        finally:
            conn.close()

    def total_predictions(self) -> int:
        """Returns total number of predictions logged."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as count FROM predictions"
            ).fetchone()
            return row["count"]
        finally:
            conn.close()

    def get_stats(self) -> dict:
        """
        Returns prediction statistics for monitoring dashboard.
        """
        conn = self._get_connection()
        try:
            total = conn.execute(
                "SELECT COUNT(*) as n FROM predictions"
            ).fetchone()["n"]

            fake_count = conn.execute(
                "SELECT COUNT(*) as n FROM predictions "
                "WHERE prediction = 1"
            ).fetchone()["n"]

            real_count = conn.execute(
                "SELECT COUNT(*) as n FROM predictions "
                "WHERE prediction = 0"
            ).fetchone()["n"]

            tier_dist = conn.execute("""
                SELECT tier, COUNT(*) as count
                FROM predictions
                GROUP BY tier
                ORDER BY count DESC
            """).fetchall()

            avg_confidence = conn.execute("""
                SELECT AVG(confidence) as avg_conf
                FROM predictions
            """).fetchone()["avg_conf"]

            avg_speed = conn.execute("""
                SELECT AVG(processing_ms) as avg_ms
                FROM predictions
            """).fetchone()["avg_ms"]

            feedback_stats = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(correct) as correct_count
                FROM feedback
            """).fetchone()

            recent = conn.execute("""
                SELECT timestamp, prediction,
                       confidence, tier, processing_ms
                FROM predictions
                ORDER BY id DESC
                LIMIT 10
            """).fetchall()

            return {
                "total_predictions"   : total,
                "fake_predictions"    : fake_count,
                "real_predictions"    : real_count,
                "fake_percentage"     : round(
                    fake_count / total * 100, 1) if total > 0 else 0,
                "tier_distribution"   : [
                    {"tier": r["tier"], "count": r["count"]}
                    for r in tier_dist
                ],
                "avg_confidence"      : round(
                    avg_confidence, 4) if avg_confidence else 0,
                "avg_processing_ms"   : round(
                    avg_speed, 1) if avg_speed else 0,
                "feedback_total"      : feedback_stats["total"],
                "feedback_correct"    : feedback_stats["correct_count"],
                "recent_predictions"  : [
                    {
                        "timestamp" : r["timestamp"],
                        "verdict"   : "FAKE" if r["prediction"] == 1
                                      else "REAL",
                        "confidence": round(r["confidence"], 3),
                        "tier"      : r["tier"],
                        "speed_ms"  : r["processing_ms"]
                    }
                    for r in recent
                ]
            }
        finally:
            conn.close()
