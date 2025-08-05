#!/usr/bin/env python3
"""
RESEARCH ASSISTANT V2
Calcula momentum, stage analysis y risk profiling para insider opportunities
"""
import pandas as pd
import requests
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

class ResearchAssistant:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        
        # Archivos de entrada y salida
        self.opportunities_file = self.data_dir / "insider_opportunities.csv"  # Clusters
        self.whale_file = self.data_dir / "whale_opportunities.csv"           # Whales
        self.research_report = self.data_dir / "weekly_research_report.json"
        self.research_csv = self.data_dir / "weekly_research_report.csv"
        
        # API key
        self.finnhub_key = self.load_api_key()
        
        # Momentum stages configuration
        self.momentum_config = {
            'early_max': 5.0,      # 0-5%: Early stage
            'confirmed_max': 15.0,  # 5-15%: Confirmed stage  
            'late_min': 15.0       # 15%+: Late stage
        }
        
    def load_api_key(self):
        """Carga API key desde archivo o environment variable"""
        import os
        env_key = os.environ.get('FINNHUB_API_KEY')
        if env_key:
            return env_key
        
        key_file = self.data_dir.parent / "finnhub_key.txt"
        if key_file.exists():
            with open(key_file, 'r') as f:
                return f.read().strip()
        
        print("⚠️  No API key found - usando hardcoded")
        return "d28176pr01qr2iau5o4gd28176pr01qr2iau5o50"
    
    def load_opportunities(self):
        """Carga clusters y whales"""
        cluster_data = []
        whale_data = []
        
        # Cargar clusters
        if self.opportunities_file.exists():
            cluster_df = pd.read_csv(self.opportunities_file)
            cluster_data = cluster_df.to_dict('records')
            print(f"📊 Cargadas {len(cluster_data)} cluster opportunities")
        
        # Cargar whales  
        if self.whale_file.exists():
            whale_df = pd.read_csv(self.whale_file)
            whale_data = whale_df.to_dict('records')
            print(f"🐋 Cargadas {len(whale_data)} whale opportunities")
        
        if not cluster_data and not whale_data:
            print(f"❌ No se encontraron datos")
            print(f"💡 Ejecuta primero: python scraper.py")
            return None, None
        
        return cluster_data, whale_data
    
    def enrich_with_market_data(self, all_opportunities):
        """Enriquece con datos de mercado actuales"""
        print(f"📈 Obteniendo precios actuales via Finnhub...")
        
        # Obtener tickers únicos
        tickers = list(set(opp['ticker'] for opp in all_opportunities))
        print(f"🎯 Actualizando {len(tickers)} tickers: {', '.join(tickers[:10])}{'...' if len(tickers) > 10 else ''}")
        
        market_data = {}
        successful_updates = 0
        
        for ticker in tickers:
            try:
                # Obtener quote actual
                quote_data = self.get_stock_quote(ticker)
                
                # Obtener info básica de la empresa
                profile_data = self.get_company_profile(ticker)
                
                if quote_data and profile_data:
                    market_data[ticker] = {
                        'current_price': quote_data.get('c', 0),
                        'prev_close': quote_data.get('pc', 0),
                        'day_change': quote_data.get('d', 0),
                        'day_change_percent': quote_data.get('dp', 0),
                        'market_cap': profile_data.get('marketCapitalization', 0),
                        'pe_ratio': profile_data.get('peNWA', 0),
                        'industry': profile_data.get('finnhubIndustry', 'Unknown'),
                        'sector': profile_data.get('gind', 'Unknown'),
                        '52w_high': quote_data.get('h', 0),
                        '52w_low': quote_data.get('l', 0)
                    }
                    
                    print(f"✅ {ticker}: ${quote_data.get('c', 0):.2f} (PE: {profile_data.get('peNWA', 'N/A')})")
                    successful_updates += 1
                else:
                    print(f"⚠️  {ticker}: No data available")
                
                time.sleep(1.2)  # Rate limiting
                
            except Exception as e:
                print(f"❌ Error con {ticker}: {e}")
        
        print(f"📊 Actualizados: {successful_updates}/{len(tickers)} tickers")
        return market_data
    
    def get_stock_quote(self, ticker):
        """Obtiene quote actual"""
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={self.finnhub_key}"
        response = requests.get(url, timeout=10)
        return response.json() if response.status_code == 200 else None
    
    def get_company_profile(self, ticker):
        """Obtiene perfil de empresa"""
        url = f"https://finnhub.io/api/v1/stock/profile2?symbol={ticker}&token={self.finnhub_key}"
        response = requests.get(url, timeout=10)
        return response.json() if response.status_code == 200 else None
    
    def calculate_momentum_and_stage(self, opportunity, market_data):
        """Calcula momentum y determina stage"""
        ticker = opportunity['ticker']
        
        if ticker not in market_data:
            return None
        
        current_price = market_data[ticker]['current_price']
        if current_price <= 0:
            return None
        
        # Obtener precio de compra insider
        if opportunity['type'] == 'whale':
            insider_price = opportunity['purchase_price']
        else:  # cluster
            insider_price = opportunity['avg_purchase_price']
        
        if insider_price <= 0:
            return None
        
        # Calcular momentum
        momentum_pct = ((current_price - insider_price) / insider_price) * 100
        
        # Determinar stage
        if momentum_pct <= self.momentum_config['early_max']:
            if momentum_pct >= 0:
                stage = 'early_positive'
                stage_desc = 'Early Positive'
                risk_level = 'medium'
            else:
                stage = 'early_negative'  
                stage_desc = 'Early Negative'
                risk_level = 'high'
        elif momentum_pct <= self.momentum_config['confirmed_max']:
            stage = 'confirmed'
            stage_desc = 'Confirmed'
            risk_level = 'medium-low'
        else:
            stage = 'late'
            stage_desc = 'Late Momentum'
            risk_level = 'high'
        
        # Strategy recommendation
        strategy = self.get_strategy_recommendation(stage, momentum_pct, opportunity)
        
        return {
            'current_price': round(current_price, 2),
            'insider_price': round(insider_price, 2),
            'momentum_pct': round(momentum_pct, 2),
            'stage': stage,
            'stage_desc': stage_desc,
            'risk_level': risk_level,
            'strategy': strategy
        }
    
    def get_strategy_recommendation(self, stage, momentum_pct, opportunity):
        """Genera recomendación de strategy basada en stage"""
        opp_type = opportunity['type']
        
        if stage == 'early_positive':
            return {
                'action': 'consider_entry',
                'position_size': 'small_to_medium',
                'stop_loss': '-8%',
                'target': '+15%',
                'reasoning': 'Early validation of insider thesis'
            }
        elif stage == 'early_negative':
            if opp_type == 'whale':
                return {
                    'action': 'strong_consider',
                    'position_size': 'medium',
                    'stop_loss': '-10%',
                    'target': '+20%',
                    'reasoning': 'Whale conviction + discount entry'
                }
            else:
                return {
                    'action': 'caution',
                    'position_size': 'small',
                    'stop_loss': '-8%',
                    'target': '+15%',
                    'reasoning': 'Insiders down money - early or wrong?'
                }
        elif stage == 'confirmed':
            return {
                'action': 'good_entry',
                'position_size': 'medium',
                'stop_loss': '-6%',
                'target': '+12%',
                'reasoning': 'Validated momentum, lower risk'
            }
        else:  # late
            return {
                'action': 'avoid',
                'position_size': 'none',
                'stop_loss': 'n/a',
                'target': 'n/a',
                'reasoning': 'Late entry - limited upside'
            }
    
    def analyze_opportunities(self, cluster_data, whale_data, market_data):
        """Analiza todas las opportunities con momentum"""
        print(f"🧮 Analizando momentum y stages...")
        
        all_enriched = []
        
        # Procesar clusters
        for opp in cluster_data:
            momentum_data = self.calculate_momentum_and_stage(opp, market_data)
            
            if momentum_data:
                enriched = opp.copy()
                enriched.update(momentum_data)
                
                # Agregar datos de mercado
                ticker = opp['ticker']
                if ticker in market_data:
                    market = market_data[ticker]
                    enriched.update({
                        'day_change_pct': round(market['day_change_percent'], 2),
                        'market_cap_millions': round(market['market_cap'], 0),
                        'pe_ratio': round(market['pe_ratio'], 1) if market['pe_ratio'] else None,
                        'industry': market['industry'],
                        '52w_high': market['52w_high'],
                        '52w_low': market['52w_low']
                    })
                    
                    # Calcular distancia desde 52W highs/lows
                    current_price = momentum_data['current_price']
                    if market['52w_high'] > 0:
                        pct_from_high = ((current_price - market['52w_high']) / market['52w_high']) * 100
                    else:
                        pct_from_high = 0
                    
                    if market['52w_low'] > 0:
                        pct_from_low = ((current_price - market['52w_low']) / market['52w_low']) * 100
                    else:
                        pct_from_low = 0
                    
                    enriched.update({
                        'pct_from_52w_high': round(pct_from_high, 1),
                        'pct_from_52w_low': round(pct_from_low, 1)
                    })
                
                # Research signals específicos
                signals = self.generate_research_signals(enriched)
                enriched['research_signals'] = signals
                enriched['analysis_date'] = datetime.now().strftime('%Y-%m-%d')
                
                all_enriched.append(enriched)
        
        # Procesar whales  
        for opp in whale_data:
            momentum_data = self.calculate_momentum_and_stage(opp, market_data)
            
            if momentum_data:
                enriched = opp.copy()
                enriched.update(momentum_data)
                
                # Agregar datos de mercado
                ticker = opp['ticker']
                if ticker in market_data:
                    market = market_data[ticker]
                    enriched.update({
                        'day_change_pct': round(market['day_change_percent'], 2),
                        'market_cap_millions': round(market['market_cap'], 0),
                        'pe_ratio': round(market['pe_ratio'], 1) if market['pe_ratio'] else None,
                        'industry': market['industry'],
                        '52w_high': market['52w_high'],
                        '52w_low': market['52w_low']
                    })
                    
                    # Calcular distancia desde 52W highs/lows
                    current_price = momentum_data['current_price']
                    if market['52w_high'] > 0:
                        pct_from_high = ((current_price - market['52w_high']) / market['52w_high']) * 100
                    else:
                        pct_from_high = 0
                    
                    if market['52w_low'] > 0:
                        pct_from_low = ((current_price - market['52w_low']) / market['52w_low']) * 100
                    else:
                        pct_from_low = 0
                    
                    enriched.update({
                        'pct_from_52w_high': round(pct_from_high, 1),
                        'pct_from_52w_low': round(pct_from_low, 1)
                    })
                
                # Research signals para whales
                signals = self.generate_whale_signals(enriched)
                enriched['research_signals'] = signals
                enriched['analysis_date'] = datetime.now().strftime('%Y-%m-%d')
                
                all_enriched.append(enriched)
        
        return all_enriched
    
    def generate_research_signals(self, opp):
        """Genera señales específicas para clusters"""
        signals = []
        
        # Momentum signal
        momentum = opp['momentum_pct']
        if momentum >= 10:
            signals.append("Strong Momentum")
        elif momentum >= 5:
            signals.append("Positive Momentum")
        elif momentum >= 0:
            signals.append("Early Positive")
        else:
            signals.append("Insiders Down")
        
        # Valuation check
        pe = opp.get('pe_ratio')
        if pe and pe < 15:
            signals.append("Low PE")
        elif pe and pe > 30:
            signals.append("High PE")
        
        # Position vs 52W range
        pct_from_high = opp.get('pct_from_52w_high', 0)
        if pct_from_high > -10:
            signals.append("Near Highs")
        elif pct_from_high < -30:
            signals.append("Deep Discount")
        
        # Market cap category
        market_cap = opp.get('market_cap_millions', 0)
        if market_cap > 50000:
            signals.append("Large Cap")
        elif market_cap > 2000:
            signals.append("Mid Cap")
        else:
            signals.append("Small Cap")
        
        # Freshness
        freshness = opp.get('freshness', 'unknown')
        if freshness == 'fresh':
            signals.append("Fresh Buys")
        elif freshness == 'recent':
            signals.append("Recent Buys")
        
        return ' | '.join(signals)
    
    def generate_whale_signals(self, opp):
        """Genera señales específicas para whales"""
        signals = ["WHALE TRADE"]
        
        # Momentum signal  
        momentum = opp['momentum_pct']
        if momentum >= 15:
            signals.append("Whale Winning Big")
        elif momentum >= 5:
            signals.append("Whale Winning")
        elif momentum >= 0:
            signals.append("Whale Even")
        else:
            signals.append("Whale Down")
        
        # Size category
        value_millions = opp.get('purchase_value_millions', 0)
        if value_millions >= 500:
            signals.append("Mega Whale (500M+)")
        elif value_millions >= 200:
            signals.append("Large Whale (200M+)")
        else:
            signals.append("Standard Whale (99M+)")
        
        # Insider type
        title = opp.get('title', '').lower()
        if 'ceo' in title or 'chief executive' in title:
            signals.append("CEO Trade")
        elif 'founder' in title:
            signals.append("Founder Trade")
        elif '10%' in title:
            signals.append("Major Shareholder")
        
        return ' | '.join(signals)
    
    def generate_research_report(self, enriched_opportunities):
        """Genera reporte final con stage analysis"""
        print(f"📋 Generando reporte con momentum analysis...")
        
        # Separar por tipo y stage
        early_opportunities = [opp for opp in enriched_opportunities if opp['stage'] in ['early_positive', 'early_negative']]
        confirmed_opportunities = [opp for opp in enriched_opportunities if opp['stage'] == 'confirmed']
        late_opportunities = [opp for opp in enriched_opportunities if opp['stage'] == 'late']
        whale_opportunities = [opp for opp in enriched_opportunities if opp['type'] == 'whale']
        cluster_opportunities = [opp for opp in enriched_opportunities if opp['type'] == 'cluster']
        
        # Ordenar por momentum
        early_opportunities.sort(key=lambda x: x['momentum_pct'], reverse=True)
        confirmed_opportunities.sort(key=lambda x: x['momentum_pct'], reverse=True)
        whale_opportunities.sort(key=lambda x: x['momentum_pct'], reverse=True)
        
        # Crear reporte estructurado
        report = {
            'generation_date': datetime.now().isoformat(),
            'summary': {
                'total_opportunities': len(enriched_opportunities),
                'whale_opportunities': len(whale_opportunities),
                'cluster_opportunities': len(cluster_opportunities),
                'early_stage': len(early_opportunities),
                'confirmed_stage': len(confirmed_opportunities),
                'late_stage': len(late_opportunities),
                'avg_momentum': round(sum(opp['momentum_pct'] for opp in enriched_opportunities) / len(enriched_opportunities), 1) if enriched_opportunities else 0
            },
            'stage_buckets': {
                'early_opportunities': early_opportunities[:10],
                'confirmed_opportunities': confirmed_opportunities[:10],
                'late_opportunities': late_opportunities[:5]
            },
            'type_buckets': {
                'whale_opportunities': whale_opportunities[:5],
                'top_cluster_opportunities': cluster_opportunities[:10]
            },
            'top_research_targets': sorted(enriched_opportunities, key=lambda x: x.get('score', 0) if x['type'] == 'cluster' else x.get('whale_score', 0), reverse=True)[:15]
        }
        
        # Guardar JSON completo
        with open(self.research_report, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Guardar CSV simple para Excel
        df_research = pd.DataFrame(enriched_opportunities)
        df_research.to_csv(self.research_csv, index=False)
        
        print(f"💾 Reporte guardado: {self.research_report}")
        print(f"💾 CSV research: {self.research_csv}")
        
        return report
    
    def print_research_summary(self, report):
        """Imprime resumen ejecutivo con stages"""
        summary = report['summary']
        
        print(f"\n📊 RESEARCH REPORT V2 - {datetime.now().strftime('%Y-%m-%d')}")
        print("=" * 70)
        
        print(f"🎯 OVERVIEW:")
        print(f"   Total opportunities: {summary['total_opportunities']}")
        print(f"   🐋 Whales: {summary['whale_opportunities']} | 📊 Clusters: {summary['cluster_opportunities']}")
        print(f"   📈 Avg momentum: {summary['avg_momentum']}%")
        
        print(f"\n📈 STAGE ANALYSIS:")
        print(f"   🟢 Early stage: {summary['early_stage']} (high risk/reward)")
        print(f"   🟡 Confirmed stage: {summary['confirmed_stage']} (moderate risk)")
        print(f"   🔴 Late stage: {summary['late_stage']} (avoid)")
        
        print(f"\n🐋 TOP WHALE OPPORTUNITIES:")
        for i, opp in enumerate(report['type_buckets']['whale_opportunities'][:3], 1):
            print(f"{i}. {opp['ticker']}: {opp['insider_name']}")
            print(f"   ${opp['purchase_value_millions']}M @ ${opp['insider_price']} → ${opp['current_price']} ({opp['momentum_pct']:+.1f}%)")
            print(f"   Stage: {opp['stage_desc']} | Action: {opp['strategy']['action']}")
            print()
        
        print(f"📊 TOP CLUSTER OPPORTUNITIES:")
        for i, opp in enumerate(report['stage_buckets']['confirmed_opportunities'][:3], 1):
            price_change = opp['momentum_pct']
            print(f"{i}. {opp['ticker']}: {opp['insider_count']} insiders")
            print(f"   ${opp['avg_purchase_price']:.2f} → ${opp['current_price']:.2f} ({price_change:+.1f}%)")
            print(f"   Stage: {opp['stage_desc']} | Action: {opp['strategy']['action']}")
            print()

def main():
    """Función principal"""
    print("🔬 RESEARCH ASSISTANT V2")
    print("=" * 50)
    
    assistant = ResearchAssistant()
    
    # 1. Cargar opportunities (clusters + whales)
    cluster_data, whale_data = assistant.load_opportunities()
    if cluster_data is None and whale_data is None:
        sys.exit(1)
    
    # Combinar para market data fetch
    all_opportunities = (cluster_data or []) + (whale_data or [])
    
    # 2. Enriquecer con datos de mercado
    market_data = assistant.enrich_with_market_data(all_opportunities)
    
    # 3. Analizar momentum y stages
    enriched_opportunities = assistant.analyze_opportunities(cluster_data or [], whale_data or [], market_data)
    
    # 4. Generar reporte
    report = assistant.generate_research_report(enriched_opportunities)
    
    # 5. Mostrar resumen
    assistant.print_research_summary(report)
    
    print(f"\n✅ RESEARCH ASSISTANT V2 COMPLETADO")
    print(f"📁 Revisa: {assistant.research_csv}")
    print(f"🎯 Próximo paso: Revisar stage buckets para strategy")

if __name__ == "__main__":
    main()