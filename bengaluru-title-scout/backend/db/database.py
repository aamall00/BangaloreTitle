import sqlite3
import json
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

log = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "./title_scout.db"):
        self.db_path = db_path

    def initialize(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id          TEXT PRIMARY KEY,
                    timestamp   TEXT NOT NULL,
                    risk_level  TEXT NOT NULL,
                    doc_type    TEXT,
                    survey_no   TEXT,
                    location    TEXT,
                    flag_count  INTEGER DEFAULT 0,
                    data        TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON analyses(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_risk ON analyses(risk_level)")
            conn.commit()
        log.info(f"Database initialised at {self.db_path}")

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def save_analysis(self, analysis: Dict) -> str:
        case_id = analysis.get("id") or str(uuid.uuid4())
        analysis["id"] = case_id
        timestamp = analysis.get("timestamp") or datetime.utcnow().isoformat()
        details = analysis.get("property_details", {})

        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO analyses
                   (id, timestamp, risk_level, doc_type, survey_no, location, flag_count, data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    case_id,
                    timestamp,
                    analysis.get("risk_level", "UNKNOWN"),
                    analysis.get("document_type_detected", analysis.get("doc_type", "")),
                    details.get("survey_number", ""),
                    details.get("location", ""),
                    len(analysis.get("flags", [])),
                    json.dumps(analysis),
                ),
            )
            conn.commit()
        return case_id

    def list_analyses(self, limit: int = 50) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, timestamp, risk_level, doc_type, survey_no, location, flag_count FROM analyses ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"id": r[0], "timestamp": r[1], "risk_level": r[2], "doc_type": r[3],
             "survey_number": r[4], "location": r[5], "flag_count": r[6]}
            for r in rows
        ]

    def get_analysis(self, case_id: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT data FROM analyses WHERE id = ?", (case_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def delete_analysis(self, case_id: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM analyses WHERE id = ?", (case_id,))
            conn.commit()
