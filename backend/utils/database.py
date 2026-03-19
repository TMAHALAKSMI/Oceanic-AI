"""
SQLite database manager for Ocean Waste Detection System.
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS detections (
    id               TEXT PRIMARY KEY,
    filename         TEXT NOT NULL,
    timestamp        TEXT NOT NULL,
    waste_detected   INTEGER NOT NULL DEFAULT 0,
    total_detections INTEGER NOT NULL DEFAULT 0,
    waste_types      TEXT NOT NULL DEFAULT '{}',
    confidence_avg   REAL NOT NULL DEFAULT 0.0,
    ocean_health_score REAL NOT NULL DEFAULT 1.0,
    upload_path      TEXT NOT NULL,
    result_path      TEXT NOT NULL,
    detections_json  TEXT NOT NULL DEFAULT '[]',
    processing_time  REAL NOT NULL DEFAULT 0.0
);
"""

CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_timestamp ON detections (timestamp DESC);
"""


class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = str(db_path)
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.execute(CREATE_TABLE)
            conn.execute(CREATE_INDEX)
            conn.commit()
        logger.info(f"Database ready: {self.db_path}")

    # ── Write ────────────────────────────────────────────────────────────────

    def save_detection(self, record: Dict[str, Any]):
        sql = """
        INSERT INTO detections
            (id, filename, timestamp, waste_detected, total_detections,
             waste_types, confidence_avg, ocean_health_score,
             upload_path, result_path, detections_json, processing_time)
        VALUES
            (:id, :filename, :timestamp, :waste_detected, :total_detections,
             :waste_types, :confidence_avg, :ocean_health_score,
             :upload_path, :result_path, :detections_json, :processing_time)
        """
        with self._conn() as conn:
            conn.execute(sql, record)
            conn.commit()

    def delete_detection(self, detection_id: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM detections WHERE id = ?", (detection_id,))
            conn.commit()

    # ── Read ─────────────────────────────────────────────────────────────────

    def get_detection(self, detection_id: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM detections WHERE id = ?", (detection_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def get_history(self, limit: int = 20, offset: int = 0) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM detections ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_total_count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0]

    def get_stats(self) -> Dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
            total_waste = conn.execute(
                "SELECT SUM(total_detections) FROM detections"
            ).fetchone()[0] or 0
            avg_conf = conn.execute(
                "SELECT AVG(confidence_avg) FROM detections WHERE total_detections > 0"
            ).fetchone()[0] or 0.0
            polluted = conn.execute(
                "SELECT COUNT(*) FROM detections WHERE waste_detected = 1"
            ).fetchone()[0]

        # Most common waste type
        records = self.get_history(limit=500)
        label_counts: Dict[str, int] = {}
        for r in records:
            wt = r.get("waste_types", {})
            if isinstance(wt, str):
                wt = json.loads(wt)
            for label, cnt in wt.items():
                label_counts[label] = label_counts.get(label, 0) + cnt

        most_common = max(label_counts, key=label_counts.get) if label_counts else "N/A"
        clean_pct = round((total - polluted) / max(total, 1) * 100, 1)
        poll_pct  = round(polluted / max(total, 1) * 100, 1)

        return {
            "total_analyses": total,
            "total_waste_items": int(total_waste),
            "avg_confidence": round(avg_conf * 100, 1),
            "most_common_waste": most_common,
            "clean_ocean_pct": clean_pct,
            "polluted_ocean_pct": poll_pct,
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict:
        d = dict(row)
        for key in ("waste_types", "detections_json"):
            if isinstance(d.get(key), str):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        d["waste_detected"] = bool(d.get("waste_detected"))
        return d
