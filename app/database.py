"""
database.py
-----------
SQLite-based local analysis history storage for Parkinova.

Provides the AnalysisDatabase class for persisting and querying MRI analysis
records without any external ORM dependencies.
"""

import json
import logging
import os
import sys
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default DB path: <repo-root>/data/parkinova_history.db
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    _ROOT_DIR = Path(sys.executable).resolve().parent
else:
    _ROOT_DIR = Path(__file__).resolve().parent.parent

_LEGACY_DB_PATH = _ROOT_DIR / "data" / "neuroscan_history.db"
_NEW_DB_PATH = _ROOT_DIR / "data" / "parkinova_history.db"

# Auto-migrate legacy database if new one does not exist yet
if not _NEW_DB_PATH.exists() and _LEGACY_DB_PATH.exists():
    try:
        import shutil
        shutil.copy2(str(_LEGACY_DB_PATH), str(_NEW_DB_PATH))
    except Exception:
        pass

_DEFAULT_DB_PATH = str(_NEW_DB_PATH if _NEW_DB_PATH.exists() or not _LEGACY_DB_PATH.exists() else _LEGACY_DB_PATH)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS analyses (
    id               TEXT PRIMARY KEY,
    patient_code     TEXT,
    image_filename   TEXT,
    image_path       TEXT,
    predicted_class  TEXT,
    model_scores     TEXT,
    model_version    TEXT,
    model_name       TEXT,
    input_shape      TEXT,
    preprocessing_info TEXT,
    created_at       TEXT,
    patient_data     TEXT,
    logged_in_user   TEXT
);
"""


class AnalysisDatabase:
    """
    Manages a local SQLite database for storing MRI analysis history.

    Parameters
    ----------
    db_path : str, optional
        Absolute or relative path to the SQLite database file.
        When *None* (default) the database is placed at
        ``<project_root>/data/parkinova_history.db``.
    """

    def __init__(self, db_path: str = None) -> None:
        self._db_path: str = db_path if db_path is not None else _DEFAULT_DB_PATH
        self._session_start: datetime = datetime.now(tz=timezone.utc)
        self._conn: Optional[sqlite3.Connection] = None

        # Ensure the parent directory exists (skip for in-memory DBs).
        if self._db_path != ":memory:":
            parent = os.path.dirname(self._db_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

        try:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrent read performance.
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
            logger.info("Connected to database: %s", self._db_path)
            self.initialize()
        except sqlite3.Error as exc:
            logger.error("Failed to connect to database '%s': %s", self._db_path, exc)
            raise

    # ------------------------------------------------------------------
    # Schema initialisation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """
        Create the ``analyses`` table if it does not already exist.

        This method is called automatically by ``__init__`` but may be
        called again safely (uses ``CREATE TABLE IF NOT EXISTS``).
        """
        try:
            with self._conn:
                self._conn.execute(_CREATE_TABLE_SQL)
                # Ensure columns added in updates exist in older databases
                cursor = self._conn.execute("PRAGMA table_info(analyses);")
                existing_cols = {col["name"] for col in cursor.fetchall()}
                if "patient_data" not in existing_cols:
                    self._conn.execute("ALTER TABLE analyses ADD COLUMN patient_data TEXT;")
                if "logged_in_user" not in existing_cols:
                    self._conn.execute("ALTER TABLE analyses ADD COLUMN logged_in_user TEXT;")
                if "spiral_data" not in existing_cols:
                    self._conn.execute("ALTER TABLE analyses ADD COLUMN spiral_data TEXT;")
            logger.debug("Database schema initialised.")
        except sqlite3.Error as exc:
            logger.error("Failed to initialise database schema: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def save_analysis(self, record: dict) -> str:
        """
        Insert a new analysis record and return its generated UUID.

        Parameters
        ----------
        record : dict
            Expected keys (all optional unless noted):

            * ``patient_code``       – str | None
            * ``image_filename``     – str  *(required)*
            * ``image_path``         – str  *(required)*
            * ``predicted_class``    – str  *(required)*
            * ``model_scores``       – dict (serialised to JSON)
            * ``model_version``      – str
            * ``model_name``         – str
            * ``input_shape``        – str
            * ``preprocessing_info`` – dict (serialised to JSON)

        Returns
        -------
        str
            The ``analysis_id`` (UUID v4) assigned to the new record.

        Raises
        ------
        sqlite3.Error
            Re-raised if the INSERT fails.
        """
        analysis_id = str(uuid.uuid4())
        created_at = datetime.now(tz=timezone.utc).isoformat()

        model_scores = record.get("model_scores", {})
        preprocessing_info = record.get("preprocessing_info", {})
        patient_data = record.get("patient_data")
        logged_in_user = record.get("logged_in_user", "")
        spiral_data = record.get("spiral_data")

        model_scores_json = (
            json.dumps(model_scores) if isinstance(model_scores, dict) else model_scores
        )
        preprocessing_info_json = (
            json.dumps(preprocessing_info)
            if isinstance(preprocessing_info, dict)
            else preprocessing_info
        )
        patient_data_json = (
            json.dumps(patient_data)
            if isinstance(patient_data, dict)
            else (patient_data if isinstance(patient_data, str) else None)
        )
        spiral_data_json = (
            json.dumps(spiral_data)
            if isinstance(spiral_data, dict)
            else (spiral_data if isinstance(spiral_data, str) else None)
        )

        sql = """
            INSERT INTO analyses (
                id, patient_code, image_filename, image_path,
                predicted_class, model_scores, model_version,
                model_name, input_shape, preprocessing_info, created_at,
                patient_data, logged_in_user, spiral_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            analysis_id,
            record.get("patient_code"),
            record.get("image_filename"),
            record.get("image_path"),
            record.get("predicted_class"),
            model_scores_json,
            record.get("model_version"),
            record.get("model_name"),
            record.get("input_shape"),
            preprocessing_info_json,
            created_at,
            patient_data_json,
            logged_in_user,
            spiral_data_json,
        )

        try:
            with self._conn:
                self._conn.execute(sql, params)
            logger.info("Saved analysis record id=%s", analysis_id)
            return analysis_id
        except sqlite3.Error as exc:
            logger.error("Failed to save analysis record: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_all_analyses(self, limit: int = 100) -> list[dict]:
        """
        Retrieve the most recent analysis records.

        Parameters
        ----------
        limit : int
            Maximum number of records to return (default 100).

        Returns
        -------
        list[dict]
            Records ordered by ``created_at`` descending. JSON fields
            (``model_scores``, ``preprocessing_info``) are deserialised
            back to Python dicts.
        """
        sql = """
            SELECT * FROM analyses
            ORDER BY created_at DESC
            LIMIT ?
        """
        try:
            cursor = self._conn.execute(sql, (limit,))
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
        except sqlite3.Error as exc:
            logger.error("Failed to fetch analyses: %s", exc)
            return []

    def get_recent_analyses(self, limit: int = 5) -> list[dict]:
        """
        Retrieve the most recent *limit* analysis records.

        Alias for :meth:`get_all_analyses` with a smaller default limit,
        used by the Dashboard to show a brief recent-history summary.

        Parameters
        ----------
        limit : int
            Maximum number of records to return (default 5).

        Returns
        -------
        list[dict]
            Records ordered by ``created_at`` descending.
        """
        return self.get_all_analyses(limit=limit)

    def get_analysis_by_id(self, analysis_id: str) -> dict | None:
        """
        Retrieve a single analysis record by its UUID.

        Parameters
        ----------
        analysis_id : str
            The UUID of the record to fetch.

        Returns
        -------
        dict | None
            The record as a dict, or *None* if not found.
        """
        sql = "SELECT * FROM analyses WHERE id = ?"
        try:
            cursor = self._conn.execute(sql, (analysis_id,))
            row = cursor.fetchone()
            if row is None:
                logger.debug("No record found with id=%s", analysis_id)
                return None
            return self._row_to_dict(row)
        except sqlite3.Error as exc:
            logger.error("Failed to fetch analysis id=%s: %s", analysis_id, exc)
            return None

    # ------------------------------------------------------------------
    # Delete operations
    # ------------------------------------------------------------------

    def delete_analysis(self, analysis_id: str) -> bool:
        """
        Delete a single analysis record by its UUID.

        Parameters
        ----------
        analysis_id : str
            The UUID of the record to delete.

        Returns
        -------
        bool
            ``True`` if a row was deleted, ``False`` otherwise.
        """
        sql = "DELETE FROM analyses WHERE id = ?"
        try:
            with self._conn:
                cursor = self._conn.execute(sql, (analysis_id,))
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info("Deleted analysis record id=%s", analysis_id)
            else:
                logger.warning("Delete requested for unknown id=%s", analysis_id)
            return deleted
        except sqlite3.Error as exc:
            logger.error("Failed to delete analysis id=%s: %s", analysis_id, exc)
            return False

    def clear_all_history(self) -> int:
        """
        Delete **all** records from the analyses table.

        Returns
        -------
        int
            The number of rows deleted.
        """
        try:
            with self._conn:
                cursor = self._conn.execute("DELETE FROM analyses")
            count = cursor.rowcount
            logger.info("Cleared all history; %d record(s) deleted.", count)
            return count
        except sqlite3.Error as exc:
            logger.error("Failed to clear history: %s", exc)
            return 0

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_session_stats(self) -> dict:
        """
        Return a summary of overall and current-session analysis counts.

        Returns
        -------
        dict
            Keys:

            * ``total_analyses``   – total rows in the database
            * ``session_analyses`` – rows added since this instance was created
            * ``latest_timestamp`` – ISO-8601 timestamp of the newest record,
              or an empty string when the table is empty
        """
        session_start_iso = self._session_start.isoformat()
        try:
            total_row = self._conn.execute(
                "SELECT COUNT(*) FROM analyses"
            ).fetchone()
            session_row = self._conn.execute(
                "SELECT COUNT(*) FROM analyses WHERE created_at >= ?",
                (session_start_iso,),
            ).fetchone()
            latest_row = self._conn.execute(
                "SELECT created_at FROM analyses ORDER BY created_at DESC LIMIT 1"
            ).fetchone()

            return {
                "total_analyses": total_row[0] if total_row else 0,
                "session_analyses": session_row[0] if session_row else 0,
                "latest_timestamp": latest_row[0] if latest_row else "",
            }
        except sqlite3.Error as exc:
            logger.error("Failed to fetch session stats: %s", exc)
            return {
                "total_analyses": 0,
                "session_analyses": 0,
                "latest_timestamp": "",
            }

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_db_path(self) -> str:
        """Return the absolute path of the database file in use."""
        return self._db_path

    def close(self) -> None:
        """Close the underlying SQLite connection gracefully."""
        if self._conn is not None:
            try:
                self._conn.close()
                self._conn = None
                logger.info("Database connection closed.")
            except sqlite3.Error as exc:
                logger.error("Error closing database connection: %s", exc)

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "AnalysisDatabase":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        """
        Convert a ``sqlite3.Row`` to a plain ``dict``, deserialising
        the JSON-encoded fields back to Python objects.
        """
        data = dict(row)

        for json_field in ("model_scores", "preprocessing_info", "patient_data"):
            raw = data.get(json_field)
            if raw:
                try:
                    data[json_field] = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(
                        "Could not deserialise JSON field '%s': %r", json_field, raw
                    )
                    # Leave as raw string rather than crashing.

        return data
