#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INSIDER TRACK RECORD SYSTEM - Month 1, Week 1-2 (PRAGMATIC VERSION)
====================================================================

Objetivo: Calcular win rate histórico individual de insiders usando datos existentes
- Usar datos de insiders ya scraped en insider_data.db
- Calcular win rate retrospectivo: % de trades +precio en 30 días
- Filtrar solo insiders con historical_win_rate >= 60%

APPROACH PRAGMÁTICO:
En lugar de descargar Form 4 históricos del SEC, usamos los datos que YA TENEMOS
de nuestro scraping diario. Esto nos da track records inmediatos y realistas.

Filosofía "Zero Feelings":
- Si los datos muestran que insider trading no tiene edge → ELIMINAR
- Este es el primer test científico del sistema

"""

import sys
import os

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

# Agregar core al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

import yfinance as yf
import pandas as pd
import sqlite3


class InsiderTrackRecordSystem:
    """Sistema para calcular track record histórico de insiders usando datos scraped"""

    def __init__(self, db_path="data/insider_trading.db"):
        """
        Args:
            db_path: Path a la database con datos de insiders
        """
        self.db_path = Path(db_path)

        if not self.db_path.exists():
            print(f"[WARN] Database no encontrada: {self.db_path}")
            print(f"   Ejecuta scraper primero para tener datos")
            return

        self._init_track_record_schema()
        print(f"[OK] Insider Track Record System inicializado")
        print(f"   Database: {self.db_path}")

    def _init_track_record_schema(self):
        """Crea tablas para track records si no existen"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabla de track records agregados por insider
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS insider_track_records (
                insider_name TEXT PRIMARY KEY,
                ticker TEXT,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                avg_return_pct REAL DEFAULT 0.0,
                last_updated TEXT
            )
        ''')

        # Tabla de trades históricos con resultados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS insider_trades_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                insider_name TEXT,
                purchase_date TEXT,
                shares REAL,
                price_at_purchase REAL,
                price_30d_later REAL,
                return_pct REAL,
                is_winner INTEGER,
                calculated_at TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def get_historical_insider_trades(self) -> pd.DataFrame:
        """
        Obtiene todos los trades de insiders scraped que tienen >= 30 días de antigüedad
        (para poder calcular win rate con datos de 30 días)

        Returns:
            DataFrame con trades históricos
        """
        conn = sqlite3.connect(self.db_path)

        # Query para obtener trades de compra con >= 30 días
        query = '''
            SELECT
                ticker,
                insider_name,
                trade_date as purchase_date,
                qty as shares,
                price as price_at_purchase
            FROM insider_trades
            WHERE transaction_type LIKE '%Purchase%'
              AND trade_date IS NOT NULL
              AND price IS NOT NULL
              AND price > 0
        '''

        try:
            df = pd.read_sql_query(query, conn)
            conn.close()

            if df.empty:
                print("[WARN] No se encontraron trades de compra en la database")
                return pd.DataFrame()

            print(f"[OK] {len(df)} purchase trades encontrados")

            # Filtrar solo trades entre 30 días y 12 meses (para track record relevante)
            df['purchase_date'] = pd.to_datetime(df['purchase_date'])
            date_30d_ago = datetime.now() - timedelta(days=30)
            date_12m_ago = datetime.now() - timedelta(days=365)

            df_filtered = df[(df['purchase_date'] >= date_12m_ago) & (df['purchase_date'] < date_30d_ago)]

            print(f"   {len(df_filtered)} trades entre 30 días y 12 meses (aptos para cálculo)")

            return df_filtered

        except Exception as e:
            conn.close()
            print(f"[ERROR] Error extrayendo trades: {e}")
            return pd.DataFrame()

    def calculate_track_records(self, save_to_db: bool = True):
        """
        Calcula track records retrospectivos para todos los insiders en la database

        Args:
            save_to_db: Si True, guarda resultados en database
        """
        print(f"\n{'='*70}")
        print(f"CALCULANDO TRACK RECORDS RETROSPECTIVOS")
        print(f"{'='*70}\n")

        # Obtener trades históricos
        trades_df = self.get_historical_insider_trades()

        if trades_df.empty:
            print("[WARN] No hay trades históricos para calcular")
            return

        print(f"[*] Calculando win rates para {len(trades_df)} trades...")
        print(f"   (esto puede tardar debido a rate limiting de yfinance)\n")

        results = []

        for idx, trade in trades_df.iterrows():
            if (idx + 1) % 10 == 0:
                print(f"   Progreso: {idx+1}/{len(trades_df)} trades...")

            try:
                ticker = trade['ticker']
                purchase_date = trade['purchase_date']
                purchase_price = trade['price_at_purchase']

                # Calcular precio 30 días después
                date_30d_later = purchase_date + timedelta(days=30)

                # Descargar datos históricos
                stock = yf.Ticker(ticker)
                end_date = min(date_30d_later + timedelta(days=5), datetime.now())

                hist = stock.history(
                    start=purchase_date.strftime("%Y-%m-%d"),
                    end=end_date.strftime("%Y-%m-%d")
                )

                if hist.empty or len(hist) < 20:
                    continue

                # Precio ~30 días después
                target_idx = min(29, len(hist) - 1)
                price_30d = hist.iloc[target_idx]['Close']

                # Return
                return_pct = ((price_30d - purchase_price) / purchase_price) * 100
                is_winner = 1 if return_pct >= 0 else 0

                results.append({
                    'ticker': ticker,
                    'insider_name': trade['insider_name'],
                    'purchase_date': purchase_date.strftime("%Y-%m-%d"),
                    'shares': trade['shares'],
                    'price_at_purchase': purchase_price,
                    'price_30d_later': price_30d,
                    'return_pct': return_pct,
                    'is_winner': is_winner,
                    'calculated_at': datetime.now().isoformat()
                })

                # Rate limiting (yfinance recomienda pausas - 1 segundo para evitar rate limit)
                time.sleep(1.0)

            except Exception as e:
                print(f"      Error procesando {trade['ticker']}: {e}")
                continue

        print(f"\n[OK] {len(results)} trades procesados con éxito\n")

        if len(results) == 0:
            print("[WARN] No se pudieron calcular resultados")
            return

        # Guardar y analizar
        if save_to_db:
            self._save_results_to_db(results)

        self._print_summary(results)

    def _save_results_to_db(self, results: List[Dict]):
        """Guarda resultados en database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Guardar trades individuales
        for result in results:
            cursor.execute('''
                INSERT INTO insider_trades_results
                (ticker, insider_name, purchase_date, shares, price_at_purchase,
                 price_30d_later, return_pct, is_winner, calculated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result['ticker'],
                result['insider_name'],
                result['purchase_date'],
                result['shares'],
                result['price_at_purchase'],
                result['price_30d_later'],
                result['return_pct'],
                result['is_winner'],
                result['calculated_at']
            ))

        # Calcular agregados por insider
        df = pd.DataFrame(results)
        insider_stats = df.groupby(['insider_name', 'ticker']).agg({
            'is_winner': ['count', 'sum'],
            'return_pct': 'mean'
        }).reset_index()

        insider_stats.columns = ['insider_name', 'ticker', 'total_trades', 'winning_trades', 'avg_return_pct']
        insider_stats['losing_trades'] = insider_stats['total_trades'] - insider_stats['winning_trades']
        insider_stats['win_rate'] = (insider_stats['winning_trades'] / insider_stats['total_trades'] * 100).round(2)
        insider_stats['last_updated'] = datetime.now().isoformat()

        # Guardar agregados
        for _, row in insider_stats.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO insider_track_records
                (insider_name, ticker, total_trades, winning_trades, losing_trades,
                 win_rate, avg_return_pct, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['insider_name'],
                row['ticker'],
                int(row['total_trades']),
                int(row['winning_trades']),
                int(row['losing_trades']),
                float(row['win_rate']),
                float(row['avg_return_pct']),
                row['last_updated']
            ))

        conn.commit()
        conn.close()

        print(f"[OK] Resultados guardados en database")
        print(f"   - {len(results)} trades individuales")
        print(f"   - {len(insider_stats)} insiders únicos\n")

    def _print_summary(self, results: List[Dict]):
        """Imprime resumen de track records"""
        df = pd.DataFrame(results)

        print(f"{'='*70}")
        print(f"RESUMEN DE TRACK RECORDS RETROSPECTIVOS")
        print(f"{'='*70}\n")

        # Estadísticas generales
        overall_wr = (df['is_winner'].sum() / len(df)) * 100
        overall_avg_ret = df['return_pct'].mean()

        print(f"[*] ESTADÍSTICAS GENERALES:")
        print(f"   Total trades analizados: {len(df)}")
        print(f"   Winning trades: {df['is_winner'].sum()}")
        print(f"   Losing trades: {len(df) - df['is_winner'].sum()}")
        print(f"   Win Rate GLOBAL: {overall_wr:.1f}%")
        print(f"   Avg Return: {overall_avg_ret:+.2f}%\n")

        # CRÍTICO: ¿Insider trading tiene edge?
        print(f"[*] EVALUACIÓN CRÍTICA:")
        if overall_wr < 52:
            print(f"   [X] Win rate < 52%: NO HAY EDGE ESTADÍSTICO")
            print(f"   [X] CONCLUSIÓN: Insider trading solo NO es rentable")
        elif 52 <= overall_wr < 58:
            print(f"   [WARN] Win rate 52-58%: EDGE MUY DEBIL")
            print(f"   [WARN] CONCLUSION: Necesita capas adicionales (Month 2-6)")
        elif 58 <= overall_wr < 65:
            print(f"   [OK] Win rate 58-65%: EDGE MODERADO")
            print(f"   [OK] CONCLUSIÓN: Prometedor con optimización")
        else:
            print(f"   [OK] Win rate > 65%: EDGE FUERTE")
            print(f"   [OK] CONCLUSIÓN: Sistema viable")

        print()

        # Agrupar por insider
        insider_stats = df.groupby(['insider_name', 'ticker']).agg({
            'is_winner': ['count', 'sum', 'mean'],
            'return_pct': 'mean'
        }).round(2)

        insider_stats.columns = ['Total', 'Wins', 'WR', 'Avg Return %']
        insider_stats['WR'] = (insider_stats['WR'] * 100).round(1)
        insider_stats = insider_stats.sort_values('WR', ascending=False)

        print(f"TOP 15 INSIDERS POR WIN RATE:")
        print(insider_stats.head(15).to_string())
        print()

        # Filtro de calidad
        quality_insiders = insider_stats[insider_stats['WR'] >= 60.0]
        print(f"[OK] INSIDERS CON WR >= 60%: {len(quality_insiders)}/{len(insider_stats)}")
        print(f"   ({len(quality_insiders)/len(insider_stats)*100:.1f}% del total)")

        if len(quality_insiders) > 0:
            print(f"\n   [+] Estos insiders tienen track record comprobado")
            print(f"   [+] RECOMENDACION: Seguir solo a estos {len(quality_insiders)} insiders")
        else:
            print(f"\n   [WARN] NINGUN insider tiene WR >= 60%")
            print(f"   [WARN] RECOMENDACION: Revisar estrategia o agregar mas capas")

        print(f"\n{'='*70}\n")

    def filter_quality_insiders(self, min_win_rate: float = 60.0, min_trades: int = 3) -> pd.DataFrame:
        """
        Obtiene insiders de calidad desde la database

        Args:
            min_win_rate: Win rate mínimo (%)
            min_trades: Número mínimo de trades

        Returns:
            DataFrame con insiders de calidad
        """
        conn = sqlite3.connect(self.db_path)

        query = f'''
            SELECT * FROM insider_track_records
            WHERE win_rate >= {min_win_rate} AND total_trades >= {min_trades}
            ORDER BY win_rate DESC
        '''

        df = pd.read_sql_query(query, conn)
        conn.close()

        return df


def main():
    """Test del sistema con datos existentes"""

    print("\n" + "="*70)
    print("INSIDER TRACK RECORD SYSTEM - PRAGMATIC VERSION")
    print("="*70)
    print("\nEste sistema calcula track records usando datos YA scraped")
    print("No requiere descargar Form 4s del SEC\n")

    system = InsiderTrackRecordSystem()

    # Calcular track records
    system.calculate_track_records(save_to_db=True)

    # Obtener insiders de calidad
    quality = system.filter_quality_insiders(min_win_rate=60.0, min_trades=2)

    if not quality.empty:
        print(f"{'='*70}")
        print(f"INSIDERS DE CALIDAD PARA MONTH 1")
        print(f"{'='*70}\n")

        for _, insider in quality.iterrows():
            print(f"{insider['insider_name']} ({insider['ticker']})")
            print(f"   Win Rate: {insider['win_rate']:.1f}%")
            print(f"   Trades: {insider['total_trades']} (W:{insider['winning_trades']}, L:{insider['losing_trades']})")
            print(f"   Avg Return: {insider['avg_return_pct']:+.2f}%")
            print()

        print(f"[*] NEXT STEP: Integrar estos {len(quality)} insiders en multi_trader.py")
        print(f"              Solo seguir trades de estos insiders\n")
    else:
        print(f"[WARN] NO HAY INSIDERS DE CALIDAD")
        print(f"   Necesitas mas datos o ajustar criterios\n")


if __name__ == "__main__":
    main()
