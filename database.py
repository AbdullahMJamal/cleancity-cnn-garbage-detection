"""
Database for CleanCity reports (SQLite — built into Python, no install needed).
==============================================================================
Why SQLite instead of a JSON file?
  - Two people submitting at the same time can't overwrite each other's reports
  - Report IDs are unique (AUTOINCREMENT), even after deletes
  - Only the changed row is written, not the whole file
"""

import json
import os
import sqlite3
from datetime import datetime

STATUSES = ("pending", "in_progress", "done", "rejected")

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    photo        TEXT NOT NULL,
    latitude     TEXT NOT NULL,
    longitude    TEXT NOT NULL,
    address      TEXT NOT NULL,
    description  TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    submitted_at TEXT NOT NULL,
    updated_at   TEXT,
    ai_result    TEXT NOT NULL            -- CNN result stored as JSON text
);
"""


def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class ReportDB:
    def __init__(self, path):
        self.path = path
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _to_dict(row):
        report = dict(row)
        report['ai_result'] = json.loads(report['ai_result'])
        return report

    # ── Read ──────────────────────────────────────────────────────────────────
    def all(self, newest_first=True):
        order = 'DESC' if newest_first else 'ASC'
        with self._connect() as conn:
            rows = conn.execute(f'SELECT * FROM reports ORDER BY id {order}').fetchall()
        return [self._to_dict(r) for r in rows]

    def get(self, report_id):
        with self._connect() as conn:
            row = conn.execute('SELECT * FROM reports WHERE id = ?', (report_id,)).fetchone()
        return self._to_dict(row) if row else None

    def count(self):
        with self._connect() as conn:
            return conn.execute('SELECT COUNT(*) FROM reports').fetchone()[0]

    # ── Write ─────────────────────────────────────────────────────────────────
    def add(self, photo, latitude, longitude, address, description, ai_result,
            status='pending', submitted_at=None, updated_at=None):
        with self._connect() as conn:
            cur = conn.execute(
                'INSERT INTO reports (photo, latitude, longitude, address, description,'
                ' status, submitted_at, updated_at, ai_result) VALUES (?,?,?,?,?,?,?,?,?)',
                (photo, latitude, longitude, address, description, status,
                 submitted_at or now(), updated_at, json.dumps(ai_result)))
            return cur.lastrowid

    def set_status(self, report_id, status):
        """Returns True if the report existed and was updated."""
        if status not in STATUSES:
            raise ValueError(f'Invalid status: {status}')
        with self._connect() as conn:
            cur = conn.execute('UPDATE reports SET status = ?, updated_at = ? WHERE id = ?',
                               (status, now(), report_id))
            return cur.rowcount == 1

    def delete(self, report_id):
        """Deletes a report and returns it (so the caller can remove the photo), or None."""
        report = self.get(report_id)
        if report:
            with self._connect() as conn:
                conn.execute('DELETE FROM reports WHERE id = ?', (report_id,))
        return report

    # ── One-time import of the old reports.json ───────────────────────────────
    def import_json(self, json_path):
        """Copies reports from the old reports.json into SQLite (only if the DB is empty)."""
        if not os.path.exists(json_path) or self.count() > 0:
            return 0
        with open(json_path) as f:
            old_reports = json.load(f)
        for r in old_reports:
            self.add(r['photo'], r['latitude'], r['longitude'], r['address'],
                     r.get('description', ''), r.get('ai_result', {}),
                     status=r.get('status', 'pending'),
                     submitted_at=r.get('submitted_at'), updated_at=r.get('updated_at'))
        os.rename(json_path, json_path + '.imported')
        return len(old_reports)
