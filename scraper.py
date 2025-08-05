#!/usr/bin/env python3
"""
INTELLIGENT INSIDER SCRAPER V2
Detecta patrones de acumulación + whale trades con análisis de momentum
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import re
from collections import defaultdict
import sys

class IntelligentInsiderScraper:
    def __init__(self, output_dir="data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Ubicaciones fijas
        self.raw_csv = self.output_dir / "insider_trades_raw.csv"
        self.filtered_csv = self.output_dir / "insider_opportunities.csv"
        self.whale_csv = self.output_dir / "whale_opportunities.csv"
        
        # Configuración inteligente
        self.config = {
            'days_back': 60,           # Extendido para whales
            'min_purchase_value': 500000,  # $500K mínimo individual cluster
            'min_cluster_value': 1500000,  # $1.5M mínimo cluster
            'whale_threshold': 99000000,   # $99M para whale trades
            'max_pe_ratio': 25,        # No overvalued stocks
            'min_market_cap': 500000000,   # $500M mínimo
            'max_market_cap': 50000000000, # $50B máximo
            'min_daily_volume': 100000,    # 100K shares liquidity
        }
        
        # Insiders relevantes (C-suite only)
        self.relevant_insiders = [
            'ceo', 'chief executive', 'founder', 'co-founder',
            'cfo', 'chief financial', 'president', 'chairman', 
            'chair', '10%'  # 10% shareholders
        ]
        
        # Whale-only insiders (más restrictivo)
        self.whale_insiders = [
            'ceo', 'chief executive', 'founder', 'co-founder', '10%'
        ]
        
    def scrape_recent_insider_data(self):
        """Scrape datos con ventana extendida para whales"""
        print(f"🔍 Scraping últimos {self.config['days_back']} días...")
        
        # Fechas
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.config['days_back'])
        
        start_str = start_date.strftime('%m/%d/%Y')
        end_str = end_date.strftime('%m/%d/%Y')
        
        print(f"📅 Período: {start_str} a {end_str}")
        
        # URL con filtros para solo compras
        url = f'http://openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh=&fd=-1&fdr={start_str}+-+{end_str}&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&xs=1&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=2000&page=1'
        
        try:
            print("📡 Descargando datos...")
            response = requests.get(url, timeout=45)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'class': 'tinytable'})
            
            if not table:
                raise Exception("No se encontró tabla de datos")
                
            tbody = table.find('tbody')
            rows = tbody.find_all('tr')
            
            print(f"📊 Filas raw encontradas: {len(rows)}")
            
            # Extraer y limpiar datos
            data = []
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 13:
                    continue
                    
                # Extraer datos limpios
                row_data = {}
                
                # Campos básicos
                row_data['filing_date'] = self._clean_text(cols[1])
                row_data['trade_date'] = self._clean_text(cols[2])
                row_data['ticker'] = self._clean_text(cols[3]).upper()
                row_data['company_name'] = self._clean_text(cols[4])
                row_data['insider_name'] = self._clean_text(cols[5])
                row_data['title'] = self._clean_text(cols[6])
                row_data['transaction_type'] = self._clean_text(cols[7])
                
                # Campos numéricos - LIMPIEZA CRÍTICA
                row_data['price'] = self._clean_numeric(cols[8])  # PRECIO DE COMPRA INSIDER
                row_data['qty'] = self._clean_numeric(cols[9])
                row_data['shares_owned'] = self._clean_numeric(cols[10])
                row_data['ownership_change'] = self._clean_percent(cols[11])
                row_data['transaction_value'] = self._clean_numeric(cols[12])
                
                # Calcular días desde trade
                row_data['days_since_trade'] = self._calculate_days_since(row_data['trade_date'])
                
                # Solo procesar si tenemos datos válidos
                if (row_data['ticker'] and 
                    row_data['transaction_value'] != 0 and
                    row_data['qty'] != 0 and
                    row_data['price'] > 0):  # Precio válido crítico
                    data.append(row_data)
            
            print(f"✅ Datos limpios extraídos: {len(data)} transacciones")
            
            # Crear DataFrame
            df = pd.DataFrame(data)
            
            # Guardar datos raw
            df.to_csv(self.raw_csv, index=False)
            print(f"💾 Datos raw guardados: {self.raw_csv}")
            
            return df
            
        except Exception as e:
            print(f"❌ ERROR scraping: {e}")
            return None
    
    def _calculate_days_since(self, trade_date_str):
        """Calcula días desde el trade"""
        try:
            trade_date = datetime.strptime(trade_date_str, '%Y-%m-%d')
            return (datetime.now() - trade_date).days
        except:
            return 999  # Fecha inválida
    
    def _clean_text(self, cell):
        """Limpia texto de celdas HTML"""
        link = cell.find('a')
        text = link.text.strip() if link else cell.text.strip()
        return text
    
    def _clean_numeric(self, cell):
        """Limpia valores numéricos - MANEJA SÍMBOLOS"""
        text = self._clean_text(cell)
        if not text or text.lower() in ['n/a', 'new', '']:
            return 0.0
        
        # Remover símbolos comunes: $, +, -, ,, espacios
        clean = re.sub(r'[\$\,\s]', '', text)
        
        # Manejar signo negativo
        is_negative = clean.startswith('-')
        if is_negative:
            clean = clean[1:]
        elif clean.startswith('+'):
            clean = clean[1:]
            
        try:
            value = float(clean)
            return -value if is_negative else value
        except ValueError:
            return 0.0
    
    def _clean_percent(self, cell):
        """Limpia porcentajes"""
        text = self._clean_text(cell)
        if not text or text.lower() in ['n/a', 'new']:
            return 0.0
            
        # Remover % y otros símbolos
        clean = re.sub(r'[\%\,\s]', '', text)
        
        is_negative = clean.startswith('-')
        if is_negative:
            clean = clean[1:]
        elif clean.startswith('+'):
            clean = clean[1:]
            
        try:
            value = float(clean)
            return -value if is_negative else value
        except ValueError:
            return 0.0
    
    def detect_whale_trades(self, df):
        """Detecta whale trades ($99M+)"""
        print(f"\n🐋 Detectando WHALE TRADES...")
        
        # Filtros para whales
        whale_df = df[
            (abs(df['transaction_value']) >= self.config['whale_threshold']) &
            (df['transaction_type'].str.contains('P - Purchase', na=False)) &
            (df['title'].str.lower().str.contains('|'.join(self.whale_insiders), na=False)) &
            (df['ticker'].str.len().between(1, 5)) &
            (df['price'] > 0)  # Precio válido
        ].copy()
        
        print(f"🐋 Whale trades encontrados: {len(whale_df)}")
        
        # Preparar datos whale
        whale_opportunities = []
        
        for _, row in whale_df.iterrows():
            # Clasificar freshness
            days = row['days_since_trade']
            if days <= 7:
                freshness = 'fresh'
                freshness_score = 30
            elif days <= 21:
                freshness = 'recent'
                freshness_score = 20
            else:
                freshness = 'old'
                freshness_score = 10
            
            # Clasificar confidence
            title = row['title'].lower()
            if any(word in title for word in ['ceo', 'chief executive', 'founder', 'co-founder']):
                confidence = 'high'
                confidence_score = 30
            elif '10%' in title:
                confidence = 'high'
                confidence_score = 25
            else:
                confidence = 'medium'
                confidence_score = 15
            
            # Score whale
            whale_score = min(
                40 +  # Base whale score
                freshness_score +
                confidence_score,
                100
            )
            
            whale_opp = {
                'type': 'whale',
                'ticker': row['ticker'],
                'company_name': row['company_name'],
                'insider_name': row['insider_name'],
                'title': row['title'],
                'purchase_value_usd': int(abs(row['transaction_value'])),
                'purchase_value_millions': round(abs(row['transaction_value'])/1000000, 1),
                'purchase_price': round(row['price'], 2),
                'purchase_date': row['trade_date'],
                'days_since_trade': days,
                'freshness': freshness,
                'confidence': confidence,
                'whale_score': round(whale_score, 1),
                'qty_purchased': int(row['qty']) if row['qty'] > 0 else 0
            }
            
            whale_opportunities.append(whale_opp)
        
        # Ordenar por score y guardar
        whale_opportunities.sort(key=lambda x: x['whale_score'], reverse=True)
        
        if whale_opportunities:
            whale_df_final = pd.DataFrame(whale_opportunities)
            whale_df_final.to_csv(self.whale_csv, index=False)
            print(f"💾 Whale opportunities guardadas: {self.whale_csv}")
            
            # Mostrar top whales
            print(f"\n🏆 TOP WHALE TRADES:")
            for i, whale in enumerate(whale_opportunities[:3], 1):
                print(f"{i}. {whale['ticker']}: {whale['insider_name']} "
                      f"(${whale['purchase_value_millions']}M @ ${whale['purchase_price']}) "
                      f"Score: {whale['whale_score']}")
        
        return whale_opportunities
    
    def apply_intelligent_filters(self, df):
        """Aplica filtros inteligentes para clusters (no whales)"""
        print(f"\n🧠 Aplicando filtros para CLUSTER DETECTION...")
        print(f"📊 Datos iniciales: {len(df)} transacciones")
        
        original_count = len(df)
        
        # 1. Solo compras (P - Purchase)
        df = df[df['transaction_type'].str.contains('P - Purchase', na=False)]
        print(f"✅ Solo compras: {len(df)} ({len(df)/original_count*100:.1f}%)")
        
        # 2. Valor mínimo pero NO whale threshold
        min_value = self.config['min_purchase_value']
        max_value = self.config['whale_threshold'] - 1  # Excluir whales
        df = df[
            (abs(df['transaction_value']) >= min_value) & 
            (abs(df['transaction_value']) < max_value)
        ]
        print(f"✅ Valor ${min_value/1000000:.1f}M-${max_value/1000000:.0f}M: {len(df)} transacciones")
        
        # 3. Solo insiders relevantes (C-suite)
        df = df[df['title'].str.lower().str.contains('|'.join(self.relevant_insiders), na=False)]
        print(f"✅ Solo C-suite: {len(df)} transacciones")
        
        # 4. Filtrar tickers válidos
        df = df[df['ticker'].str.len().between(1, 5)]
        print(f"✅ Tickers válidos: {len(df)} transacciones")
        
        # 5. Precio válido
        df = df[df['price'] > 0]
        print(f"✅ Precios válidos: {len(df)} transacciones")
        
        # 6. Eliminar duplicados exactos
        df = df.drop_duplicates(subset=['ticker', 'insider_name', 'trade_date', 'transaction_value'])
        print(f"✅ Sin duplicados: {len(df)} transacciones")
        
        return df
    
    def detect_cluster_buying(self, df):
        """Detecta patrones de cluster buying (múltiples insiders)"""
        print(f"\n🎯 Detectando CLUSTER BUYING patterns...")
        
        # Agrupar por ticker
        clusters = defaultdict(list)
        
        for _, row in df.iterrows():
            ticker = row['ticker']
            clusters[ticker].append({
                'insider': row['insider_name'],
                'title': row['title'],
                'value': abs(row['transaction_value']),
                'price': row['price'],  # PRECIO DE COMPRA CRÍTICO
                'date': row['trade_date'],
                'days_since': row['days_since_trade'],
                'qty': row['qty']
            })
        
        # Analizar clusters
        cluster_results = []
        
        for ticker, purchases in clusters.items():
            if len(purchases) >= 1:  # Al menos 1 compra
                total_value = sum(p['value'] for p in purchases)
                insider_count = len(set(p['insider'] for p in purchases))
                
                # Calcular precio promedio ponderado por valor
                total_purchase_value = sum(p['value'] for p in purchases)
                weighted_price = sum(p['price'] * p['value'] for p in purchases) / total_purchase_value
                
                # Días desde última compra
                latest_date = max(p['date'] for p in purchases)
                days_since_latest = min(p['days_since'] for p in purchases)
                
                # Clasificar freshness del cluster
                if days_since_latest <= 7:
                    freshness = 'fresh'
                elif days_since_latest <= 21:
                    freshness = 'recent'
                else:
                    freshness = 'old'
                
                # Calcular score
                score = self._calculate_cluster_score(purchases, total_value, insider_count, days_since_latest)
                
                cluster_results.append({
                    'type': 'cluster',
                    'ticker': ticker,
                    'insider_count': insider_count,
                    'total_value': total_value,
                    'avg_value': total_value / len(purchases),
                    'avg_purchase_price': round(weighted_price, 2),  # PRECIO PROMEDIO PONDERADO
                    'latest_purchase': latest_date,
                    'days_since_latest': days_since_latest,
                    'freshness': freshness,
                    'score': score,
                    'purchases': purchases
                })
        
        # Ordenar por score
        cluster_results.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"📈 Clusters detectados: {len(cluster_results)}")
        
        # Mostrar top clusters
        print(f"\n🏆 TOP CLUSTERS:")
        for i, cluster in enumerate(cluster_results[:5], 1):
            print(f"{i}. {cluster['ticker']}: {cluster['insider_count']} insiders, "
                  f"${cluster['total_value']/1000000:.1f}M @ ${cluster['avg_purchase_price']:.2f} avg "
                  f"(Score: {cluster['score']:.1f})")
        
        return cluster_results
    
    def _calculate_cluster_score(self, purchases, total_value, insider_count, days_since):
        """Calcula score realista para cluster con freshness"""
        score = 0
        
        # 1. Valor total (0-25 puntos)
        if total_value >= 5000000:      # $5M+
            score += 25
        elif total_value >= 2000000:    # $2M+
            score += 20
        elif total_value >= 1000000:    # $1M+
            score += 15
        elif total_value >= 500000:     # $500K+
            score += 10
        
        # 2. Cluster effect (0-25 puntos)
        if insider_count >= 3:
            score += 25
        elif insider_count >= 2:
            score += 20
        else:
            score += 10  # Single insider
        
        # 3. Insider quality (0-25 puntos)
        max_insider_score = 0
        for purchase in purchases:
            title = purchase['title'].lower()
            if any(word in title for word in ['ceo', 'chief executive']):
                max_insider_score = max(max_insider_score, 25)
            elif any(word in title for word in ['cfo', 'chief financial']):
                max_insider_score = max(max_insider_score, 20)
            elif any(word in title for word in ['founder', 'co-founder']):
                max_insider_score = max(max_insider_score, 25)
            elif '10%' in title:
                max_insider_score = max(max_insider_score, 20)
            elif any(word in title for word in ['president', 'chairman']):
                max_insider_score = max(max_insider_score, 15)
            else:
                max_insider_score = max(max_insider_score, 8)
        
        score += max_insider_score
        
        # 4. Freshness bonus (0-25 puntos) - MÁS IMPORTANTE
        if days_since <= 7:
            score += 25  # Fresh
        elif days_since <= 14:
            score += 20  # Recent
        elif days_since <= 21:
            score += 15  # Still good
        elif days_since <= 30:
            score += 10  # Getting old
        else:
            score += 5   # Old
        
        return min(score, 100)
    
    def save_opportunities(self, clusters):
        """Guarda oportunidades cluster filtradas"""
        opportunities = []
        
        for cluster in clusters:
            if cluster['score'] >= 50:  # Threshold mínimo
                # Crear registro detallado
                opp = {
                    'type': 'cluster',
                    'ticker': cluster['ticker'],
                    'score': round(cluster['score'], 1),
                    'insider_count': cluster['insider_count'],
                    'total_value_usd': int(cluster['total_value']),
                    'total_value_millions': round(cluster['total_value']/1000000, 1),
                    'avg_purchase_value': int(cluster['avg_value']),
                    'avg_purchase_price': cluster['avg_purchase_price'],  # PRECIO PROMEDIO
                    'latest_purchase': cluster['latest_purchase'],
                    'days_since_latest': cluster['days_since_latest'],
                    'freshness': cluster['freshness']
                }
                
                # Agregar detalles de insiders
                insiders_detail = []
                for purchase in cluster['purchases']:
                    insiders_detail.append(f"{purchase['insider']} ({purchase['title']}: ${purchase['value']/1000000:.1f}M @ ${purchase['price']:.2f})")
                
                opp['insiders_detail'] = ' | '.join(insiders_detail)
                opportunities.append(opp)
        
        # Guardar CSV
        if opportunities:
            df_opp = pd.DataFrame(opportunities)
            df_opp.to_csv(self.filtered_csv, index=False)
            print(f"💾 Cluster opportunities guardadas: {self.filtered_csv}")
            print(f"🎯 Total cluster opportunities: {len(opportunities)}")
        else:
            print("⚠️  No se encontraron cluster opportunities que cumplan criterios")
        
        return opportunities

def main():
    """Función principal"""
    print("🚀 INTELLIGENT INSIDER SCRAPER V2")
    print("=" * 60)
    
    scraper = IntelligentInsiderScraper()
    
    # 1. Scraping básico
    df = scraper.scrape_recent_insider_data()
    if df is None:
        print("❌ SCRAPING FALLIDO")
        sys.exit(1)
    
    # 2. Detectar WHALE TRADES primero
    whale_opportunities = scraper.detect_whale_trades(df)
    
    # 3. Filtros para CLUSTERS (excluye whales)
    df_filtered = scraper.apply_intelligent_filters(df)
    
    # 4. Detección de CLUSTERS
    clusters = scraper.detect_cluster_buying(df_filtered)
    
    # 5. Guardar cluster opportunities
    cluster_opportunities = scraper.save_opportunities(clusters)
    
    print(f"\n✅ SCRAPER V2 COMPLETADO")
    print(f"🐋 Whale trades: {len(whale_opportunities)}")
    print(f"📊 Cluster opportunities: {len(cluster_opportunities)}")
    print(f"📁 Datos raw: {scraper.raw_csv}")
    print(f"📁 Clusters: {scraper.filtered_csv}")
    print(f"📁 Whales: {scraper.whale_csv}")
    print(f"🎯 Siguiente paso: Ejecutar asistente_v2.py para momentum analysis")

if __name__ == "__main__":
    main()