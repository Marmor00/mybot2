#!/usr/bin/env python3
"""
INSIDER TRACKER - Calcula track records y performance de insiders
Usa precios históricos para determinar win rates
"""
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from database import Database
from config import Config


class InsiderTracker:
    def __init__(self, db: Database = None):
        """
        Inicializa el tracker

        Args:
            db: Instancia de Database (opcional, crea una nueva si no se provee)
        """
        self.db = db if db else Database()
        self.finnhub_api_key = Config.FINNHUB_API_KEY if hasattr(Config, 'FINNHUB_API_KEY') else None

        # Configuración de evaluación
        self.MIN_DAYS_TO_EVALUATE = 30  # Solo evaluar trades con mínimo 30 días
        self.WIN_THRESHOLD = 5.0  # Trade es "winning" si return > 5%
        self.LOSS_THRESHOLD = -5.0  # Trade es "losing" si return < -5%

        # Configuración de confianza
        self.CONFIDENCE_THRESHOLDS = {
            'HIGH': {'min_trades': 10, 'min_win_rate': 70.0},
            'MEDIUM': {'min_trades': 5, 'min_win_rate': 60.0},
            'LOW': {'min_trades': 3, 'min_win_rate': 50.0}
        }

    def get_current_price(self, ticker: str) -> Optional[float]:
        """
        Obtiene precio actual de un ticker usando Finnhub

        Args:
            ticker: Símbolo del ticker

        Returns:
            Precio actual o None si hay error
        """
        if not self.finnhub_api_key:
            print(f"WARNING: No Finnhub API key - no se puede obtener precio actual para {ticker}")
            return None

        try:
            url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={self.finnhub_api_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            current_price = data.get('c')  # 'c' = current price

            if current_price and current_price > 0:
                return current_price

            return None

        except Exception as e:
            print(f"WARNING: Error obteniendo precio para {ticker}: {e}")
            return None

    def calculate_trade_return(self, purchase_price: float, current_price: float,
                              purchase_date: str) -> Optional[Dict]:
        """
        Calcula return de un trade individual

        Args:
            purchase_price: Precio de compra del insider
            current_price: Precio actual (o de venta si ya salió)
            purchase_date: Fecha de compra

        Returns:
            Diccionario con return_pct, holding_days, status
        """
        if purchase_price <= 0 or current_price <= 0:
            return None

        # Calcular return porcentual
        return_pct = ((current_price - purchase_price) / purchase_price) * 100

        # Calcular días de holding
        try:
            purchase_dt = datetime.strptime(purchase_date, '%Y-%m-%d')
            holding_days = (datetime.now() - purchase_dt).days
        except:
            holding_days = 999

        # Determinar status
        if return_pct >= self.WIN_THRESHOLD:
            status = 'winning'
        elif return_pct <= self.LOSS_THRESHOLD:
            status = 'losing'
        else:
            status = 'neutral'

        return {
            'return_pct': round(return_pct, 2),
            'holding_days': holding_days,
            'status': status
        }

    def evaluate_insider_trades(self, insider_name: str, ticker: str = None) -> Dict:
        """
        Evalúa todos los trades de un insider y calcula estadísticas

        Args:
            insider_name: Nombre del insider
            ticker: Filtrar por ticker específico (opcional)

        Returns:
            Diccionario con estadísticas detalladas
        """
        # Obtener todas las compras del insider
        purchases_df = self.db.get_insider_purchases(insider_name, ticker)

        if purchases_df.empty:
            return {
                'insider_name': insider_name,
                'ticker': ticker,
                'total_trades': 0,
                'evaluated_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'neutral_trades': 0,
                'pending_trades': 0,
                'win_rate': 0.0,
                'avg_return': 0.0,
                'best_trade': None,
                'worst_trade': None,
                'confidence_level': 'UNKNOWN',
                'total_invested': 0.0
        }

        total_trades = len(purchases_df)
        total_invested = abs(purchases_df['transaction_value'].sum())

        # Filtrar trades que tengan al menos MIN_DAYS_TO_EVALUATE días
        purchases_df['days_old'] = purchases_df.apply(
            lambda row: (datetime.now() - datetime.strptime(row['trade_date'], '%Y-%m-%d')).days,
            axis=1
        )

        mature_trades = purchases_df[purchases_df['days_old'] >= self.MIN_DAYS_TO_EVALUATE]

        if mature_trades.empty:
            # Todos los trades son muy recientes para evaluar
            return {
                'insider_name': insider_name,
                'ticker': ticker,
                'total_trades': total_trades,
                'evaluated_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'neutral_trades': 0,
                'pending_trades': total_trades,
                'win_rate': 0.0,
                'avg_return': 0.0,
                'best_trade': None,
                'worst_trade': None,
                'confidence_level': 'INSUFFICIENT_DATA',
                'total_invested': total_invested
            }

        # Evaluar cada trade maduro
        evaluated_trades = []

        for _, trade in mature_trades.iterrows():
            ticker_symbol = trade['ticker']
            purchase_price = trade['price']
            purchase_date = trade['trade_date']

            # Obtener precio actual
            current_price = self.get_current_price(ticker_symbol)

            if current_price is None:
                # No se pudo obtener precio - skip
                continue

            # Calcular return
            trade_result = self.calculate_trade_return(purchase_price, current_price, purchase_date)

            if trade_result:
                evaluated_trades.append({
                    'ticker': ticker_symbol,
                    'purchase_date': purchase_date,
                    'purchase_price': purchase_price,
                    'current_price': current_price,
                    'return_pct': trade_result['return_pct'],
                    'holding_days': trade_result['holding_days'],
                    'status': trade_result['status'],
                    'trade_value': abs(trade['transaction_value'])
                })

        if not evaluated_trades:
            return {
                'insider_name': insider_name,
                'ticker': ticker,
                'total_trades': total_trades,
                'evaluated_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'neutral_trades': 0,
                'pending_trades': total_trades,
                'win_rate': 0.0,
                'avg_return': 0.0,
                'best_trade': None,
                'worst_trade': None,
                'confidence_level': 'NO_DATA_AVAILABLE',
                'total_invested': total_invested
            }

        # Calcular estadísticas
        trades_df = pd.DataFrame(evaluated_trades)

        winning_trades = len(trades_df[trades_df['status'] == 'winning'])
        losing_trades = len(trades_df[trades_df['status'] == 'losing'])
        neutral_trades = len(trades_df[trades_df['status'] == 'neutral'])

        evaluated_count = len(trades_df)
        win_rate = (winning_trades / evaluated_count) * 100 if evaluated_count > 0 else 0.0
        avg_return = trades_df['return_pct'].mean()

        # Mejor y peor trade
        best_trade = trades_df.loc[trades_df['return_pct'].idxmax()].to_dict() if not trades_df.empty else None
        worst_trade = trades_df.loc[trades_df['return_pct'].idxmin()].to_dict() if not trades_df.empty else None

        # Determinar nivel de confianza
        confidence_level = self.get_confidence_level(win_rate, evaluated_count)

        return {
            'insider_name': insider_name,
            'ticker': ticker,
            'total_trades': total_trades,
            'evaluated_trades': evaluated_count,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'neutral_trades': neutral_trades,
            'pending_trades': total_trades - evaluated_count,
            'win_rate': round(win_rate, 1),
            'avg_return': round(avg_return, 2),
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'confidence_level': confidence_level,
            'total_invested': total_invested,
            'trades_detail': evaluated_trades  # Para debugging
        }

    def get_confidence_level(self, win_rate: float, total_trades: int) -> str:
        """
        Determina nivel de confianza basado en win rate y número de trades

        Args:
            win_rate: Win rate porcentual
            total_trades: Total de trades evaluados

        Returns:
            'HIGH', 'MEDIUM', 'LOW', 'INSUFFICIENT_DATA'
        """
        if total_trades < self.CONFIDENCE_THRESHOLDS['LOW']['min_trades']:
            return 'INSUFFICIENT_DATA'

        # HIGH confidence
        if (total_trades >= self.CONFIDENCE_THRESHOLDS['HIGH']['min_trades'] and
            win_rate >= self.CONFIDENCE_THRESHOLDS['HIGH']['min_win_rate']):
            return 'HIGH'

        # MEDIUM confidence
        if (total_trades >= self.CONFIDENCE_THRESHOLDS['MEDIUM']['min_trades'] and
            win_rate >= self.CONFIDENCE_THRESHOLDS['MEDIUM']['min_win_rate']):
            return 'MEDIUM'

        # LOW confidence (pero tiene datos mínimos)
        if total_trades >= self.CONFIDENCE_THRESHOLDS['LOW']['min_trades']:
            return 'LOW'

        return 'INSUFFICIENT_DATA'

    def calculate_track_record(self, insider_name: str, ticker: str = None) -> Dict:
        """
        Calcula track record completo de un insider

        Esta es la función principal que se usa desde el resto de la app

        Args:
            insider_name: Nombre del insider
            ticker: Filtrar por ticker (opcional)

        Returns:
            Diccionario con track record completo
        """
        stats = self.evaluate_insider_trades(insider_name, ticker)

        # Formatear para respuesta limpia
        track_record = {
            'insider_name': stats['insider_name'],
            'total_trades': stats['total_trades'],
            'evaluated_trades': stats['evaluated_trades'],
            'win_rate': stats['win_rate'],
            'avg_return': stats['avg_return'],
            'confidence_level': stats['confidence_level'],
            'winning_trades': stats['winning_trades'],
            'losing_trades': stats['losing_trades']
        }

        # Agregar best/worst trade si existen
        if stats['best_trade']:
            track_record['best_trade'] = {
                'ticker': stats['best_trade']['ticker'],
                'return': stats['best_trade']['return_pct'],
                'date': stats['best_trade']['purchase_date']
            }

        if stats['worst_trade']:
            track_record['worst_trade'] = {
                'ticker': stats['worst_trade']['ticker'],
                'return': stats['worst_trade']['return_pct'],
                'date': stats['worst_trade']['purchase_date']
            }

        return track_record

    def get_confidence_badge(self, win_rate: float, total_trades: int) -> str:
        """
        Retorna badge de confianza (usado en dashboard)

        Args:
            win_rate: Win rate porcentual
            total_trades: Total de trades evaluados

        Returns:
            'TRUSTED', 'GOOD', 'POOR', 'NEW', 'INSUFFICIENT_DATA'
        """
        confidence = self.get_confidence_level(win_rate, total_trades)

        if confidence == 'HIGH':
            return 'TRUSTED'
        elif confidence == 'MEDIUM':
            return 'GOOD'
        elif confidence == 'LOW':
            if win_rate < 50:
                return 'POOR'
            return 'GOOD'
        else:
            return 'NEW' if total_trades > 0 else 'INSUFFICIENT_DATA'

    def update_all_insiders(self):
        """
        Recalcula estadísticas para todos los insiders en la DB

        NOTA: Esta función puede tardar mucho si hay muchos insiders
        (hace requests a Finnhub para cada ticker)
        """
        print("\nActualizando track records de todos los insiders...")

        all_insiders = self.db.get_all_insiders()
        print(f"Total insiders a procesar: {len(all_insiders)}")

        updated = 0
        for i, insider in enumerate(all_insiders, 1):
            if i % 50 == 0:
                print(f"Procesando {i}/{len(all_insiders)}...")

            try:
                stats = self.evaluate_insider_trades(insider)

                # Guardar en DB
                self.db.save_insider_performance(insider, stats)
                updated += 1

            except Exception as e:
                print(f"WARNING: Error procesando {insider}: {e}")
                continue

        print(f"Track records actualizados: {updated}/{len(all_insiders)}")

    def get_top_insiders(self, limit: int = 10, min_trades: int = 5) -> List[Dict]:
        """
        Obtiene los top insiders por win rate

        Args:
            limit: Número máximo de insiders a retornar
            min_trades: Mínimo de trades para considerar

        Returns:
            Lista de insiders ordenados por win rate
        """
        all_insiders = self.db.get_all_insiders()

        top_insiders = []

        for insider in all_insiders:
            track_record = self.calculate_track_record(insider)

            if track_record['evaluated_trades'] >= min_trades:
                top_insiders.append(track_record)

        # Ordenar por win rate
        top_insiders.sort(key=lambda x: x['win_rate'], reverse=True)

        return top_insiders[:limit]


def main():
    """Test del insider tracker"""
    print("INSIDER TRACKER TEST")
    print("=" * 60)

    # Inicializar
    db = Database()
    tracker = InsiderTracker(db)

    # Obtener algunos insiders de ejemplo
    all_insiders = db.get_all_insiders()

    if not all_insiders:
        print("No hay insiders en la base de datos")
        return

    print(f"\nTotal insiders en DB: {len(all_insiders)}")

    # Probar con primer insider que tenga compras
    test_insider = None
    for insider in all_insiders[:100]:  # Probar primeros 100
        purchases = db.get_insider_purchases(insider)
        if not purchases.empty:
            test_insider = insider
            break

    if test_insider:
        print(f"\nCalculando track record para: {test_insider}")
        track_record = tracker.calculate_track_record(test_insider)

        print(f"\nRESULTADOS:")
        print(f"  Total trades: {track_record['total_trades']}")
        print(f"  Evaluated trades: {track_record['evaluated_trades']}")
        print(f"  Win rate: {track_record['win_rate']}%")
        print(f"  Avg return: {track_record['avg_return']}%")
        print(f"  Confidence: {track_record['confidence_level']}")

        if 'best_trade' in track_record:
            print(f"  Best trade: {track_record['best_trade']['ticker']} ({track_record['best_trade']['return']}%)")

    db.close()
    print("\nTest completado")


if __name__ == "__main__":
    main()
