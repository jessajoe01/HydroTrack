import sqlite3
import os

DB_PATH = os.path.join('instance', 'smartwater.db')


def get_columns(cursor, table_name):
    """Return a list of existing column names in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def get_tables(cursor):
    """Return a list of existing table names in the database."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cursor.fetchall()]


def add_column(cursor, table, column, col_type, default=None):
    """Add a column only if it doesn't already exist."""
    existing = get_columns(cursor, table)
    if column not in existing:
        if default is not None:
            cursor.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}"
            )
        else:
            cursor.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
            )
        print(f"  ✅ Added column  [{table}].{column}")
    else:
        print(f"  ⏭️  Already exists [{table}].{column} — skipped")


def migrate():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {DB_PATH}")
        print("   Make sure you run this from your project root (same folder as app.py)")
        return

    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()

    existing_tables = get_tables(c)
    print(f"\n📂 Database: {DB_PATH}")
    print(f"📋 Existing tables: {', '.join(existing_tables)}\n")


    # ═════════════════════════════════════════════════════════
    # 1. USERS TABLE — new columns
    # ═════════════════════════════════════════════════════════
    print("── users ────────────────────────────────────────────")
    add_column(c, 'users', 'sump_capacity', 'REAL',    'NULL')
    add_column(c, 'users', 'house_type',    'TEXT',    "NULL")
    add_column(c, 'users', 'updated_on',    'DATETIME','NULL')

    # Set default sump_capacity for existing users who have NULL
    c.execute("UPDATE users SET sump_capacity = 6000.0 WHERE sump_capacity IS NULL")
    rows = c.rowcount
    if rows:
        print(f"  ✅ Set sump_capacity=6000 for {rows} existing user(s)")


    # ═════════════════════════════════════════════════════════
    # 2. TANKER_LOGS TABLE — new columns
    # ═════════════════════════════════════════════════════════
    print("── tanker_logs ──────────────────────────────────────")
    # status must have a default so existing rows are not NULL
    add_column(c, 'tanker_logs', 'status',      'TEXT', "'Pending'")
    add_column(c, 'tanker_logs', 'supplier_id', 'INTEGER', 'NULL')


    # ═════════════════════════════════════════════════════════
    # 3. DAILY_USAGE TABLE — new columns
    # ═════════════════════════════════════════════════════════
    print("── daily_usage ──────────────────────────────────────")
    add_column(c, 'daily_usage', 'guests_count', 'INTEGER', '0')
    add_column(c, 'daily_usage', 'notes',        'TEXT',    'NULL')
    add_column(c, 'daily_usage', 'created_on',   'DATETIME','NULL')


    # ═════════════════════════════════════════════════════════
    # 4. ALERTS TABLE — new columns
    # ═════════════════════════════════════════════════════════
    print("── alerts ───────────────────────────────────────────")
    add_column(c, 'alerts', 'title',            'TEXT',  'NULL')
    add_column(c, 'alerts', 'severity',         'TEXT',  "'medium'")
    add_column(c, 'alerts', 'confidence_level', 'REAL',  '0.5')


    # ═════════════════════════════════════════════════════════
    # 5. SUPPLIERS TABLE — new columns
    # ═════════════════════════════════════════════════════════
    print("── suppliers ────────────────────────────────────────")
    add_column(c, 'suppliers', 'avg_delivery_hours', 'INTEGER', '24')
    add_column(c, 'suppliers', 'rating',             'REAL',    '3.0')
    add_column(c, 'suppliers', 'added_on',           'DATETIME','NULL')

    # Backfill avg_delivery_hours from avg_delivery_days if present
    supplier_cols = get_columns(c, 'suppliers')
    if 'avg_delivery_days' in supplier_cols:
        c.execute("""
            UPDATE suppliers
            SET avg_delivery_hours = avg_delivery_days * 24
            WHERE avg_delivery_hours = 24 AND avg_delivery_days IS NOT NULL
        """)
        print("  ✅ Backfilled avg_delivery_hours from avg_delivery_days")


    # ═════════════════════════════════════════════════════════
    # 6. SPECIAL_REQUESTS TABLE — new columns
    # ═════════════════════════════════════════════════════════
    print("── special_requests ─────────────────────────────────")
    add_column(c, 'special_requests', 'expected_guests',   'INTEGER', '0')
    add_column(c, 'special_requests', 'supplier_notified', 'INTEGER', '0')


    # ═════════════════════════════════════════════════════════
    # 7. NEW TABLE — vacation_modes
    # ═════════════════════════════════════════════════════════
    print("── vacation_modes (new table) ───────────────────────")
    if 'vacation_modes' not in existing_tables:
        c.execute('''
            CREATE TABLE vacation_modes (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id           INTEGER NOT NULL REFERENCES users(id),
                start_date        DATE    NOT NULL,
                end_date          DATE    NOT NULL,
                occupancy_percent REAL    DEFAULT 0,
                is_active         INTEGER DEFAULT 1,
                created_on        DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("  ✅ Created vacation_modes table")
    else:
        print("  ⏭️  vacation_modes already exists — skipped")


    # ═════════════════════════════════════════════════════════
    # 8. NEW TABLE — prediction_history
    # ═════════════════════════════════════════════════════════
    print("── prediction_history (new table) ───────────────────")
    if 'prediction_history' not in existing_tables:
        c.execute('''
            CREATE TABLE prediction_history (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id                  INTEGER NOT NULL REFERENCES users(id),
                predicted_daily_usage    REAL    NOT NULL,
                predicted_days_remaining REAL,
                confidence_score         REAL    DEFAULT 0.5,
                model_used               TEXT    DEFAULT 'TankerCycleLR',
                tanker_capacity          REAL,
                data_points_used         INTEGER DEFAULT 0,
                actual_daily_usage       REAL,
                actual_days_lasted       REAL,
                error_percent            REAL,
                user_confirmed           INTEGER DEFAULT 0,
                prediction_date          DATE    NOT NULL DEFAULT (date('now')),
                created_on               DATETIME DEFAULT CURRENT_TIMESTAMP,
                confirmed_on             DATETIME
            )
        ''')
        print("  ✅ Created prediction_history table")
    else:
        # Table already exists — check if it has the right columns and add any missing ones
        print("  ℹ️  prediction_history already exists — checking columns...")
        add_column(c, 'prediction_history', 'model_used',           'TEXT',    "'TankerCycleLR'")
        add_column(c, 'prediction_history', 'data_points_used',     'INTEGER', '0')
        add_column(c, 'prediction_history', 'user_confirmed',       'INTEGER', '0')
        add_column(c, 'prediction_history', 'tanker_capacity',      'REAL',    'NULL')
        add_column(c, 'prediction_history', 'confirmed_on',         'DATETIME','NULL')
        add_column(c, 'prediction_history', 'prediction_date',      'DATE',    'NULL')
        # Backfill prediction_date for existing rows that got NULL
        c.execute("UPDATE prediction_history SET prediction_date = date('now') WHERE prediction_date IS NULL")
        if c.rowcount:
            print(f"  ✅ Backfilled prediction_date for {c.rowcount} existing row(s)")
        add_column(c, 'prediction_history', 'actual_daily_usage',   'REAL',    'NULL')
        add_column(c, 'prediction_history', 'actual_days_lasted',   'REAL',    'NULL')
        add_column(c, 'prediction_history', 'error_percent',        'REAL',    'NULL')


    # ═════════════════════════════════════════════════════════
    # 9. NEW TABLE — user_confirmations
    # ═════════════════════════════════════════════════════════
    print("── user_confirmations (new table) ───────────────────")
    if 'user_confirmations' not in existing_tables:
        c.execute('''
            CREATE TABLE user_confirmations (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id                  INTEGER NOT NULL REFERENCES users(id),
                alert_id                 INTEGER REFERENCES alerts(id),
                tanker_delivery_id       INTEGER REFERENCES tanker_logs(id),
                estimated_days_remaining REAL,
                actual_days_lasted       REAL,
                user_note                TEXT,
                used_for_training        INTEGER DEFAULT 0,
                confirmed_on             DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("  ✅ Created user_confirmations table")
    else:
        print("  ⏭️  user_confirmations already exists — skipped")


    # ═════════════════════════════════════════════════════════
    # COMMIT AND CLOSE
    # ═════════════════════════════════════════════════════════
    conn.commit()
    conn.close()

    print("\n" + "═" * 55)
    print("✅ Migration complete.")
    print("   Your existing data is fully intact.")
    print("   You can now replace models.py and restart the app.")
    print("═" * 55 + "\n")


if __name__ == '__main__':
    migrate()