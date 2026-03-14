"""
Event Database: Historical events with asset price reactions.

This implements Section 8 of PULSE - building a database of historical events
and their correlation with asset movements.

Event Types:
- military_attack: Military action in Middle East (Kharg Island, Strait of Hormuz, etc)
- fed_decision: Federal Reserve interest rate decisions
- trade_sanction: Trade sanctions between major economies
- opec_cut: OPEC production cuts or increases
- crypto_regulation: Cryptocurrency regulatory announcements

Assets Tracked:
- CL=F: Crude Oil (WTI)
- GC=F: Gold
- ^GSPC: S&P 500
- BTC-USD: Bitcoin
- MXN=X: USD/MXN (inverted for MXN strength)
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import yfinance as yf

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'events.db')

EVENT_TYPES = [
    'military_attack',
    'fed_decision', 
    'trade_sanction',
    'opec_cut',
    'crypto_regulation',
]

TRACKED_ASSETS = {
    'oil': 'CL=F',
    'gold': 'GC=F',
    'sp500': '^GSPC',
    'btc': 'BTC-USD',
    'usdmxn': 'MXN=X',
}

TIME_WINDOWS = ['1h', '4h', '24h']


def init_db():
    """Initialize the events database schema."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Events table
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            event_date DATE NOT NULL,
            event_time TIME,
            title TEXT NOT NULL,
            description TEXT,
            source TEXT,
            source_url TEXT,
            severity INTEGER DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(event_type, event_date, title)
        )
    """)
    
    # Price reactions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS price_reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            asset TEXT NOT NULL,
            price_before REAL,
            price_1h REAL,
            price_4h REAL,
            price_24h REAL,
            change_1h_pct REAL,
            change_4h_pct REAL,
            change_24h_pct REAL,
            direction_1h TEXT,
            direction_4h TEXT,
            direction_24h TEXT,
            FOREIGN KEY (event_id) REFERENCES events(id),
            UNIQUE(event_id, asset)
        )
    """)
    
    # Statistics table (pre-calculated)
    c.execute("""
        CREATE TABLE IF NOT EXISTS event_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            asset TEXT NOT NULL,
            time_window TEXT NOT NULL,
            sample_size INTEGER,
            median_change REAL,
            percentile_25 REAL,
            percentile_75 REAL,
            direction_accuracy REAL,
            avg_positive REAL,
            avg_negative REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(event_type, asset, time_window)
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"Events database initialized at {DB_PATH}")


def add_event(event_type: str, event_date: str, title: str, 
              description: str = None, source: str = None, 
              source_url: str = None, severity: int = 5,
              event_time: str = None) -> int:
    """
    Add a new event to the database.
    
    Args:
        event_type: One of EVENT_TYPES
        event_date: Date in YYYY-MM-DD format
        title: Short event title
        description: Longer description
        source: News source (Reuters, AP, etc)
        source_url: URL to the source article
        severity: 1-10 scale of impact (10 = highest)
        event_time: Optional time in HH:MM format
    
    Returns:
        Event ID
    """
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Invalid event_type. Must be one of: {EVENT_TYPES}")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        c.execute("""
            INSERT INTO events (event_type, event_date, event_time, title, description, source, source_url, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (event_type, event_date, event_time, title, description, source, source_url, severity))
        
        event_id = c.lastrowid
        conn.commit()
        print(f"Added event #{event_id}: {title}")
        return event_id
        
    except sqlite3.IntegrityError:
        c.execute("SELECT id FROM events WHERE event_type=? AND event_date=? AND title=?",
                  (event_type, event_date, title))
        row = c.fetchone()
        print(f"Event already exists (id={row[0]})")
        return row[0]
    finally:
        conn.close()


def fetch_price_at_time(ticker: str, target_dt: datetime) -> Optional[float]:
    """
    Fetch the price of an asset at a specific datetime.
    Uses yfinance with 1-hour intervals for precision.
    """
    try:
        # Fetch a range around the target time
        start = target_dt - timedelta(hours=2)
        end = target_dt + timedelta(hours=2)
        
        data = yf.download(ticker, start=start, end=end, interval='1h', progress=False)
        if data.empty:
            # Fallback to daily data
            data = yf.download(ticker, start=start, end=end + timedelta(days=1), interval='1d', progress=False)
        
        if data.empty:
            return None
        
        # Find the closest price to target time
        data.index = data.index.tz_localize(None) if data.index.tz else data.index
        closest_idx = data.index.get_indexer([target_dt], method='nearest')[0]
        
        if closest_idx >= 0 and closest_idx < len(data):
            return float(data['Close'].iloc[closest_idx])
        return None
        
    except Exception as e:
        print(f"Error fetching price for {ticker}: {e}")
        return None


def calculate_price_reactions(event_id: int, force: bool = False):
    """
    Calculate price reactions for all tracked assets after an event.
    
    Args:
        event_id: The event ID to process
        force: If True, recalculate even if data exists
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get event details
    c.execute("SELECT event_date, event_time FROM events WHERE id=?", (event_id,))
    row = c.fetchone()
    if not row:
        print(f"Event {event_id} not found")
        conn.close()
        return
    
    event_date, event_time = row
    
    # Parse datetime
    if event_time:
        event_dt = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
    else:
        # Default to market open (9:30 AM ET)
        event_dt = datetime.strptime(f"{event_date} 09:30", "%Y-%m-%d %H:%M")
    
    # Check if already calculated
    if not force:
        c.execute("SELECT COUNT(*) FROM price_reactions WHERE event_id=?", (event_id,))
        if c.fetchone()[0] > 0:
            print(f"Price reactions already exist for event {event_id}")
            conn.close()
            return
    
    print(f"Calculating price reactions for event {event_id} on {event_date}...")
    
    for asset_name, ticker in TRACKED_ASSETS.items():
        try:
            # Fetch prices at different time windows
            price_before = fetch_price_at_time(ticker, event_dt - timedelta(hours=1))
            price_1h = fetch_price_at_time(ticker, event_dt + timedelta(hours=1))
            price_4h = fetch_price_at_time(ticker, event_dt + timedelta(hours=4))
            price_24h = fetch_price_at_time(ticker, event_dt + timedelta(hours=24))
            
            if price_before is None:
                print(f"  {asset_name}: No data available")
                continue
            
            # Calculate changes
            change_1h = ((price_1h - price_before) / price_before * 100) if price_1h else None
            change_4h = ((price_4h - price_before) / price_before * 100) if price_4h else None
            change_24h = ((price_24h - price_before) / price_before * 100) if price_24h else None
            
            # Determine direction
            dir_1h = 'up' if change_1h and change_1h > 0 else ('down' if change_1h and change_1h < 0 else 'flat')
            dir_4h = 'up' if change_4h and change_4h > 0 else ('down' if change_4h and change_4h < 0 else 'flat')
            dir_24h = 'up' if change_24h and change_24h > 0 else ('down' if change_24h and change_24h < 0 else 'flat')
            
            # Insert or update
            c.execute("""
                INSERT OR REPLACE INTO price_reactions 
                (event_id, asset, price_before, price_1h, price_4h, price_24h,
                 change_1h_pct, change_4h_pct, change_24h_pct,
                 direction_1h, direction_4h, direction_24h)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (event_id, asset_name, price_before, price_1h, price_4h, price_24h,
                  change_1h, change_4h, change_24h, dir_1h, dir_4h, dir_24h))
            
            print(f"  {asset_name}: 1h={change_1h:+.2f}% 4h={change_4h:+.2f}% 24h={change_24h:+.2f}%" if change_1h else f"  {asset_name}: partial data")
            
        except Exception as e:
            print(f"  {asset_name}: Error - {e}")
    
    conn.commit()
    conn.close()


def calculate_statistics():
    """
    Calculate aggregate statistics for each event_type + asset combination.
    This is what Sentinel will use for correlation predictions.
    """
    import statistics
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("Calculating event statistics...")
    
    for event_type in EVENT_TYPES:
        for asset_name in TRACKED_ASSETS.keys():
            for window in TIME_WINDOWS:
                col = f"change_{window}_pct"
                dir_col = f"direction_{window}"
                
                c.execute(f"""
                    SELECT pr.{col}, pr.{dir_col}
                    FROM price_reactions pr
                    JOIN events e ON e.id = pr.event_id
                    WHERE e.event_type = ? AND pr.asset = ? AND pr.{col} IS NOT NULL
                """, (event_type, asset_name))
                
                rows = c.fetchall()
                if len(rows) < 3:
                    continue
                
                changes = [r[0] for r in rows]
                directions = [r[1] for r in rows]
                
                # Calculate statistics
                median_change = statistics.median(changes)
                sorted_changes = sorted(changes)
                n = len(sorted_changes)
                p25 = sorted_changes[int(n * 0.25)]
                p75 = sorted_changes[int(n * 0.75)]
                
                # Direction accuracy (how often does it move in the expected direction)
                # For now, use the most common direction as "expected"
                up_count = sum(1 for d in directions if d == 'up')
                down_count = sum(1 for d in directions if d == 'down')
                most_common = 'up' if up_count >= down_count else 'down'
                accuracy = max(up_count, down_count) / len(directions) * 100
                
                # Average positive and negative moves
                positives = [c for c in changes if c > 0]
                negatives = [c for c in changes if c < 0]
                avg_pos = statistics.mean(positives) if positives else 0
                avg_neg = statistics.mean(negatives) if negatives else 0
                
                c.execute("""
                    INSERT OR REPLACE INTO event_statistics
                    (event_type, asset, time_window, sample_size, median_change,
                     percentile_25, percentile_75, direction_accuracy, avg_positive, avg_negative, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (event_type, asset_name, window, len(rows), median_change,
                      p25, p75, accuracy, avg_pos, avg_neg, datetime.now().isoformat()))
                
                print(f"  {event_type}/{asset_name}/{window}: n={len(rows)}, median={median_change:+.2f}%, accuracy={accuracy:.0f}%")
    
    conn.commit()
    conn.close()
    print("Statistics calculation complete.")


def get_correlation(event_type: str, asset: str, time_window: str = '24h') -> Optional[Dict]:
    """
    Get the historical correlation for an event type and asset.
    
    Returns:
        Dict with median, percentiles, accuracy, and sample size
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT median_change, percentile_25, percentile_75, direction_accuracy, sample_size
        FROM event_statistics
        WHERE event_type = ? AND asset = ? AND time_window = ?
    """, (event_type, asset, time_window))
    
    row = c.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return {
        'median': row[0],
        'p25': row[1],
        'p75': row[2],
        'accuracy': row[3],
        'sample_size': row[4],
    }


def get_all_events(event_type: str = None, limit: int = 100) -> List[Dict]:
    """Get events from the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if event_type:
        c.execute("""
            SELECT id, event_type, event_date, title, description, source, severity
            FROM events WHERE event_type = ? ORDER BY event_date DESC LIMIT ?
        """, (event_type, limit))
    else:
        c.execute("""
            SELECT id, event_type, event_date, title, description, source, severity
            FROM events ORDER BY event_date DESC LIMIT ?
        """, (limit,))
    
    rows = c.fetchall()
    conn.close()
    
    return [{
        'id': r[0], 'event_type': r[1], 'event_date': r[2], 'title': r[3],
        'description': r[4], 'source': r[5], 'severity': r[6]
    } for r in rows]


def print_statistics_report():
    """Print a summary of the event database statistics."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM events")
    total_events = c.fetchone()[0]
    
    c.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type")
    type_counts = dict(c.fetchall())
    
    print("\n" + "=" * 60)
    print("EVENT DATABASE STATISTICS")
    print("=" * 60)
    print(f"\nTotal events: {total_events}")
    print("\nBy type:")
    for et in EVENT_TYPES:
        count = type_counts.get(et, 0)
        status = "OK" if count >= 20 else "NEEDS MORE"
        print(f"  {et}: {count} [{status}]")
    
    print("\n" + "-" * 60)
    print("CORRELATIONS (24h window, min 5 samples)")
    print("-" * 60)
    
    c.execute("""
        SELECT event_type, asset, median_change, direction_accuracy, sample_size
        FROM event_statistics
        WHERE time_window = '24h' AND sample_size >= 5
        ORDER BY event_type, ABS(median_change) DESC
    """)
    
    current_type = None
    for row in c.fetchall():
        if row[0] != current_type:
            current_type = row[0]
            print(f"\n{current_type}:")
        
        direction = "UP" if row[2] > 0 else "DOWN"
        confidence = "HIGH" if row[3] >= 65 else "MEDIUM" if row[3] >= 50 else "LOW"
        print(f"  {row[1]}: {row[2]:+.2f}% ({direction}) | accuracy: {row[3]:.0f}% [{confidence}] | n={row[4]}")
    
    conn.close()
    print("\n" + "=" * 60)


if __name__ == '__main__':
    init_db()
    print_statistics_report()
