#!/usr/bin/env python3
"""
DAILY SCRAPER WITH NEW OPPORTUNITY DETECTION
Ejecuta scraping + detección de compras NUEVAS + alertas Telegram
"""
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import sys

# Importar módulos existentes
from scraper import IntelligentInsiderScraper
from asistente import ResearchAssistant
from telegram_bot import TelegramBot
from config import Config
from database import Database
from insider_tracker import InsiderTracker
# from paper_trading import PaperTradingSystem  # Removed - using multi_trader only
from multi_trader import MultiTraderSystem

class DailyScraper:
    def __init__(self):
        self.scraper = IntelligentInsiderScraper()
        self.assistant = ResearchAssistant()
        self.telegram = TelegramBot()
        self.config = Config

        # Database y tracker
        self.db = Database()
        self.tracker = InsiderTracker(self.db)

        # Paper trading systems
        # self.paper_trading = PaperTradingSystem()  # Sistema original (mantener compatibilidad)
        self.multi_trader = MultiTraderSystem()     # Sistema multi-trader (5 estrategias)

        # Archivos
        self.previous_scrape_file = Config.FILES['previous_scrape']
        self.new_opportunities_file = Config.FILES['new_opportunities']

    def load_previous_scrape(self):
        """Carga datos del scrape anterior para comparación"""
        if not self.previous_scrape_file.exists():
            print("WARNING: No hay scrape anterior. Este sera el primero.")
            return None

        try:
            df = pd.read_csv(self.previous_scrape_file)
            print(f"Scrape anterior cargado: {len(df)} transacciones")
            return df
        except Exception as e:
            print(f"ERROR: Error cargando scrape anterior: {e}")
            return None

    def save_current_scrape(self, df):
        """Guarda scrape actual como referencia para próxima ejecución"""
        try:
            df.to_csv(self.previous_scrape_file, index=False)
            print(f" Scrape actual guardado para comparación futura")
        except Exception as e:
            print(f"ERROR: Error guardando scrape actual: {e}")

    def detect_new_opportunities(self, current_df, previous_df):
        """Detecta oportunidades NUEVAS comparando con scrape anterior"""
        print("\n Detectando NUEVAS oportunidades...")

        if previous_df is None:
            print("WARNING: Primer scrape - todas las oportunidades son nuevas")
            return current_df

        # Crear key única para cada transacción
        def create_key(row):
            return f"{row['ticker']}_{row['insider_name']}_{row['trade_date']}_{row['transaction_value']}"

        current_df['key'] = current_df.apply(create_key, axis=1)
        previous_df['key'] = previous_df.apply(create_key, axis=1)

        # Encontrar transacciones nuevas
        previous_keys = set(previous_df['key'].values)
        new_trades = current_df[~current_df['key'].isin(previous_keys)].copy()

        print(f" Nuevas transacciones detectadas: {len(new_trades)}")

        return new_trades

    def classify_by_freshness(self, opportunities):
        """Clasifica opportunities por freshness"""
        freshness_buckets = {
            'hot': [],      # 0-3 días
            'fresh': [],    # 4-7 días
            'recent': [],   # 8-14 días
            'old': []       # 15+ días
        }

        for opp in opportunities:
            days = opp.get('days_since_latest') or opp.get('days_since_trade', 999)

            if days <= Config.FRESHNESS_CONFIG['hot_max_days']:
                freshness_buckets['hot'].append(opp)
                opp['freshness_level'] = 'hot'
            elif days <= Config.FRESHNESS_CONFIG['fresh_max_days']:
                freshness_buckets['fresh'].append(opp)
                opp['freshness_level'] = 'fresh'
            elif days <= Config.FRESHNESS_CONFIG['recent_max_days']:
                freshness_buckets['recent'].append(opp)
                opp['freshness_level'] = 'recent'
            else:
                freshness_buckets['old'].append(opp)
                opp['freshness_level'] = 'old'

        return freshness_buckets

    def send_alerts(self, new_opportunities, new_exits):
        """Envía alertas Telegram para oportunidades nuevas"""
        if not self.telegram.enabled:
            print("WARNING: Telegram no configurado - saltando alertas")
            return

        print("\n Enviando alertas Telegram...")

        alerts_sent = 0

        # Separar por tipo
        whales = [opp for opp in new_opportunities if opp.get('type') == 'whale']
        clusters = [opp for opp in new_opportunities if opp.get('type') == 'cluster']

        # Alertas de Whales
        for whale in whales:
            value_usd = whale.get('purchase_value_usd', 0)
            if value_usd >= Config.ALERT_THRESHOLDS['whale_min_value']:
                self.telegram.send_whale_alert(whale)
                alerts_sent += 1

        # Alertas de Clusters
        for cluster in clusters:
            insider_count = cluster.get('insider_count', 0)
            days = cluster.get('days_since_latest', 999)

            if (insider_count >= Config.ALERT_THRESHOLDS['cluster_min_insiders'] and
                days <= Config.ALERT_THRESHOLDS['cluster_timeframe_days']):
                self.telegram.send_cluster_alert(cluster)
                alerts_sent += 1

        # Alertas de Exits
        for exit_info in new_exits:
            sale_value = exit_info.get('sale_value', 0)
            if sale_value >= Config.ALERT_THRESHOLDS['exit_alert_min_value']:
                self.telegram.send_exit_alert(exit_info)
                alerts_sent += 1

        print(f"OK: {alerts_sent} alertas enviadas a Telegram")

    def save_trades_to_database(self, df):
        """Guarda nuevos trades en la base de datos SQLite"""
        print("\n Guardando trades en base de datos...")

        inserted = 0
        duplicates = 0

        for _, row in df.iterrows():
            try:
                self.db.insert_trade(
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
                    scrape_date=datetime.now().strftime('%Y-%m-%d')
                )
                inserted += 1
            except Exception as e:
                # Probablemente duplicado
                duplicates += 1
                continue

        self.db.get_connection().commit()

        print(f"   OK: Insertados: {inserted}")
        print(f"     Duplicados: {duplicates}")

        return inserted

    def enrich_with_track_records(self, opportunities):
        """Enriquece oportunidades con track records de insiders"""
        print("\nEnriqueciendo con track records de insiders...")

        enriched_count = 0

        for opp in opportunities:
            # Para whales: un solo insider
            if opp.get('type') == 'whale':
                insider_name = opp.get('insider_name')
                if insider_name:
                    try:
                        track_record = self.tracker.calculate_track_record(insider_name)
                        opp['insider_track_record'] = track_record
                        enriched_count += 1
                    except Exception as e:
                        print(f"   WARNING: Error calculando track record para {insider_name}: {e}")
                        opp['insider_track_record'] = None

            # Para clusters: track record del insider principal (primer comprador)
            elif opp.get('type') == 'cluster':
                # Tomar el primer insider del cluster como representativo
                insiders_detail = opp.get('insiders_detail', '')
                if insiders_detail:
                    # Parsear primer insider del detail
                    first_insider = insiders_detail.split('|')[0].split('(')[0].strip()
                    try:
                        track_record = self.tracker.calculate_track_record(first_insider)
                        opp['insider_track_record'] = track_record
                        enriched_count += 1
                    except Exception as e:
                        print(f"   WARNING: Error calculando track record para {first_insider}: {e}")
                        opp['insider_track_record'] = None

        print(f"   OK: Oportunidades enriquecidas: {enriched_count}/{len(opportunities)}")

        return opportunities

    def get_current_prices(self, opportunities):
        """Obtiene precios actuales para todas las oportunidades"""
        import requests

        print("\nObteniendo precios actuales para paper trading...")

        tickers = list(set([opp['ticker'] for opp in opportunities]))
        prices = {}

        for ticker in tickers:
            try:
                url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={Config.FINNHUB_API_KEY}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                current_price = data.get('c', None)  # current price

                if current_price and current_price > 0:
                    prices[ticker] = current_price

            except Exception as e:
                print(f"   WARNING: No se pudo obtener precio para {ticker}: {e}")
                continue

        print(f"   Precios obtenidos: {len(prices)}/{len(tickers)}")
        return prices

    def save_new_opportunities_report(self, new_opportunities, freshness_buckets):
        """Guarda reporte de nuevas oportunidades"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_new': len(new_opportunities),
            'freshness_breakdown': {
                'hot': len(freshness_buckets['hot']),
                'fresh': len(freshness_buckets['fresh']),
                'recent': len(freshness_buckets['recent']),
                'old': len(freshness_buckets['old'])
            },
            'new_opportunities': new_opportunities,
            'hot_opportunities': freshness_buckets['hot']
        }

        with open(self.new_opportunities_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f" Reporte de nuevas oportunidades guardado: {self.new_opportunities_file}")

    def run_daily_pipeline(self, send_telegram_alerts=True):
        """Pipeline completo diario"""
        print("DAILY SCRAPER V1 - NEW OPPORTUNITY DETECTION")
        print("=" * 70)
        print(f" Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 1. Cargar scrape anterior para comparación
        previous_df = self.load_previous_scrape()

        # 2. Ejecutar scraper actual
        print("\n PASO 1: Scraping datos actuales...")
        current_df = self.scraper.scrape_recent_insider_data()

        if current_df is None:
            print("ERROR: Scraping fallo")
            return False

        # 3. Detectar transacciones NUEVAS
        new_trades_df = self.detect_new_opportunities(current_df, previous_df)

        # 4. Guardar scrape actual como referencia
        self.save_current_scrape(current_df)

        # 5. Detectar ventas (sales)
        print("\n PASO 2: Detectando ventas de insiders...")
        all_sales = self.scraper.detect_insider_sales(current_df)

        # Detectar ventas NUEVAS
        new_sales = []
        if previous_df is not None:
            previous_sales = self.scraper.detect_insider_sales(previous_df)
            previous_sale_keys = set([f"{s['ticker']}_{s['insider_name']}_{s['sale_date']}" for s in previous_sales])
            new_sales = [s for s in all_sales if f"{s['ticker']}_{s['insider_name']}_{s['sale_date']}" not in previous_sale_keys]
            print(f" Nuevas ventas detectadas: {len(new_sales)}")
        else:
            new_sales = all_sales

        # 6. Detectar whale trades
        print("\n PASO 3: Detectando whale trades...")
        whale_opportunities = self.scraper.detect_whale_trades(current_df)

        # 7. Detectar clusters
        print("\n PASO 4: Detectando cluster buying...")
        df_filtered = self.scraper.apply_intelligent_filters(current_df)
        clusters = self.scraper.detect_cluster_buying(df_filtered)
        cluster_opportunities = self.scraper.save_opportunities(clusters)

        # 8. Exit tracking
        print("\n PASO 5: Exit tracking...")
        exit_tracking = self.scraper.track_exits(cluster_opportunities, whale_opportunities, all_sales)

        # Detectar exits NUEVOS
        new_exits = []
        if len(new_sales) > 0:
            # Los exits nuevos son aquellos relacionados con ventas nuevas
            new_exit_keys = set([f"{s['ticker']}_{s['insider_name']}" for s in new_sales])
            new_exits = [e for e in exit_tracking if f"{e['ticker']}_{e['insider_name']}" in new_exit_keys]
            print(f" Nuevos exits detectados: {len(new_exits)}")

        # 9. Guardar trades nuevos en base de datos
        if len(new_trades_df) > 0:
            print("\n PASO 6: Guardando trades en base de datos...")
            self.save_trades_to_database(new_trades_df)

        # 10. Ejecutar research assistant (enriquecer con momentum)
        print("\n PASO 7: Enriqueciendo con datos de mercado...")
        all_opportunities = cluster_opportunities + whale_opportunities
        market_data = self.assistant.enrich_with_market_data(all_opportunities)
        enriched_opportunities = self.assistant.analyze_opportunities(
            cluster_opportunities, whale_opportunities, market_data
        )

        # 11. Enriquecer con track records de insiders
        enriched_opportunities = self.enrich_with_track_records(enriched_opportunities)

        # 12. MULTI-TRADER - Procesar con las 5 estrategias
        print("\n" + "=" * 70)
        print("MULTI-TRADER SYSTEM (5 Strategies)")
        print("=" * 70)

        # Obtener precios actuales
        current_prices = self.get_current_prices(enriched_opportunities)

        # Procesar nuevas oportunidades para auto-compra (5 estrategias)
        multi_buys = self.multi_trader.process_opportunities(enriched_opportunities, current_prices)
        multi_sells = self.multi_trader.update_positions(current_prices)
        self.multi_trader.print_comparative_summary()

        # Combinar buys y sells para Telegram
        multi_trade_actions = {}
        for strategy_id in multi_buys.keys():
            multi_trade_actions[strategy_id] = {
                'buys': multi_buys.get(strategy_id, {}).get('buys', []),
                'sells': multi_sells.get(strategy_id, [])
            }

        # 13. Generar reporte
        report = self.assistant.generate_research_report(enriched_opportunities)

        # 14. Clasificar por freshness
        print("\nClasificando por freshness...")
        freshness_buckets = self.classify_by_freshness(enriched_opportunities)

        print(f"\n HOT (0-3 días): {len(freshness_buckets['hot'])}")
        print(f"OK: FRESH (4-7 dias): {len(freshness_buckets['fresh'])}")
        print(f"WARNING: RECENT (8-14 dias): {len(freshness_buckets['recent'])}")
        print(f"  OLD (15+ días): {len(freshness_buckets['old'])}")

        # 15. Identificar oportunidades NUEVAS de hoy
        # Las nuevas son aquellas que están en new_trades_df
        new_trade_keys = set([f"{row['ticker']}_{row['insider_name']}" for _, row in new_trades_df.iterrows()])

        new_opportunities = []
        for opp in enriched_opportunities:
            ticker = opp['ticker']
            # Para clusters, verificar si alguno de los insiders es nuevo
            if opp.get('type') == 'cluster':
                # Simplificado: si el ticker aparece en new_trades, considerarlo nuevo
                if any(ticker in key for key in new_trade_keys):
                    new_opportunities.append(opp)
            else:  # whale
                insider = opp.get('insider_name', '')
                key = f"{ticker}_{insider}"
                if any(key in tk for tk in new_trade_keys):
                    new_opportunities.append(opp)

        print(f"\n NUEVAS OPORTUNIDADES DETECTADAS: {len(new_opportunities)}")

        # 16. Guardar reporte de nuevas oportunidades
        self.save_new_opportunities_report(new_opportunities, freshness_buckets)

        # 17. Enviar alertas Telegram
        if send_telegram_alerts and (len(new_opportunities) > 0 or len(new_exits) > 0):
            self.send_alerts(new_opportunities, new_exits)

            # Enviar resumen diario
            summary_data = {
                'new_whales': len([o for o in new_opportunities if o.get('type') == 'whale']),
                'new_clusters': len([o for o in new_opportunities if o.get('type') == 'cluster']),
                'new_exits': len(new_exits),
                'hot_opportunities': freshness_buckets['hot']
            }
            self.telegram.send_daily_summary(summary_data)

        # 17b. Enviar alertas multi-trader si hubo trades
        if send_telegram_alerts:
            self.telegram.send_multi_trader_summary(multi_trade_actions)

        # 18. Resumen final
        print("\n" + "=" * 70)
        print("DAILY SCRAPER COMPLETADO")
        print("=" * 70)
        print(f"Total oportunidades: {len(enriched_opportunities)}")
        print(f"Nuevas oportunidades: {len(new_opportunities)}")
        print(f"HOT opportunities: {len(freshness_buckets['hot'])}")
        print(f"Nuevos exits: {len(new_exits)}")
        print(f"Alertas enviadas: {'Si' if send_telegram_alerts else 'No'}")
        print()

        print(f"Datos guardados en: {Config.DATA_DIR}")
        print(f"Abre dashboard para ver resultados")
        print()

        # 19. Generar reporte JSON para multi-trader dashboard
        self.generate_multi_trader_json()

        # Cerrar conexiones
        self.multi_trader.close()

        return True

    def generate_multi_trader_json(self):
        """Genera JSON para el dashboard multi-trader"""
        import pandas as pd

        summaries = self.multi_trader.get_all_summaries()

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

            # Evaluar si cumple criterios
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
        output_file = Config.DATA_DIR / 'multi_trader_report.json'

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"OK: Multi-trader report saved: {output_file}")


def main():
    """Función principal"""
    import argparse

    parser = argparse.ArgumentParser(description='Daily Insider Scraper with Alerts')
    parser.add_argument('--no-alerts', action='store_true', help='Deshabilitar alertas Telegram')
    args = parser.parse_args()

    scraper = DailyScraper()
    success = scraper.run_daily_pipeline(send_telegram_alerts=not args.no_alerts)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
