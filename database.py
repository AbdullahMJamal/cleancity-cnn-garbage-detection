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

-- Audit trail: one row for everything that happens to a report
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id  INTEGER NOT NULL,
    at         TEXT NOT NULL,
    message    TEXT NOT NULL
);
"""

STATUS_EVENTS = {
    "pending":     "Report reopened — back in triage queue",
    "in_progress": "Cleanup team dispatched",
    "done":        "Site marked as cleaned",
    "rejected":    "Report rejected by team",
}


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

    def events(self, report_id):
        with self._connect() as conn:
            rows = conn.execute('SELECT at, message FROM events WHERE report_id = ? ORDER BY id',
                                (report_id,)).fetchall()
        return [dict(r) for r in rows]

    def all_events(self):
        """All audit-trail entries grouped by report id: {report_id: [events...]}"""
        grouped = {}
        with self._connect() as conn:
            for r in conn.execute('SELECT report_id, at, message FROM events ORDER BY id'):
                grouped.setdefault(r['report_id'], []).append({'at': r['at'], 'message': r['message']})
        return grouped

    def count(self):
        with self._connect() as conn:
            return conn.execute('SELECT COUNT(*) FROM reports').fetchone()[0]

    # ── Write ─────────────────────────────────────────────────────────────────
    @staticmethod
    def _log(conn, report_id, message, at=None):
        conn.execute('INSERT INTO events (report_id, at, message) VALUES (?,?,?)',
                     (report_id, at or now(), message))

    @staticmethod
    def describe_ai(ai_result):
        if ai_result.get('garbage_type', 'Unknown') == 'Unknown':
            return 'AI model unavailable — manual inspection needed'
        return (f"CNN classified: {ai_result['garbage_type']} "
                f"({ai_result['confidence']}% confidence, {ai_result['danger_level']} danger)")

    def add(self, photo, latitude, longitude, address, description, ai_result,
            status='pending', submitted_at=None, updated_at=None):
        with self._connect() as conn:
            cur = conn.execute(
                'INSERT INTO reports (photo, latitude, longitude, address, description,'
                ' status, submitted_at, updated_at, ai_result) VALUES (?,?,?,?,?,?,?,?,?)',
                (photo, latitude, longitude, address, description, status,
                 submitted_at or now(), updated_at, json.dumps(ai_result)))
            report_id = cur.lastrowid
            at = submitted_at or now()
            self._log(conn, report_id, 'Report submitted by citizen via web form', at)
            self._log(conn, report_id, self.describe_ai(ai_result), at)
            if status != 'pending':
                self._log(conn, report_id, STATUS_EVENTS[status], updated_at or at)
            return report_id

    def set_status(self, report_id, status):
        """Returns True if the report existed and was updated."""
        if status not in STATUSES:
            raise ValueError(f'Invalid status: {status}')
        with self._connect() as conn:
            cur = conn.execute('UPDATE reports SET status = ?, updated_at = ? WHERE id = ?',
                               (status, now(), report_id))
            if cur.rowcount != 1:
                return False
            self._log(conn, report_id, STATUS_EVENTS[status])
            return True

    def set_ai_result(self, report_id, ai_result):
        """Store a new CNN result (used by "Re-classify"). Returns True if the report exists."""
        with self._connect() as conn:
            cur = conn.execute('UPDATE reports SET ai_result = ?, updated_at = ? WHERE id = ?',
                               (json.dumps(ai_result), now(), report_id))
            if cur.rowcount != 1:
                return False
            self._log(conn, report_id, 'Re-classified — ' + self.describe_ai(ai_result))
            return True

    def delete(self, report_id):
        """Deletes a report and returns it (so the caller can remove the photo), or None."""
        report = self.get(report_id)
        if report:
            with self._connect() as conn:
                conn.execute('DELETE FROM reports WHERE id = ?', (report_id,))
                conn.execute('DELETE FROM events WHERE report_id = ?', (report_id,))
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
