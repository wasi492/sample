"""
database.py — All database operations for the Sample Tracking System.
Handles connection, table creation, seed data, and all queries.
Uses raw sqlite3 — no ORM, by design.
"""

import sqlite3
import os
import shutil
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lab.db')
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')


def get_db():
    """Get a database connection with Row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys (off by default in SQLite)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they don't exist. Safe to call on every startup."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS samples (
            sample_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            received_from TEXT NOT NULL,
            date_received TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Under Testing',
            deleted INTEGER NOT NULL DEFAULT 0,
            folder_id INTEGER REFERENCES folders(id)
        )
    """)

    # Migration: add folder_id column if the table already existed without it
    try:
        cursor.execute("ALTER TABLE samples ADD COLUMN folder_id INTEGER REFERENCES folders(id)")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Migration: add client_report_no column if the table already existed without it
    try:
        cursor.execute("ALTER TABLE samples ADD COLUMN client_report_no INTEGER")
    except sqlite3.OperationalError:
        pass  # Column already exists

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_parameters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            unit TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sample_results (
            sample_id TEXT NOT NULL,
            parameter_id INTEGER NOT NULL,
            result TEXT NOT NULL,
            method TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
            FOREIGN KEY (parameter_id) REFERENCES test_parameters(id),
            PRIMARY KEY (sample_id, parameter_id)
        )
    """)

    # Migration: add method column if the table already existed without it
    try:
        cursor.execute("ALTER TABLE sample_results ADD COLUMN method TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()


def seed_parameters():
    """
    Seed the test_parameters table with the master list from PRD Section 6.
    Only inserts if the table is empty — safe to call on every startup.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Only seed if empty
    count = cursor.execute("SELECT COUNT(*) FROM test_parameters").fetchone()[0]
    if count > 0:
        conn.close()
        return

    parameters = [
        ("Total Solids (TS)", "%"),
        ("Total Suspended Solids (TSS)", "mg/L"),
        ("Total Dissolved Solids (TDS)", "mg/L"),
        ("Moisture Content", "%"),
        ("pH", "—"),
        ("Specific Gravity", "—"),
        ("COD", "mg/L"),
        ("BOD", "mg/L"),
        ("D.E", "%"),
        ("Total Sugar", "%"),
        ("Protein", "%"),
        ("Nitrogen", "%"),
        ("Starch", "%"),
        ("Ca", "%"),
        ("Mg", "mg/L"),
        ("SO4", "mg/L"),
        ("Cl", "mg/L"),
        ("CO3", "mg/L"),
        ("HCO3", "mg/L"),
        ("Na", "mg/L"),
        ("K", "mg/L"),
    ]

    cursor.executemany(
        "INSERT INTO test_parameters (name, unit) VALUES (?, ?)",
        parameters
    )
    conn.commit()
    conn.close()


def create_backup():
    """
    Copy lab.db into backups/ with a timestamped filename.
    Keeps only the 5 most recent backups, deletes the rest.
    Called once on app startup.
    """
    # Don't backup if the database doesn't exist yet
    if not os.path.exists(DB_PATH):
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"lab_backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    shutil.copy2(DB_PATH, backup_path)

    # Prune: keep only the 5 most recent backups
    # Timestamp format sorts correctly as plain text
    backups = sorted([
        f for f in os.listdir(BACKUP_DIR)
        if f.startswith("lab_backup_") and f.endswith(".db")
    ])

    while len(backups) > 5:
        oldest = backups.pop(0)
        os.remove(os.path.join(BACKUP_DIR, oldest))


# ---------------------------------------------------------------------------
# Sample CRUD operations (added in later phases)
# ---------------------------------------------------------------------------

def get_next_sample_id():
    """
    Generate the next sequential Sample ID in format SSP-####.
    Always reads from the database — never cached — to prevent duplicates.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Extract the numeric suffix from existing IDs and find the max
    row = cursor.execute(
        "SELECT MAX(CAST(SUBSTR(sample_id, 5) AS INTEGER)) FROM samples"
    ).fetchone()

    conn.close()

    current_max = row[0] if row[0] is not None else 0
    next_num = current_max + 1
    return f"SSP-{next_num:04d}"


def insert_sample(sample_id, name, received_from, date_received, folder_id=None):
    """Insert a new sample with default status 'Under Testing' and deleted=0."""
    # If a folder is assigned at registration, auto-assign the next client report number
    client_report_no = None
    if folder_id is not None:
        client_report_no = get_next_client_report_no(folder_id)

    conn = get_db()
    conn.execute(
        """INSERT INTO samples (sample_id, name, received_from, date_received, status, deleted, folder_id, client_report_no)
           VALUES (?, ?, ?, ?, 'Under Testing', 0, ?, ?)""",
        (sample_id, name, received_from, date_received, folder_id, client_report_no)
    )
    conn.commit()
    conn.close()


def get_all_samples():
    """Get all non-deleted samples, ordered by sample ID descending (newest first)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM samples WHERE deleted = 0 ORDER BY sample_id DESC"
    ).fetchall()
    conn.close()
    return rows


def search_samples(query):
    """
    Search non-deleted samples across multiple columns.
    Matches sample_id, name, received_from, or date_received using LIKE.
    """
    conn = get_db()
    like_query = f"%{query}%"
    rows = conn.execute(
        """SELECT * FROM samples
           WHERE deleted = 0
             AND (sample_id LIKE ? OR name LIKE ? OR received_from LIKE ? OR date_received LIKE ?)
           ORDER BY sample_id DESC""",
        (like_query, like_query, like_query, like_query)
    ).fetchall()
    conn.close()
    return rows


def get_sample(sample_id):
    """Get a single sample by ID (regardless of deleted status, for detail/restore views)."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM samples WHERE sample_id = ?", (sample_id,)
    ).fetchone()
    conn.close()
    return row


def get_all_parameters():
    """Get the full master list of test parameters."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM test_parameters ORDER BY id"
    ).fetchall()
    conn.close()
    return rows


def add_parameter(name, unit):
    """
    Add a new test parameter to the master list.
    Returns the new parameter's ID so it can be immediately used.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO test_parameters (name, unit) VALUES (?, ?)",
        (name, unit)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def get_sample_results(sample_id):
    """
    Get saved test results for a sample, joined with parameter names/units.
    Returns rows with: parameter_id, name, unit, result, method.
    """
    conn = get_db()
    rows = conn.execute(
        """SELECT sr.parameter_id, tp.name, tp.unit, sr.result, sr.method
           FROM sample_results sr
           JOIN test_parameters tp ON sr.parameter_id = tp.id
           WHERE sr.sample_id = ?
           ORDER BY tp.id""",
        (sample_id,)
    ).fetchall()
    conn.close()
    return rows


def save_sample_results(sample_id, results_list):
    """
    Save test results for a sample.
    Deletes existing results first, then inserts the new ones — all in one transaction.
    results_list: list of (parameter_id, result_value, method_value) tuples
    """
    conn = get_db()
    try:
        conn.execute("DELETE FROM sample_results WHERE sample_id = ?", (sample_id,))
        conn.executemany(
            "INSERT INTO sample_results (sample_id, parameter_id, result, method) VALUES (?, ?, ?, ?)",
            [(sample_id, pid, val, method) for pid, val, method in results_list]
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_sample_status(sample_id, new_status):
    """Update a sample's status. Only valid values: 'Under Testing', 'Report Sent'."""
    conn = get_db()
    conn.execute(
        "UPDATE samples SET status = ? WHERE sample_id = ?",
        (new_status, sample_id)
    )
    conn.commit()
    conn.close()


def soft_delete_sample(sample_id):
    """Soft delete: set deleted = 1."""
    conn = get_db()
    conn.execute(
        "UPDATE samples SET deleted = 1 WHERE sample_id = ?", (sample_id,)
    )
    conn.commit()
    conn.close()


def restore_sample(sample_id):
    """Restore a soft-deleted sample: set deleted = 0."""
    conn = get_db()
    conn.execute(
        "UPDATE samples SET deleted = 0 WHERE sample_id = ?", (sample_id,)
    )
    conn.commit()
    conn.close()


def permanent_delete_sample(sample_id):
    """Permanently delete a sample and all its results. Irreversible."""
    conn = get_db()
    try:
        conn.execute("DELETE FROM sample_results WHERE sample_id = ?", (sample_id,))
        conn.execute("DELETE FROM samples WHERE sample_id = ?", (sample_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_deleted_samples():
    """Get all soft-deleted samples."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM samples WHERE deleted = 1 ORDER BY sample_id DESC"
    ).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Folder operations
# ---------------------------------------------------------------------------

def create_folder(name):
    """Create a new folder. Returns the new folder's id."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO folders (name) VALUES (?)", (name,))
    folder_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return folder_id


def get_all_folders():
    """Get all folders, ordered by name."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM folders ORDER BY name").fetchall()
    conn.close()
    return rows


def get_folder(folder_id):
    """Get a single folder by id."""
    conn = get_db()
    row = conn.execute("SELECT * FROM folders WHERE id = ?", (folder_id,)).fetchone()
    conn.close()
    return row


def get_samples_by_folder(folder_id):
    """Get all non-deleted samples assigned to a folder."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM samples WHERE deleted = 0 AND folder_id = ? ORDER BY sample_id DESC",
        (folder_id,)
    ).fetchall()
    conn.close()
    return rows


def get_next_client_report_no(folder_id):
    """
    Get the next sequential client report number for a given folder.
    Counts from all samples ever assigned to this folder (including deleted ones)
    to prevent number reuse.
    """
    conn = get_db()
    row = conn.execute(
        "SELECT MAX(client_report_no) FROM samples WHERE folder_id = ?",
        (folder_id,)
    ).fetchone()
    conn.close()
    current_max = row[0] if row[0] is not None else 0
    return current_max + 1


def update_sample_folder(sample_id, folder_id):
    """
    Update which folder a sample belongs to. Pass None to unassign.
    If assigning to a folder and the sample doesn't already have a client_report_no,
    auto-assign the next number for that folder.
    """
    conn = get_db()

    # Check if this sample already has a client_report_no
    sample = conn.execute(
        "SELECT client_report_no FROM samples WHERE sample_id = ?", (sample_id,)
    ).fetchone()

    client_report_no = sample['client_report_no'] if sample else None

    # Only assign a new number if moving to a folder AND doesn't already have one
    if folder_id is not None and client_report_no is None:
        conn.close()
        client_report_no = get_next_client_report_no(folder_id)
        conn = get_db()
        conn.execute(
            "UPDATE samples SET folder_id = ?, client_report_no = ? WHERE sample_id = ?",
            (folder_id, client_report_no, sample_id)
        )
    else:
        conn.execute(
            "UPDATE samples SET folder_id = ? WHERE sample_id = ?",
            (folder_id, sample_id)
        )

    conn.commit()
    conn.close()


def delete_folder(folder_id):
    """Delete a folder. Unassigns any samples in it first (sets folder_id to NULL)."""
    conn = get_db()
    try:
        conn.execute("UPDATE samples SET folder_id = NULL WHERE folder_id = ?", (folder_id,))
        conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
