"""
Database module for SmartMoneyAlerts.
Uses SQLite for simplicity and portability.
"""

import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional

# Import settings - handle both module import and direct execution
try:
    from config.settings import DATABASE_PATH
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.settings import DATABASE_PATH


def get_connection():
    """Get database connection with row factory."""
    db_path = DATABASE_PATH
    if not os.path.isabs(db_path):
        # Make path relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(project_root, db_path)

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize all database tables."""
    conn = get_connection()
    cursor = conn.cursor()

    # === INSIDER TRADES ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS insider_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Filing info
            accession_number TEXT UNIQUE NOT NULL,
            filing_date TEXT NOT NULL,
            filing_url TEXT,

            -- Company info
            ticker TEXT,
            company_name TEXT,
            company_cik TEXT,

            -- Insider info
            insider_name TEXT,
            insider_cik TEXT,
            insider_role TEXT,
            is_director INTEGER DEFAULT 0,
            is_officer INTEGER DEFAULT 0,
            is_ten_percent_owner INTEGER DEFAULT 0,
            officer_title TEXT,

            -- Transaction info
            transaction_type TEXT,  -- P=Purchase, S=Sale, A=Award, etc.
            transaction_date TEXT,
            shares INTEGER,
            price_per_share REAL,
            total_value REAL,
            shares_owned_after INTEGER,

            -- Our analysis
            virality_score INTEGER DEFAULT 0,
            anomalies TEXT,  -- JSON array of detected anomalies

            -- Posting status
            twitter_posted INTEGER DEFAULT 0,
            twitter_post_id TEXT,
            twitter_posted_at TEXT,
            discord_posted INTEGER DEFAULT 0,
            discord_posted_at TEXT,

            -- Metadata
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # === CONGRESS TRADES (Phase 2) ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS congress_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Source info
            source TEXT,  -- 'house' or 'senate'
            external_id TEXT UNIQUE,

            -- Politician info
            politician_name TEXT,
            politician_party TEXT,
            politician_state TEXT,
            politician_chamber TEXT,

            -- Trade info
            ticker TEXT,
            company_name TEXT,
            transaction_type TEXT,  -- purchase, sale, exchange
            transaction_date TEXT,
            disclosure_date TEXT,
            amount_range TEXT,  -- "$1,001 - $15,000" etc.
            amount_low INTEGER,
            amount_high INTEGER,
            asset_type TEXT,  -- stock, option, etc.

            -- Analysis
            virality_score INTEGER DEFAULT 0,
            days_to_disclose INTEGER,
            suspicious_timing INTEGER DEFAULT 0,

            -- Posting status
            twitter_posted INTEGER DEFAULT 0,
            twitter_post_id TEXT,
            discord_posted INTEGER DEFAULT 0,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # === HEDGE FUND 13F (Phase 3) ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hedge_fund_filings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            accession_number TEXT UNIQUE NOT NULL,
            filing_date TEXT,
            report_date TEXT,  -- Quarter end date

            fund_name TEXT,
            fund_cik TEXT,
            manager_name TEXT,

            -- We'll store position changes as JSON
            new_positions TEXT,      -- JSON
            increased_positions TEXT, -- JSON
            decreased_positions TEXT, -- JSON
            exited_positions TEXT,   -- JSON

            total_value REAL,
            position_count INTEGER,

            virality_score INTEGER DEFAULT 0,
            twitter_posted INTEGER DEFAULT 0,
            discord_posted INTEGER DEFAULT 0,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # === POSTING QUEUE ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posting_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            source_type TEXT,  -- 'insider', 'congress', 'hedge_fund'
            source_id INTEGER,

            platform TEXT,  -- 'twitter', 'discord'
            tier INTEGER,  -- 1, 2, 3, or 4 (roundup)

            message_text TEXT,
            tags TEXT,  -- JSON array

            scheduled_for TEXT,
            posted_at TEXT,
            post_id TEXT,

            status TEXT DEFAULT 'pending',  -- pending, posted, failed
            error_message TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # === DAILY STATS ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,

            insider_trades_scraped INTEGER DEFAULT 0,
            insider_trades_posted INTEGER DEFAULT 0,
            congress_trades_scraped INTEGER DEFAULT 0,
            congress_trades_posted INTEGER DEFAULT 0,
            hedge_fund_filings_scraped INTEGER DEFAULT 0,
            hedge_fund_filings_posted INTEGER DEFAULT 0,

            twitter_posts INTEGER DEFAULT 0,
            twitter_impressions INTEGER DEFAULT 0,
            twitter_engagements INTEGER DEFAULT 0,

            discord_messages INTEGER DEFAULT 0,
            new_discord_members INTEGER DEFAULT 0,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_insider_ticker ON insider_trades(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_insider_date ON insider_trades(filing_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_insider_posted ON insider_trades(twitter_posted)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_insider_virality ON insider_trades(virality_score)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON posting_queue(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_congress_ticker ON congress_trades(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_congress_date ON congress_trades(transaction_date)")

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


# === INSIDER TRADE HELPERS ===

def insert_insider_trade(trade_data: Dict) -> Optional[int]:
    """Insert an insider trade. Returns ID or None if duplicate."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT OR IGNORE INTO insider_trades (
                accession_number, filing_date, filing_url,
                ticker, company_name, company_cik,
                insider_name, insider_cik, insider_role,
                is_director, is_officer, is_ten_percent_owner, officer_title,
                transaction_type, transaction_date, shares, price_per_share,
                total_value, shares_owned_after,
                virality_score, anomalies
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_data.get('accession_number'),
            trade_data.get('filing_date'),
            trade_data.get('filing_url'),
            trade_data.get('ticker'),
            trade_data.get('company_name'),
            trade_data.get('company_cik'),
            trade_data.get('insider_name'),
            trade_data.get('insider_cik'),
            trade_data.get('insider_role'),
            trade_data.get('is_director', 0),
            trade_data.get('is_officer', 0),
            trade_data.get('is_ten_percent_owner', 0),
            trade_data.get('officer_title'),
            trade_data.get('transaction_type'),
            trade_data.get('transaction_date'),
            trade_data.get('shares'),
            trade_data.get('price_per_share'),
            trade_data.get('total_value'),
            trade_data.get('shares_owned_after'),
            trade_data.get('virality_score', 0),
            trade_data.get('anomalies', '[]'),
        ))
        conn.commit()
        return cursor.lastrowid if cursor.rowcount > 0 else None
    except Exception as e:
        print(f"Error inserting trade: {e}")
        return None
    finally:
        conn.close()


def insert_congress_trade(trade_data: Dict) -> Optional[int]:
    """Insert a congressional trade. Returns ID or None if duplicate."""
    conn = get_connection()
    cursor = conn.cursor()

    # Create a unique ID from politician + ticker + date
    external_id = f"{trade_data.get('politician_name', '')}_{trade_data.get('ticker', '')}_{trade_data.get('transaction_date', '')}"

    try:
        cursor.execute("""
            INSERT OR IGNORE INTO congress_trades (
                source, external_id, politician_name, politician_party,
                politician_state, politician_chamber, ticker, company_name,
                transaction_type, transaction_date, disclosure_date,
                amount_range, amount_low, amount_high, asset_type,
                virality_score, days_to_disclose, suspicious_timing
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_data.get('source', 'capitol_trades'),
            external_id,
            trade_data.get('politician_name'),
            trade_data.get('politician_party'),
            trade_data.get('politician_state'),
            trade_data.get('politician_chamber'),
            trade_data.get('ticker'),
            trade_data.get('company_name'),
            trade_data.get('transaction_type'),
            trade_data.get('transaction_date'),
            trade_data.get('disclosure_date'),
            trade_data.get('amount_range'),
            trade_data.get('amount_low', 0),
            trade_data.get('amount_high', 0),
            trade_data.get('asset_type'),
            trade_data.get('virality_score', 0),
            trade_data.get('days_to_disclose', 0),
            trade_data.get('suspicious_timing', 0),
        ))
        conn.commit()
        return cursor.lastrowid if cursor.rowcount > 0 else None
    except Exception as e:
        print(f"Error inserting congress trade: {e}")
        return None
    finally:
        conn.close()


def insert_hedge_fund_filing(filing_data: Dict) -> Optional[int]:
    """Insert a 13F filing. Returns ID or None if duplicate."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT OR IGNORE INTO hedge_fund_filings (
                accession_number, filing_date, report_date,
                fund_name, fund_cik, manager_name,
                new_positions, increased_positions, decreased_positions, exited_positions,
                total_value, position_count, virality_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            filing_data.get('accession_number'),
            filing_data.get('filing_date'),
            filing_data.get('report_date'),
            filing_data.get('fund_name'),
            filing_data.get('fund_cik'),
            filing_data.get('manager_name'),
            json.dumps(filing_data.get('new_positions', [])),
            json.dumps(filing_data.get('increased_positions', [])),
            json.dumps(filing_data.get('decreased_positions', [])),
            json.dumps(filing_data.get('exited_positions', [])),
            filing_data.get('total_value', 0),
            filing_data.get('position_count', 0),
            filing_data.get('virality_score', 0),
        ))
        conn.commit()
        return cursor.lastrowid if cursor.rowcount > 0 else None
    except Exception as e:
        print(f"Error inserting 13F filing: {e}")
        return None
    finally:
        conn.close()


def get_unposted_trades(platform: str = 'twitter', limit: int = 50) -> List[Dict]:
    """Get trades that haven't been posted yet."""
    conn = get_connection()
    cursor = conn.cursor()

    column = f"{platform}_posted"
    cursor.execute(f"""
        SELECT * FROM insider_trades
        WHERE {column} = 0
        AND transaction_type IN ('P', 'S')
        AND total_value >= ?
        ORDER BY virality_score DESC, filing_date DESC
        LIMIT ?
    """, (50000, limit))  # Purchases and sales over $50K

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def mark_trade_posted(trade_id: int, platform: str, post_id: str = None):
    """Mark a trade as posted."""
    conn = get_connection()
    cursor = conn.cursor()

    if platform == 'twitter':
        cursor.execute("""
            UPDATE insider_trades
            SET twitter_posted = 1, twitter_post_id = ?, twitter_posted_at = ?
            WHERE id = ?
        """, (post_id, datetime.now().isoformat(), trade_id))
    elif platform == 'discord':
        cursor.execute("""
            UPDATE insider_trades
            SET discord_posted = 1, discord_posted_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), trade_id))

    conn.commit()
    conn.close()


def get_recent_trades_for_ticker(ticker: str, days: int = 7) -> List[Dict]:
    """Get recent trades for a ticker (for cluster detection)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM insider_trades
        WHERE ticker = ?
        AND transaction_type = 'P'
        AND filing_date >= date('now', ?)
        ORDER BY filing_date DESC
    """, (ticker, f'-{days} days'))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_insider_history(insider_cik: str, ticker: str = None) -> List[Dict]:
    """Get historical trades for an insider."""
    conn = get_connection()
    cursor = conn.cursor()

    if ticker:
        cursor.execute("""
            SELECT * FROM insider_trades
            WHERE insider_cik = ? AND ticker = ?
            ORDER BY filing_date DESC
            LIMIT 100
        """, (insider_cik, ticker))
    else:
        cursor.execute("""
            SELECT * FROM insider_trades
            WHERE insider_cik = ?
            ORDER BY filing_date DESC
            LIMIT 100
        """, (insider_cik,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_trade_by_id(trade_id: int) -> Optional[Dict]:
    """Get a single trade by ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM insider_trades WHERE id = ?", (trade_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_today_trades() -> List[Dict]:
    """Get all trades filed today."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM insider_trades
        WHERE filing_date = date('now')
        AND transaction_type = 'P'
        ORDER BY total_value DESC
    """)

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_trade_score(trade_id: int, score: int, anomalies: str = None):
    """Update virality score and anomalies for a trade."""
    conn = get_connection()
    cursor = conn.cursor()

    if anomalies:
        cursor.execute("""
            UPDATE insider_trades
            SET virality_score = ?, anomalies = ?, updated_at = ?
            WHERE id = ?
        """, (score, anomalies, datetime.now().isoformat(), trade_id))
    else:
        cursor.execute("""
            UPDATE insider_trades
            SET virality_score = ?, updated_at = ?
            WHERE id = ?
        """, (score, datetime.now().isoformat(), trade_id))

    conn.commit()
    conn.close()


def get_stats_summary() -> Dict:
    """Get summary statistics for the database."""
    conn = get_connection()
    cursor = conn.cursor()

    stats = {}

    # Total trades
    cursor.execute("SELECT COUNT(*) FROM insider_trades")
    stats['total_trades'] = cursor.fetchone()[0]

    # Purchases only
    cursor.execute("SELECT COUNT(*) FROM insider_trades WHERE transaction_type = 'P'")
    stats['total_purchases'] = cursor.fetchone()[0]

    # Posted to Twitter
    cursor.execute("SELECT COUNT(*) FROM insider_trades WHERE twitter_posted = 1")
    stats['twitter_posted'] = cursor.fetchone()[0]

    # Posted to Discord
    cursor.execute("SELECT COUNT(*) FROM insider_trades WHERE discord_posted = 1")
    stats['discord_posted'] = cursor.fetchone()[0]

    # Today's trades
    cursor.execute("SELECT COUNT(*) FROM insider_trades WHERE filing_date = date('now')")
    stats['today_trades'] = cursor.fetchone()[0]

    # Average virality score
    cursor.execute("SELECT AVG(virality_score) FROM insider_trades WHERE virality_score > 0")
    result = cursor.fetchone()[0]
    stats['avg_virality_score'] = round(result, 1) if result else 0

    conn.close()
    return stats


if __name__ == "__main__":
    init_db()
    print("\nDatabase stats:")
    stats = get_stats_summary()
    for key, value in stats.items():
        print(f"  {key}: {value}")
