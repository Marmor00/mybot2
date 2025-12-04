#!/usr/bin/env python3
"""
DATABASE MODULE - SQLite para Insider Trading Track Records
Gestiona histórico de trades y performance de insiders
"""
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import json


class Database:
    def __init__(self, db_path: str = "data/insider_trading.db"):
        """Inicializa conexión a base de datos SQLite"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.conn = None
        self.init_database()

    def get_connection(self):
        """Obtiene conexión SQLite (singleton)"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
        return self.conn

    def init_database(self):
        """Crea todas las tablas si no existen"""
        conn = self.get_connection()
        cursor = conn.cursor()

        print("Inicializando base de datos SQLite...")

        # Tabla 1: Trades históricos (todas las transacciones)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS insider_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                company_name TEXT,
                insider_name TEXT NOT NULL,
                insider_title TEXT,
                trade_date DATE NOT NULL,
                filing_date DATE,
                transaction_type TEXT,  -- 'P - Purchase', 'S - Sale', etc.
                price REAL NOT NULL,
                qty INTEGER,
                shares_owned INTEGER,
                ownership_change REAL,
                transaction_value REAL NOT NULL,
                days_since_trade INTEGER,
                scrape_date DATE,
                UNIQUE(ticker, insider_name, trade_date, transaction_value)
            )
        """)

        # Índices para búsquedas rápidas
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticker
            ON insider_trades(ticker)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_insider_name
            ON insider_trades(insider_name)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trade_date
            ON insider_trades(trade_date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transaction_type
            ON insider_trades(transaction_type)
        """)

        # Tabla 2: Performance de insiders (estadísticas calculadas)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS insider_performance (
                insider_name TEXT PRIMARY KEY,
                ticker TEXT,
                total_trades INTEGER DEFAULT 0,
                total_purchases INTEGER DEFAULT 0,
                total_sales INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                pending_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                avg_return REAL DEFAULT 0.0,
                best_trade_return REAL DEFAULT 0.0,
                best_trade_ticker TEXT,
                worst_trade_return REAL DEFAULT 0.0,
                worst_trade_ticker TEXT,
                total_invested REAL DEFAULT 0.0,
                last_updated DATE
            )
        """)

        # Tabla 3: Resultados de trades individuales
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                insider_name TEXT NOT NULL,
                purchase_date DATE NOT NULL,
                purchase_price REAL NOT NULL,
                purchase_value REAL,
                exit_date DATE,
                exit_price REAL,
                exit_value REAL,
                holding_days INTEGER,
                return_pct REAL,
                return_usd REAL,
                status TEXT DEFAULT 'open',  -- 'open', 'closed', 'partial'
                evaluation_date DATE,  -- Cuándo se calculó este return
                FOREIGN KEY(ticker) REFERENCES insider_trades(ticker),
                FOREIGN KEY(insider_name) REFERENCES insider_trades(insider_name)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trade_results_insider
            ON trade_results(insider_name)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trade_results_status
            ON trade_results(status)
        """)

        conn.commit()
        print("Base de datos inicializada correctamente")

    def migrate_from_csv(self, csv_path: str = "data/insider_trades_raw.csv"):
        """
        Migra datos históricos desde CSV a SQLite

        Args:
            csv_path: Ruta al CSV con datos históricos
        """
        print(f"\nMIGRANDO DATOS DESDE CSV...")
        print(f"Archivo: {csv_path}")

        csv_file = Path(csv_path)
        if not csv_file.exists():
            print(f"WARNING: Archivo CSV no encontrado: {csv_path}")
            return False

        try:
            # Leer CSV
            df = pd.read_csv(csv_path)
            print(f"Trades en CSV: {len(df)}")

            # Limpiar y preparar datos
            df['scrape_date'] = datetime.now().strftime('%Y-%m-%d')

            # Asegurar que trade_date esté en formato correcto
            if 'trade_date' in df.columns:
                # Si trade_date tiene timestamp, convertir a solo fecha
                df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')

            if 'filing_date' in df.columns:
                df['filing_date'] = pd.to_datetime(df['filing_date'], errors='coerce').dt.strftime('%Y-%m-%d')

            # Insertar en base de datos (ignorar duplicados)
            conn = self.get_connection()

            inserted = 0
            duplicates = 0

            for _, row in df.iterrows():
                try:
                    self.insert_trade(
                        ticker=row['ticker'],
                        company_name=row.get('company_name', ''),
                        insider_name=row['insider_name'],
                        insider_title=row.get('title', ''),
                        trade_date=row['trade_date'],
                        filing_date=row.get('filing_date', None),
                        transaction_type=row.get('transaction_type', ''),
                        price=float(row['price']) if row['price'] else 0.0,
                        qty=int(row['qty']) if row['qty'] and row['qty'] != 0 else None,
                        shares_owned=int(row['shares_owned']) if 'shares_owned' in row and row['shares_owned'] else None,
                        ownership_change=float(row['ownership_change']) if 'ownership_change' in row and row['ownership_change'] else None,
                        transaction_value=float(row['transaction_value']) if row['transaction_value'] else 0.0,
                        days_since_trade=int(row['days_since_trade']) if 'days_since_trade' in row else None,
                        scrape_date=row['scrape_date']
                    )
                    inserted += 1
                except sqlite3.IntegrityError:
                    # Duplicado - ignorar
                    duplicates += 1
                    continue
                except Exception as e:
                    print(f"WARNING: Error insertando trade {row.get('ticker', 'N/A')}: {e}")
                    continue

            conn.commit()

            print(f"\nMIGRACION COMPLETADA")
            print(f"   Insertados: {inserted}")
            print(f"   Duplicados ignorados: {duplicates}")
            print(f"   Total en DB: {self.get_total_trades()}")

            return True

        except Exception as e:
            print(f"ERROR: Error en migracion: {e}")
            return False

    def insert_trade(self, ticker: str, insider_name: str, trade_date: str,
                    transaction_type: str, price: float, transaction_value: float,
                    company_name: str = '', insider_title: str = '',
                    filing_date: str = None, qty: int = None,
                    shares_owned: int = None, ownership_change: float = None,
                    days_since_trade: int = None, scrape_date: str = None):
        """
        Inserta un trade en la base de datos

        Raises:
            sqlite3.IntegrityError si el trade ya existe (duplicado)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        if scrape_date is None:
            scrape_date = datetime.now().strftime('%Y-%m-%d')

        cursor.execute("""
            INSERT INTO insider_trades (
                ticker, company_name, insider_name, insider_title,
                trade_date, filing_date, transaction_type, price, qty,
                shares_owned, ownership_change, transaction_value,
                days_since_trade, scrape_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker, company_name, insider_name, insider_title,
            trade_date, filing_date, transaction_type, price, qty,
            shares_owned, ownership_change, transaction_value,
            days_since_trade, scrape_date
        ))

    def get_total_trades(self) -> int:
        """Retorna total de trades en la base de datos"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM insider_trades")
        return cursor.fetchone()[0]

    def get_insider_trades(self, insider_name: str, transaction_type: str = None) -> pd.DataFrame:
        """
        Obtiene todos los trades de un insider específico

        Args:
            insider_name: Nombre del insider
            transaction_type: Filtrar por tipo ('P - Purchase', 'S - Sale', etc.)

        Returns:
            DataFrame con los trades
        """
        conn = self.get_connection()

        if transaction_type:
            query = """
                SELECT * FROM insider_trades
                WHERE insider_name = ? AND transaction_type LIKE ?
                ORDER BY trade_date DESC
            """
            df = pd.read_sql_query(query, conn, params=(insider_name, f"%{transaction_type}%"))
        else:
            query = """
                SELECT * FROM insider_trades
                WHERE insider_name = ?
                ORDER BY trade_date DESC
            """
            df = pd.read_sql_query(query, conn, params=(insider_name,))

        return df

    def get_insider_purchases(self, insider_name: str, ticker: str = None) -> pd.DataFrame:
        """Obtiene solo las COMPRAS de un insider"""
        conn = self.get_connection()

        if ticker:
            query = """
                SELECT * FROM insider_trades
                WHERE insider_name = ?
                AND ticker = ?
                AND transaction_type LIKE '%Purchase%'
                ORDER BY trade_date DESC
            """
            df = pd.read_sql_query(query, conn, params=(insider_name, ticker))
        else:
            query = """
                SELECT * FROM insider_trades
                WHERE insider_name = ?
                AND transaction_type LIKE '%Purchase%'
                ORDER BY trade_date DESC
            """
            df = pd.read_sql_query(query, conn, params=(insider_name,))

        return df

    def get_insider_sales(self, insider_name: str, ticker: str = None) -> pd.DataFrame:
        """Obtiene solo las VENTAS de un insider"""
        conn = self.get_connection()

        if ticker:
            query = """
                SELECT * FROM insider_trades
                WHERE insider_name = ?
                AND ticker = ?
                AND transaction_type LIKE '%Sale%'
                ORDER BY trade_date DESC
            """
            df = pd.read_sql_query(query, conn, params=(insider_name, ticker))
        else:
            query = """
                SELECT * FROM insider_trades
                WHERE insider_name = ?
                AND transaction_type LIKE '%Sale%'
                ORDER BY trade_date DESC
            """
            df = pd.read_sql_query(query, conn, params=(insider_name,))

        return df

    def get_all_insiders(self) -> List[str]:
        """Retorna lista de todos los insiders únicos en la DB"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT insider_name FROM insider_trades ORDER BY insider_name")
        return [row[0] for row in cursor.fetchall()]

    def save_insider_performance(self, insider_name: str, stats: Dict):
        """
        Guarda/actualiza estadísticas de performance de un insider

        Args:
            insider_name: Nombre del insider
            stats: Diccionario con estadísticas calculadas
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO insider_performance (
                insider_name, ticker, total_trades, total_purchases, total_sales,
                winning_trades, losing_trades, pending_trades, win_rate, avg_return,
                best_trade_return, best_trade_ticker, worst_trade_return, worst_trade_ticker,
                total_invested, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            insider_name,
            stats.get('ticker', None),
            stats.get('total_trades', 0),
            stats.get('total_purchases', 0),
            stats.get('total_sales', 0),
            stats.get('winning_trades', 0),
            stats.get('losing_trades', 0),
            stats.get('pending_trades', 0),
            stats.get('win_rate', 0.0),
            stats.get('avg_return', 0.0),
            stats.get('best_trade_return', 0.0),
            stats.get('best_trade_ticker', None),
            stats.get('worst_trade_return', 0.0),
            stats.get('worst_trade_ticker', None),
            stats.get('total_invested', 0.0),
            datetime.now().strftime('%Y-%m-%d')
        ))

        conn.commit()

    def get_insider_performance(self, insider_name: str) -> Optional[Dict]:
        """
        Obtiene estadísticas guardadas de un insider

        Returns:
            Diccionario con stats o None si no existe
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM insider_performance WHERE insider_name = ?
        """, (insider_name,))

        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def save_trade_result(self, ticker: str, insider_name: str, purchase_date: str,
                         purchase_price: float, purchase_value: float = None,
                         exit_date: str = None, exit_price: float = None,
                         exit_value: float = None, status: str = 'open'):
        """
        Guarda resultado de un trade individual

        Args:
            status: 'open', 'closed', 'partial'
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Calcular return si hay exit
        return_pct = None
        return_usd = None
        holding_days = None

        if exit_price and exit_date:
            return_pct = ((exit_price - purchase_price) / purchase_price) * 100

            if purchase_value and exit_value:
                return_usd = exit_value - purchase_value

            # Calcular días de holding
            from datetime import datetime
            purchase_dt = datetime.strptime(purchase_date, '%Y-%m-%d')
            exit_dt = datetime.strptime(exit_date, '%Y-%m-%d')
            holding_days = (exit_dt - purchase_dt).days

        cursor.execute("""
            INSERT INTO trade_results (
                ticker, insider_name, purchase_date, purchase_price, purchase_value,
                exit_date, exit_price, exit_value, holding_days,
                return_pct, return_usd, status, evaluation_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker, insider_name, purchase_date, purchase_price, purchase_value,
            exit_date, exit_price, exit_value, holding_days,
            return_pct, return_usd, status, datetime.now().strftime('%Y-%m-%d')
        ))

        conn.commit()

    def close(self):
        """Cierra conexión a la base de datos"""
        if self.conn:
            self.conn.close()
            self.conn = None


def main():
    """Test del módulo de base de datos"""
    print("DATABASE MODULE TEST")
    print("=" * 60)

    # Crear instancia
    db = Database()

    # Migrar desde CSV
    success = db.migrate_from_csv()

    if success:
        # Mostrar estadísticas
        total = db.get_total_trades()
        insiders = db.get_all_insiders()

        print(f"\nESTADISTICAS DE LA BASE DE DATOS")
        print(f"   Total trades: {total}")
        print(f"   Total insiders unicos: {len(insiders)}")

        # Ejemplo: obtener trades de un insider
        if insiders:
            example_insider = insiders[0]
            trades = db.get_insider_trades(example_insider)
            purchases = db.get_insider_purchases(example_insider)

            print(f"\nEjemplo: {example_insider}")
            print(f"   Total trades: {len(trades)}")
            print(f"   Purchases: {len(purchases)}")

    db.close()
    print("\nTest completado")


if __name__ == "__main__":
    main()
