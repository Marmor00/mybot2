#!/usr/bin/env python3
"""
MULTI-TRADER REPORT GENERATOR
Genera reporte JSON con métricas comparativas de las 5 estrategias
"""
import json
import sys
from pathlib import Path

# Agregar directorio core al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
from multi_trader import MultiTraderSystem


def generate_multi_trader_report():
    """Genera reporte completo del multi-trader"""

    mts = MultiTraderSystem()
    summaries = mts.get_all_summaries()

    # Preparar datos para JSON
    report = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'strategies': []
    }

    for summary in summaries:
        strategy_data = {
            'id': summary['strategy'],
            'name': summary['name'],
            'emoji': summary['emoji'],
            'portfolio': {
                'total_value': summary['total_value'],
                'cash': summary['cash'],
                'invested': summary['invested'],
                'initial_capital': summary['initial_capital'],
                'total_return_pct': summary['total_return_pct'],
                'total_profit': summary['total_profit']
            },
            'trading': {
                'open_positions': summary['open_positions'],
                'total_trades': summary['total_trades'],
                'winning_trades': summary['winning_trades'],
                'losing_trades': summary['losing_trades'],
                'win_rate': summary['win_rate'],
                'avg_return': summary['avg_return'],
                'total_realized_profit': summary['total_realized_profit']
            },
            'investment_metrics': {
                'sharpe_ratio': summary['sharpe_ratio'],
                'max_drawdown_pct': summary['max_drawdown_pct'],
                'profit_factor': summary['profit_factor'],
                'avg_win_pct': summary['avg_win_pct'],
                'avg_loss_pct': summary['avg_loss_pct'],
                'win_loss_ratio': summary['win_loss_ratio'],
                'consistency_score': summary['consistency_score']
            },
            'ready_for_real_money': False
        }

        # Evaluar si cumple criterios para dinero real
        if summary['total_trades'] >= 15:
            meets_criteria = (
                summary['win_rate'] >= 60.0 and
                summary['sharpe_ratio'] >= 1.5 and
                summary['max_drawdown_pct'] >= -15.0
            )
            strategy_data['ready_for_real_money'] = meets_criteria

        report['strategies'].append(strategy_data)

    # Ordenar por performance
    report['strategies'] = sorted(
        report['strategies'],
        key=lambda x: x['portfolio']['total_return_pct'],
        reverse=True
    )

    # Guardar JSON
    output_file = Path('data/multi_trader_report.json')
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"OK: Reporte generado: {output_file}")

    mts.close()
    return report


if __name__ == "__main__":
    import pandas as pd
    generate_multi_trader_report()
