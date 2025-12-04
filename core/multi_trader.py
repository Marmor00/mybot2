#!/usr/bin/env python3
"""
MULTI-TRADER SYSTEM
Sistema de paper trading con múltiples estrategias paralelas
Para validación científica de qué estrategia funciona mejor
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json


# Definición de las 5 estrategias
STRATEGIES = {
    'ultra_conservative': {
        'name': 'Ultra Conservative',
        'emoji': '[UC]',
        'description': 'Calidad extrema > Cantidad',
        'initial_capital': 10000,
        'position_size_pct': 0.10,
        'max_positions': 10,
        'holding_period_days': 30,
        'stop_loss_pct': -10.0,
        'take_profit_pct': 30.0,
        'filters': {
            'min_score': 90,
            'min_momentum': 4.0,
            'stages': ['early_positive'],
            'max_days_old': 2
        }
    },
    'balanced_optimal': {
        'name': 'Balanced Optimal',
        'emoji': '[BO]',
        'description': 'Balance óptimo entre selectividad y oportunidad',
        'initial_capital': 10000,
        'position_size_pct': 0.10,
        'max_positions': 10,
        'holding_period_days': 30,
        'stop_loss_pct': -12.0,
        'take_profit_pct': 22.0,
        'filters': {
            'min_score': 80,
            'min_momentum': 2.5,
            'stages': ['early_positive', 'early_neutral', 'confirmed_positive'],
            'max_days_old': 4
        }
    },
    'momentum_hunter': {
        'name': 'Momentum Hunter',
        'emoji': '[MH]',
        'description': 'Momentum fuerte > Score alto',
        'initial_capital': 10000,
        'position_size_pct': 0.10,
        'max_positions': 10,
        'holding_period_days': 40,
        'stop_loss_pct': -15.0,
        'take_profit_pct': 35.0,
        'filters': {
            'min_score': 75,
            'min_momentum': 6.0,
            'stages': ['early_positive', 'early_neutral', 'confirmed_positive'],
            'max_days_old': 5
        }
    },
    'early_stage_master': {
        'name': 'Early Stage Master',
        'emoji': '[ES]',
        'description': 'Early stage es crítico',
        'initial_capital': 10000,
        'position_size_pct': 0.10,
        'max_positions': 10,
        'holding_period_days': 30,
        'stop_loss_pct': -15.0,
        'take_profit_pct': 25.0,
        'filters': {
            'min_score': 78,
            'min_momentum': 2.0,
            'stages': ['early_positive'],
            'max_days_old': 3
        }
    },
    'diversified_portfolio': {
        'name': 'Diversified Portfolio',
        'emoji': '[DP]',
        'description': 'Más trades pequeños = menos riesgo',
        'initial_capital': 10000,
        'position_size_pct': 0.0667,  # 6.67%
        'max_positions': 15,
        'holding_period_days': 35,
        'stop_loss_pct': -15.0,
        'take_profit_pct': 25.0,
        'filters': {
            'min_score': 75,
            'min_momentum': 1.5,
            'stages': ['early_positive', 'early_neutral', 'confirmed_positive'],
            'max_days_old': 7
        }
    }
}


class MultiTraderSystem:
    def __init__(self, db_path: str = "data/multi_trader.db"):
        """Inicializa el sistema multi-trader"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.conn = None
        self.strategies = STRATEGIES
        self.init_database()

    def get_connection(self):
        """Obtiene conexión a la base de datos"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def init_database(self):
        """Crea tablas para cada estrategia"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Tabla de posiciones (una para todas las estrategias)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy TEXT NOT NULL,
                ticker TEXT NOT NULL,
                entry_date DATE NOT NULL,
                entry_price REAL NOT NULL,
                shares INTEGER NOT NULL,
                position_value REAL NOT NULL,
                exit_date DATE,
                exit_price REAL,
                exit_reason TEXT,
                return_pct REAL,
                profit_usd REAL,
                status TEXT DEFAULT 'open',
                score INTEGER,
                momentum REAL,
                stage TEXT,
                insider_name TEXT,
                opportunity_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Índice por estrategia
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_strategy_status
            ON positions(strategy, status)
        """)

        # Tabla de portfolio history por estrategia
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy TEXT NOT NULL,
                date DATE NOT NULL,
                total_value REAL NOT NULL,
                cash REAL NOT NULL,
                invested REAL NOT NULL,
                total_return_pct REAL,
                open_positions INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(strategy, date)
            )
        """)

        # Tabla de configuración por estrategia
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                strategy TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (strategy, key)
            )
        """)

        # Inicializar capital para cada estrategia
        for strategy_id, config in self.strategies.items():
            cursor.execute(
                "SELECT value FROM config WHERE strategy = ? AND key = 'initial_capital'",
                (strategy_id,)
            )
            if not cursor.fetchone():
                initial = config['initial_capital']
                cursor.execute(
                    "INSERT INTO config (strategy, key, value) VALUES (?, 'initial_capital', ?)",
                    (strategy_id, str(initial))
                )
                cursor.execute(
                    "INSERT INTO config (strategy, key, value) VALUES (?, 'current_cash', ?)",
                    (strategy_id, str(initial))
                )

        conn.commit()
        print("Multi-Trader System inicializado")

    def get_current_cash(self, strategy: str) -> float:
        """Obtiene cash disponible para una estrategia"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT value FROM config WHERE strategy = ? AND key = 'current_cash'",
            (strategy,)
        )
        result = cursor.fetchone()
        return float(result[0]) if result else self.strategies[strategy]['initial_capital']

    def update_cash(self, strategy: str, new_cash: float):
        """Actualiza cash disponible"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE config SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE strategy = ? AND key = 'current_cash'",
            (str(new_cash), strategy)
        )
        conn.commit()

    def get_open_positions(self, strategy: str) -> List[Dict]:
        """Obtiene posiciones abiertas de una estrategia"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM positions
            WHERE strategy = ? AND status = 'open'
            ORDER BY entry_date DESC
        """, (strategy,))
        return [dict(row) for row in cursor.fetchall()]

    def should_auto_buy(self, strategy: str, opportunity: Dict) -> bool:
        """Determina si una estrategia debe comprar esta oportunidad"""
        config = self.strategies[strategy]
        filters = config['filters']

        # Verificar filtros
        score = opportunity.get('score', 0)
        momentum = opportunity.get('momentum_pct', 0)
        stage = opportunity.get('stage', '')
        days_old = opportunity.get('days_since_latest', 999)

        if score < filters['min_score']:
            return False
        if momentum < filters['min_momentum']:
            return False
        if stage not in filters['stages']:
            return False
        if days_old > filters['max_days_old']:
            return False

        # Verificar que no esté ya en portfolio
        open_positions = self.get_open_positions(strategy)
        if any(pos['ticker'] == opportunity['ticker'] for pos in open_positions):
            return False

        # Verificar espacio para más posiciones
        if len(open_positions) >= config['max_positions']:
            return False

        # Verificar cash disponible
        current_cash = self.get_current_cash(strategy)
        position_size = config['initial_capital'] * config['position_size_pct']
        if current_cash < position_size:
            return False

        return True

    def buy_position(self, strategy: str, opportunity: Dict, current_price: float) -> Optional[int]:
        """Ejecuta una compra para una estrategia"""
        config = self.strategies[strategy]
        ticker = opportunity['ticker']
        position_value = config['initial_capital'] * config['position_size_pct']
        shares = int(position_value / current_price)
        actual_cost = shares * current_price

        current_cash = self.get_current_cash(strategy)
        if current_cash < actual_cost:
            return None

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO positions (
                strategy, ticker, entry_date, entry_price, shares, position_value,
                status, score, momentum, stage, insider_name, opportunity_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            strategy,
            ticker,
            datetime.now().strftime('%Y-%m-%d'),
            current_price,
            shares,
            actual_cost,
            'open',
            opportunity.get('score'),
            opportunity.get('momentum_pct'),
            opportunity.get('stage'),
            opportunity.get('insider_name', ''),
            json.dumps(opportunity, default=str)
        ))

        position_id = cursor.lastrowid
        new_cash = current_cash - actual_cost
        self.update_cash(strategy, new_cash)
        conn.commit()

        return position_id

    def check_exit_conditions(self, strategy: str, position: Dict, current_price: float) -> Optional[str]:
        """Verifica si debe cerrar posición"""
        config = self.strategies[strategy]
        entry_price = position['entry_price']
        entry_date = datetime.strptime(position['entry_date'], '%Y-%m-%d')
        days_held = (datetime.now() - entry_date).days

        return_pct = ((current_price - entry_price) / entry_price) * 100

        # Stop loss
        if return_pct <= config['stop_loss_pct']:
            return f"Stop Loss ({return_pct:.2f}%)"

        # Take profit
        if return_pct >= config['take_profit_pct']:
            return f"Take Profit ({return_pct:.2f}%)"

        # Holding period
        if days_held >= config['holding_period_days']:
            return f"Holding Period ({days_held} days)"

        return None

    def sell_position(self, strategy: str, position: Dict, current_price: float, reason: str):
        """Ejecuta una venta"""
        position_id = position['id']
        shares = position['shares']
        entry_price = position['entry_price']

        exit_value = shares * current_price
        profit = exit_value - position['position_value']
        return_pct = ((current_price - entry_price) / entry_price) * 100

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE positions
            SET exit_date = ?, exit_price = ?, exit_reason = ?,
                return_pct = ?, profit_usd = ?, status = 'closed'
            WHERE id = ?
        """, (
            datetime.now().strftime('%Y-%m-%d'),
            current_price,
            reason,
            return_pct,
            profit,
            position_id
        ))

        current_cash = self.get_current_cash(strategy)
        new_cash = current_cash + exit_value
        self.update_cash(strategy, new_cash)
        conn.commit()

    def process_opportunities(self, opportunities: List[Dict], current_prices: Dict[str, float]):
        """Procesa oportunidades para TODAS las estrategias"""
        print("\n" + "=" * 70)
        print("MULTI-TRADER - PROCESANDO OPORTUNIDADES")
        print("=" * 70)

        # Trackear trades para Telegram
        trade_actions = {}

        for strategy_id, config in self.strategies.items():
            print(f"\n{config['emoji']} {config['name']}:")
            buys = []

            for opp in opportunities:
                ticker = opp['ticker']

                if self.should_auto_buy(strategy_id, opp):
                    current_price = current_prices.get(ticker)

                    if current_price and current_price > 0:
                        position_id = self.buy_position(strategy_id, opp, current_price)
                        if position_id:
                            print(f"   BUY: {ticker} @ ${current_price:.2f}")
                            # Trackear para Telegram
                            buys.append({
                                'ticker': ticker,
                                'price': current_price,
                                'score': opp.get('score', 0)
                            })

            trade_actions[strategy_id] = {'buys': buys, 'sells': []}
            print(f"   Auto-compras: {len(buys)}")

        print("=" * 70)
        return trade_actions

    def save_portfolio_snapshot(self, strategy: str):
        """Guarda snapshot diario del portfolio de una estrategia"""
        summary = self.get_portfolio_summary(strategy)

        conn = self.get_connection()
        cursor = conn.cursor()

        today = datetime.now().strftime('%Y-%m-%d')

        cursor.execute("""
            INSERT OR REPLACE INTO portfolio_history (
                strategy, date, total_value, cash, invested, total_return_pct, open_positions
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            strategy,
            today,
            summary['total_value'],
            summary['cash'],
            summary['invested'],
            summary['total_return_pct'],
            summary['open_positions']
        ))

        conn.commit()

    def update_positions(self, current_prices: Dict[str, float]):
        """Actualiza posiciones de TODAS las estrategias"""
        print("\n" + "=" * 70)
        print("MULTI-TRADER - ACTUALIZANDO POSICIONES")
        print("=" * 70)

        # Trackear sells para Telegram
        all_sells = {}

        for strategy_id, config in self.strategies.items():
            open_positions = self.get_open_positions(strategy_id)

            if not open_positions:
                continue

            print(f"\n{config['emoji']} {config['name']}: {len(open_positions)} posiciones")
            sells = []

            for position in open_positions:
                ticker = position['ticker']
                current_price = current_prices.get(ticker)

                if current_price is None or current_price <= 0:
                    continue

                exit_reason = self.check_exit_conditions(strategy_id, position, current_price)

                if exit_reason:
                    # Calcular return antes de vender
                    entry_price = position['entry_price']
                    return_pct = ((current_price - entry_price) / entry_price) * 100

                    self.sell_position(strategy_id, position, current_price, exit_reason)

                    # Trackear para Telegram
                    sells.append({
                        'ticker': ticker,
                        'return_pct': return_pct,
                        'reason': exit_reason
                    })

            if len(sells) > 0:
                print(f"   Posiciones cerradas: {len(sells)}")
                all_sells[strategy_id] = sells

            # Guardar snapshot después de actualizar
            self.save_portfolio_snapshot(strategy_id)

        print("=" * 70)
        return all_sells

    def calculate_investment_metrics(self, strategy: str, closed_positions: List[Dict]) -> Dict:
        """
        Calcula métricas investment-grade para una estrategia

        Métricas:
        - Sharpe Ratio: Retorno ajustado por riesgo
        - Max Drawdown: Peor caída desde un pico
        - Profit Factor: Ganancias totales / Pérdidas totales
        - Average Win vs Average Loss
        - Consistency Score: % de meses positivos
        """
        if not closed_positions:
            return {
                'sharpe_ratio': 0,
                'max_drawdown_pct': 0,
                'profit_factor': 0,
                'avg_win_pct': 0,
                'avg_loss_pct': 0,
                'win_loss_ratio': 0,
                'consistency_score': 0
            }

        df = pd.DataFrame(closed_positions)

        # Sharpe Ratio (anualizado)
        # Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns
        # Asumimos risk-free rate = 0 para simplificar
        returns = df['return_pct'].values
        if len(returns) > 1 and returns.std() > 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252 / 30)  # Anualizado
        else:
            sharpe_ratio = 0

        # Max Drawdown
        # Calculado sobre el portfolio value histórico
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, total_value
            FROM portfolio_history
            WHERE strategy = ?
            ORDER BY date
        """, (strategy,))
        history = cursor.fetchall()

        if len(history) > 0:
            values = [h[1] for h in history]
            peak = values[0]
            max_dd = 0

            for value in values:
                if value > peak:
                    peak = value
                dd = ((value - peak) / peak) * 100
                if dd < max_dd:
                    max_dd = dd
        else:
            max_dd = 0

        # Profit Factor
        winning_trades = df[df['profit_usd'] > 0]
        losing_trades = df[df['profit_usd'] <= 0]

        total_wins = winning_trades['profit_usd'].sum() if len(winning_trades) > 0 else 0
        total_losses = abs(losing_trades['profit_usd'].sum()) if len(losing_trades) > 0 else 0

        profit_factor = total_wins / total_losses if total_losses > 0 else (total_wins if total_wins > 0 else 0)

        # Average Win vs Average Loss
        avg_win_pct = winning_trades['return_pct'].mean() if len(winning_trades) > 0 else 0
        avg_loss_pct = losing_trades['return_pct'].mean() if len(losing_trades) > 0 else 0
        win_loss_ratio = abs(avg_win_pct / avg_loss_pct) if avg_loss_pct != 0 else 0

        # Consistency Score (% de trades positivos)
        consistency_score = (len(winning_trades) / len(df)) * 100 if len(df) > 0 else 0

        return {
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_dd,
            'profit_factor': profit_factor,
            'avg_win_pct': avg_win_pct,
            'avg_loss_pct': avg_loss_pct,
            'win_loss_ratio': win_loss_ratio,
            'consistency_score': consistency_score
        }

    def get_portfolio_summary(self, strategy: str) -> Dict:
        """Obtiene resumen de una estrategia con métricas investment-grade"""
        config = self.strategies[strategy]
        conn = self.get_connection()

        open_positions = self.get_open_positions(strategy)

        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM positions WHERE strategy = ? AND status = 'closed'",
            (strategy,)
        )
        closed_positions = [dict(row) for row in cursor.fetchall()]

        current_cash = self.get_current_cash(strategy)
        invested = sum(p['position_value'] for p in open_positions)
        total_value = current_cash + invested

        if closed_positions:
            closed_df = pd.DataFrame(closed_positions)
            total_trades = len(closed_df)
            winning_trades = len(closed_df[closed_df['return_pct'] > 0])
            win_rate = (winning_trades / total_trades) * 100
            avg_return = closed_df['return_pct'].mean()
            total_profit = closed_df['profit_usd'].sum()
        else:
            total_trades = 0
            winning_trades = 0
            win_rate = 0
            avg_return = 0
            total_profit = 0

        total_return_pct = ((total_value - config['initial_capital']) / config['initial_capital']) * 100

        # Calcular métricas investment-grade
        investment_metrics = self.calculate_investment_metrics(strategy, closed_positions)

        return {
            'strategy': strategy,
            'name': config['name'],
            'emoji': config['emoji'],
            'total_value': total_value,
            'cash': current_cash,
            'invested': invested,
            'initial_capital': config['initial_capital'],
            'total_return_pct': total_return_pct,
            'total_profit': total_value - config['initial_capital'],
            'open_positions': len(open_positions),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'total_realized_profit': total_profit,
            # Investment-grade metrics
            'sharpe_ratio': investment_metrics['sharpe_ratio'],
            'max_drawdown_pct': investment_metrics['max_drawdown_pct'],
            'profit_factor': investment_metrics['profit_factor'],
            'avg_win_pct': investment_metrics['avg_win_pct'],
            'avg_loss_pct': investment_metrics['avg_loss_pct'],
            'win_loss_ratio': investment_metrics['win_loss_ratio'],
            'consistency_score': investment_metrics['consistency_score']
        }

    def get_all_summaries(self) -> List[Dict]:
        """Obtiene resúmenes de TODAS las estrategias"""
        summaries = []
        for strategy_id in self.strategies.keys():
            summaries.append(self.get_portfolio_summary(strategy_id))
        return summaries

    def print_comparative_summary(self):
        """Imprime resumen comparativo con métricas investment-grade"""
        summaries = self.get_all_summaries()

        print("\n" + "=" * 70)
        print("MULTI-TRADER - RESUMEN COMPARATIVO")
        print("=" * 70)

        for summary in summaries:
            print(f"\n{summary['emoji']} {summary['name']}:")
            print(f"   Portfolio: ${summary['total_value']:,.2f} ({summary['total_return_pct']:+.2f}%)")
            print(f"   Trades: {summary['total_trades']} | Win Rate: {summary['win_rate']:.1f}%")
            print(f"   Posiciones: {summary['open_positions']} abiertas")

            # Métricas investment-grade (solo si hay trades cerrados)
            if summary['total_trades'] >= 5:
                print(f"   INVESTMENT METRICS:")
                print(f"      Sharpe Ratio: {summary['sharpe_ratio']:.2f}")
                print(f"      Max Drawdown: {summary['max_drawdown_pct']:.2f}%")
                print(f"      Profit Factor: {summary['profit_factor']:.2f}")
                print(f"      Avg Win: {summary['avg_win_pct']:+.2f}% | Avg Loss: {summary['avg_loss_pct']:.2f}%")
                print(f"      Win/Loss Ratio: {summary['win_loss_ratio']:.2f}x")

        # Ranking por performance
        summaries_sorted = sorted(summaries, key=lambda x: x['total_return_pct'], reverse=True)

        print("\n" + "-" * 70)
        print("RANKING POR RETURN:")
        for i, summary in enumerate(summaries_sorted, 1):
            print(f"{i}. {summary['emoji']} {summary['name']}: {summary['total_return_pct']:+.2f}%")

        # Ranking por Sharpe Ratio (solo estrategias con suficientes trades)
        qualified = [s for s in summaries if s['total_trades'] >= 5]
        if qualified:
            qualified_sorted = sorted(qualified, key=lambda x: x['sharpe_ratio'], reverse=True)

            print("\n" + "-" * 70)
            print("RANKING POR SHARPE RATIO (min 5 trades):")
            for i, summary in enumerate(qualified_sorted, 1):
                print(f"{i}. {summary['emoji']} {summary['name']}: {summary['sharpe_ratio']:.2f}")

        # Identificar estrategia(s) que cumplen criterios de inversión real
        print("\n" + "-" * 70)
        print("CRITERIOS PARA DINERO REAL:")
        print("   Win Rate >= 60% | Sharpe >= 1.5 | Max DD <= -15%")
        print()

        investment_ready = []
        for summary in summaries:
            if summary['total_trades'] >= 15:  # Mínimo 15 trades para evaluar
                meets_criteria = (
                    summary['win_rate'] >= 60.0 and
                    summary['sharpe_ratio'] >= 1.5 and
                    summary['max_drawdown_pct'] >= -15.0
                )

                status = "READY" if meets_criteria else "NOT READY"
                print(f"{summary['emoji']} {summary['name']}: {status}")
                print(f"   WR: {summary['win_rate']:.1f}% | Sharpe: {summary['sharpe_ratio']:.2f} | DD: {summary['max_drawdown_pct']:.2f}%")

                if meets_criteria:
                    investment_ready.append(summary)

        if investment_ready:
            print("\n" + "=" * 70)
            print("ESTRATEGIAS LISTAS PARA DINERO REAL:")
            for summary in investment_ready:
                print(f"   {summary['emoji']} {summary['name']}")
            print("=" * 70)
        else:
            print("\n   NINGUNA estrategia cumple criterios todavía.")
            print("   Continúa acumulando datos...")

        print("=" * 70)

    def close(self):
        """Cierra conexión"""
        if self.conn:
            self.conn.close()
            self.conn = None


def main():
    """Test del multi-trader system"""
    print("MULTI-TRADER SYSTEM TEST")
    print("=" * 70)

    mts = MultiTraderSystem()
    mts.print_comparative_summary()
    mts.close()


if __name__ == "__main__":
    main()
