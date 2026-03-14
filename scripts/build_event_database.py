"""
Build Event Database - Section 8 of PULSE

This script populates the events database with historical events (2020-2026).
Each event is documented with its date, description, source, and severity.

Target: 20+ events per category, 100+ total events.

Usage:
    python scripts/build_event_database.py --populate   # Add sample events
    python scripts/build_event_database.py --calculate  # Calculate price reactions
    python scripts/build_event_database.py --stats      # Show statistics
    python scripts/build_event_database.py --all        # Do everything
"""

import sys
import os
import argparse
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_sources.event_database import (
    init_db, add_event, calculate_price_reactions, 
    calculate_statistics, print_statistics_report, get_all_events
)


# ============================================
# HISTORICAL EVENTS DATABASE
# ============================================
# Format: (event_type, date, title, description, source, severity)

HISTORICAL_EVENTS = [
    # ==========================================
    # MILITARY ATTACKS (Middle East focus)
    # ==========================================
    ('military_attack', '2020-01-03', 'US kills Iranian General Soleimani',
     'US drone strike in Baghdad kills Qasem Soleimani, head of Iran Quds Force',
     'Reuters', 10),
    
    ('military_attack', '2020-01-08', 'Iran retaliates with missile attack on US bases',
     'Iran launches missile strikes on Al-Asad and Erbil bases in Iraq',
     'AP', 9),
    
    ('military_attack', '2021-02-25', 'US airstrikes on Iranian-backed militias in Syria',
     'Biden administration orders airstrikes on facilities used by Iranian-backed militias',
     'Reuters', 6),
    
    ('military_attack', '2022-02-24', 'Russia invades Ukraine',
     'Russia launches full-scale military invasion of Ukraine',
     'BBC', 10),
    
    ('military_attack', '2022-09-26', 'Nord Stream pipeline explosions',
     'Explosions damage Nord Stream 1 and 2 pipelines in Baltic Sea',
     'Reuters', 8),
    
    ('military_attack', '2023-10-07', 'Hamas attacks Israel',
     'Hamas launches surprise attack on Israel from Gaza, thousands killed',
     'AP', 10),
    
    ('military_attack', '2023-10-27', 'Israel ground invasion of Gaza begins',
     'Israeli forces begin ground operations in northern Gaza',
     'Reuters', 8),
    
    ('military_attack', '2023-11-19', 'Houthis seize cargo ship in Red Sea',
     'Yemen Houthi rebels seize Galaxy Leader cargo ship in Red Sea',
     'Al Jazeera', 7),
    
    ('military_attack', '2024-01-12', 'US-UK strikes on Houthi targets in Yemen',
     'Coalition launches airstrikes on Houthi military targets in Yemen',
     'BBC', 8),
    
    ('military_attack', '2024-04-13', 'Iran launches drones and missiles at Israel',
     'Iran fires over 300 drones and missiles at Israel in retaliation for Damascus strike',
     'Reuters', 9),
    
    ('military_attack', '2024-07-31', 'Israel kills Hamas leader Haniyeh in Tehran',
     'Ismail Haniyeh killed in Tehran, raising fears of regional escalation',
     'Al Jazeera', 9),
    
    ('military_attack', '2025-01-15', 'Houthis attack oil tanker near Bab el-Mandeb',
     'Houthi drone strikes oil tanker, disrupting Red Sea shipping',
     'Reuters', 7),
    
    # ==========================================
    # FED DECISIONS
    # ==========================================
    ('fed_decision', '2020-03-03', 'Fed emergency rate cut - 50bp',
     'Federal Reserve cuts rates by 50bp in emergency meeting due to COVID-19',
     'Federal Reserve', 9),
    
    ('fed_decision', '2020-03-15', 'Fed cuts to zero, launches QE',
     'Fed cuts rates to 0-0.25% and announces unlimited QE program',
     'Federal Reserve', 10),
    
    ('fed_decision', '2021-11-03', 'Fed announces tapering',
     'FOMC announces tapering of asset purchases starting November 2021',
     'Federal Reserve', 7),
    
    ('fed_decision', '2022-03-16', 'Fed begins rate hikes - 25bp',
     'First rate hike since 2018, Fed raises by 25bp to combat inflation',
     'Federal Reserve', 8),
    
    ('fed_decision', '2022-05-04', 'Fed raises 50bp',
     'Largest rate hike since 2000, Fed signals aggressive tightening',
     'Federal Reserve', 8),
    
    ('fed_decision', '2022-06-15', 'Fed raises 75bp',
     'Largest hike since 1994, Fed raises to 1.50-1.75% range',
     'Federal Reserve', 9),
    
    ('fed_decision', '2022-09-21', 'Fed raises 75bp third time',
     'Third consecutive 75bp hike, signals more increases coming',
     'Federal Reserve', 8),
    
    ('fed_decision', '2022-11-02', 'Fed raises 75bp fourth time',
     'Fourth 75bp hike, rates now at 3.75-4.00%',
     'Federal Reserve', 8),
    
    ('fed_decision', '2023-02-01', 'Fed raises 25bp, signals slower pace',
     'Fed slows to 25bp hike, signals data-dependent approach',
     'Federal Reserve', 6),
    
    ('fed_decision', '2023-05-03', 'Fed raises 25bp, hints at pause',
     'May hike to 5.00-5.25%, Fed signals potential pause',
     'Federal Reserve', 7),
    
    ('fed_decision', '2023-07-26', 'Fed raises to 5.25-5.50%',
     'Final hike of cycle, rates at 22-year high',
     'Federal Reserve', 7),
    
    ('fed_decision', '2024-09-18', 'Fed cuts 50bp - pivot begins',
     'First cut since 2020, Fed pivots with 50bp reduction',
     'Federal Reserve', 9),
    
    ('fed_decision', '2024-11-07', 'Fed cuts 25bp',
     'Continued easing with 25bp cut to 4.50-4.75%',
     'Federal Reserve', 6),
    
    ('fed_decision', '2024-12-18', 'Fed cuts 25bp, signals slower pace',
     'December cut with hawkish tone, signals fewer cuts in 2025',
     'Federal Reserve', 7),
    
    # ==========================================
    # TRADE SANCTIONS
    # ==========================================
    ('trade_sanction', '2020-05-15', 'US bans Huawei chip supplies',
     'Commerce Department bans semiconductor sales to Huawei',
     'Reuters', 8),
    
    ('trade_sanction', '2021-06-03', 'Biden expands China investment ban',
     'Executive order expands list of Chinese companies banned for US investment',
     'White House', 7),
    
    ('trade_sanction', '2022-02-26', 'SWIFT ban on Russian banks',
     'US and EU remove major Russian banks from SWIFT system',
     'Reuters', 10),
    
    ('trade_sanction', '2022-03-08', 'US bans Russian oil imports',
     'Biden announces ban on Russian oil, gas, and coal imports',
     'White House', 9),
    
    ('trade_sanction', '2022-04-06', 'US sanctions on Russia expanded',
     'New sanctions on Sberbank, major oligarchs, and Putin family',
     'Treasury Dept', 8),
    
    ('trade_sanction', '2022-10-07', 'US chip export controls on China',
     'Sweeping restrictions on semiconductor exports to China',
     'Commerce Dept', 9),
    
    ('trade_sanction', '2023-01-27', 'US-NL-Japan chip equipment pact',
     'Allies agree to restrict advanced chip equipment exports to China',
     'Reuters', 8),
    
    ('trade_sanction', '2023-08-09', 'Biden restricts China tech investment',
     'Executive order limits US investment in Chinese AI, quantum, semiconductors',
     'White House', 7),
    
    ('trade_sanction', '2024-05-14', 'US tariffs on Chinese EVs, batteries',
     '100% tariff on Chinese EVs, higher tariffs on batteries and solar',
     'White House', 8),
    
    ('trade_sanction', '2024-12-02', 'US expands China chip restrictions',
     'New export controls target 140 Chinese chip companies',
     'Commerce Dept', 8),
    
    # ==========================================
    # OPEC PRODUCTION DECISIONS
    # ==========================================
    ('opec_cut', '2020-04-12', 'OPEC+ historic 9.7M bpd cut',
     'Largest production cut in history amid COVID demand collapse',
     'OPEC', 10),
    
    ('opec_cut', '2021-04-01', 'OPEC+ extends cuts, cautious recovery',
     'Group extends most cuts through June despite demand recovery',
     'OPEC', 6),
    
    ('opec_cut', '2021-07-18', 'OPEC+ agrees to increase production',
     'Deal to add 400K bpd monthly starting August 2021',
     'OPEC', 7),
    
    ('opec_cut', '2022-10-05', 'OPEC+ cuts 2M bpd',
     'Surprise deep cut despite US pressure, largest since 2020',
     'OPEC', 9),
    
    ('opec_cut', '2023-04-02', 'OPEC+ surprise 1.16M bpd cut',
     'Unscheduled voluntary cuts by Saudi, Iraq, UAE, Kuwait',
     'OPEC', 8),
    
    ('opec_cut', '2023-06-04', 'Saudi Arabia 1M bpd voluntary cut',
     'Saudi announces unilateral 1M bpd cut for July',
     'Reuters', 8),
    
    ('opec_cut', '2023-11-30', 'OPEC+ extends voluntary cuts',
     'Group extends 2.2M bpd voluntary cuts into Q1 2024',
     'OPEC', 7),
    
    ('opec_cut', '2024-06-02', 'OPEC+ plans gradual output increase',
     'Group signals unwinding cuts starting October 2024',
     'OPEC', 7),
    
    ('opec_cut', '2024-09-05', 'OPEC+ delays output increase',
     'Group postpones planned production increase by 2 months',
     'OPEC', 6),
    
    ('opec_cut', '2024-12-05', 'OPEC+ extends cuts through 2025',
     'Production cuts extended, unwinding delayed to April 2025',
     'OPEC', 7),
    
    # ==========================================
    # CRYPTO REGULATION
    # ==========================================
    ('crypto_regulation', '2021-05-18', 'China bans crypto transactions',
     'China financial institutions banned from crypto services',
     'PBOC', 9),
    
    ('crypto_regulation', '2021-09-24', 'China declares all crypto illegal',
     'PBOC declares all cryptocurrency transactions illegal',
     'PBOC', 10),
    
    ('crypto_regulation', '2022-02-09', 'US releases crypto executive order',
     'Biden signs executive order for comprehensive crypto regulation',
     'White House', 7),
    
    ('crypto_regulation', '2022-11-11', 'FTX files bankruptcy',
     'FTX exchange collapses, files for Chapter 11 bankruptcy',
     'Reuters', 10),
    
    ('crypto_regulation', '2023-02-09', 'SEC sues Kraken for staking',
     'Kraken settles with SEC for $30M, ends US staking program',
     'SEC', 7),
    
    ('crypto_regulation', '2023-06-05', 'SEC sues Binance and Coinbase',
     'SEC files lawsuits against two largest exchanges',
     'SEC', 9),
    
    ('crypto_regulation', '2024-01-10', 'SEC approves Bitcoin ETFs',
     'Historic approval of 11 spot Bitcoin ETFs in US',
     'SEC', 10),
    
    ('crypto_regulation', '2024-05-23', 'SEC approves Ethereum ETFs',
     'Surprise approval of spot Ethereum ETF applications',
     'SEC', 8),
    
    ('crypto_regulation', '2024-11-06', 'Trump wins, pro-crypto administration',
     'Trump election victory signals pro-crypto regulatory shift',
     'AP', 9),
    
    ('crypto_regulation', '2025-01-20', 'SEC chair Gensler steps down',
     'Pro-enforcement SEC chair replaced by crypto-friendly nominee',
     'Reuters', 8),
]


def populate_events():
    """Add all historical events to the database."""
    print("=" * 60)
    print("POPULATING EVENT DATABASE")
    print("=" * 60)
    
    init_db()
    
    added = 0
    skipped = 0
    
    for event in HISTORICAL_EVENTS:
        event_type, date, title, desc, source, severity = event
        try:
            result = add_event(
                event_type=event_type,
                event_date=date,
                title=title,
                description=desc,
                source=source,
                severity=severity
            )
            if result:
                added += 1
        except Exception as e:
            print(f"Error adding event: {e}")
            skipped += 1
    
    print(f"\nAdded: {added}, Skipped: {skipped}")


def calculate_all_reactions():
    """Calculate price reactions for all events."""
    print("=" * 60)
    print("CALCULATING PRICE REACTIONS")
    print("=" * 60)
    
    events = get_all_events(limit=500)
    total = len(events)
    
    for i, event in enumerate(events, 1):
        print(f"\n[{i}/{total}] Processing: {event['title'][:50]}...")
        calculate_price_reactions(event['id'])
        time.sleep(1)  # Rate limiting for yfinance
    
    print("\nPrice reaction calculation complete.")


def main():
    parser = argparse.ArgumentParser(description='Build Event Database')
    parser.add_argument('--populate', action='store_true', help='Add sample events')
    parser.add_argument('--calculate', action='store_true', help='Calculate price reactions')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--all', action='store_true', help='Do everything')
    
    args = parser.parse_args()
    
    if args.all:
        populate_events()
        calculate_all_reactions()
        calculate_statistics()
        print_statistics_report()
    elif args.populate:
        populate_events()
    elif args.calculate:
        calculate_all_reactions()
        calculate_statistics()
    elif args.stats:
        init_db()
        print_statistics_report()
    else:
        parser.print_help()
        print("\nQuick start:")
        print("  python scripts/build_event_database.py --populate  # Add events")
        print("  python scripts/build_event_database.py --stats     # View status")


if __name__ == '__main__':
    main()
