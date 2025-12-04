# PROGRESSIVE INCOME SYSTEM - "Zero Feelings" Approach

**Creado:** 2025-12-04
**Filosofía:** Build what WORKS, not what sounds good
**Objetivo:** $100 → $1,000 MXN/month en 6 meses (progresivo, realista)

---

## CONTEXTO: ¿POR QUÉ ESTE PLAN?

### Problema Identificado con Enfoque Original
El sistema multi-trader actual tiene estas limitaciones científicas:

1. **Edge débil**: Insider trading solo = ~52-58% win rate histórico
2. **Overfitting**: 5 estrategias optimizadas en datos conocidos
3. **Exit ingenuo**: 30 días fijos ignora volatilidad
4. **Costos ignorados**: No cuenta comisiones ni slippage
5. **Sample size**: 30 días insuficiente (necesitas 200-300 trades)

### Nuevo Enfoque: Progressive Edges
En vez de depender de UN solo edge (insider trading), construir CAPAS de ventajas:

```
Layer 1: Insider Mejorado (track record + ATR exits)
Layer 2: Options Income (theta decay consistente)
Layer 3: Convergence Signals (insider + 13F + unusual options)
Layer 4: ML Classification (filtrar señales de calidad)
Layer 5: Portfolio Optimization (Kelly criterion, correlaciones)
```

**Resultado esperado:** Edge combinado ~62-68% win rate + income estable

---

## ROADMAP DE 6 MESES

### MONTH 1: Critical Fixes & Validation
**Objetivo:** $100-200 MXN/month | Validar si insider tiene edge REAL

#### Week 1-2: Insider Track Record
**Implementar:**
- Scraping histórico de insiders (últimos 12 meses)
- Cálculo de win rate por insider individual
- Filtro: Solo seguir insiders con WR ≥ 60% en último año

**Herramienta:** `sec-edgar-downloader` (open source)
```python
from sec_edgar_downloader import Downloader

# Descargar Form 4 (insider trades) históricos
dl = Downloader("MyCompany", "email@example.com")
dl.get("4", ticker="AAPL", after="2024-01-01", before="2025-01-01")
```

**Archivo nuevo:** `insider_track_record.py`
- Parse Form 4 XMLs descargados
- Calcular win rate individual (compra → precio +30d)
- Guardar en DB: `insiders` table con columna `historical_win_rate`

**Métricas de éxito:**
- Base de datos con ≥500 insiders y sus track records
- Filtro funcional en `multi_trader.py`: `insider_wr >= 0.60`

---

#### Week 3-4: ATR-Based Exits + Real Costs
**Implementar:**
- Reemplazar hold fijo (30 días) con stops adaptativos (ATR)
- Agregar costos reales: $6.95 comisión + 0.15% slippage

**ATR (Average True Range):**
```python
import pandas_ta as ta

# ATR = 14-day average de true range
df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

# Stop loss dinámico: -2 * ATR desde entry
stop_loss = entry_price - (2 * current_atr)

# Take profit: +3 * ATR
take_profit = entry_price + (3 * current_atr)
```

**Archivo a modificar:** `multi_trader.py`
- Método: `check_exit_conditions()` → agregar lógica ATR
- Método: `buy_position()` → restar comisión ($6.95) del cash
- Método: `sell_position()` → restar comisión + slippage (0.15%)

**Métricas de éxito:**
- Exits adaptativos a volatilidad (Tesla exit más rápido que Walmart)
- Costos reflejados en returns (portfolio value más conservador)

---

### MONTH 2: Options Income Layer
**Objetivo:** $300-500 MXN/month | Agregar flujo consistente de theta decay

#### Estrategia: Cash-Secured Puts + Covered Calls
**Concepto:**
- Vender puts en tickers que QUIERES comprar (si asignan = bought at discount)
- Vender calls cubiertos en posiciones existentes (collect premium)

**Ejemplo Real:**
```
Capital disponible: $2,000 USD
1. Vender CSP: AAPL $180 put @ $3.00 premium (30 DTE)
   - Collect: $300 USD
   - Si asignan → compras AAPL @ $180 (descuento)
   - Si expiran OTM → keeps premium ($300)

2. Si tienes 100 shares AAPL @ $185:
   - Vender CC: AAPL $195 call @ $2.00 premium
   - Collect: $200 USD
   - Si ejercen → vendes @ $195 (ganancia cap gains + premium)
```

**Herramienta:** `yfinance` (ya lo usas) + manual execution (Interactive Brokers)

**Archivo nuevo:** `options_income.py`
- Identificar tickers con alto IV pero fundamentals sólidos
- Calcular delta óptimo (~0.30 delta para CSPs, 0.30 para CCs)
- Sugerir strikes/expirations óptimos
- Track premiums collected

**Criterios:**
- Solo vender puts en stocks con score ≥80
- Solo tickers con volumen de opciones ≥1,000 contratos/día
- Evitar earnings weeks (IV crush)

**Métricas de éxito:**
- Sistema recomienda 5-10 CSPs/semana
- Tracking de premium income mensual
- Win rate ≥ 70% (mayoría expiran OTM)

---

### MONTH 3: Convergence Signals
**Objetivo:** $500-700 MXN/month | Aumentar edge con señales convergentes

#### Agregar 13F Filings + Unusual Options Activity
**Concepto:** Las señales MÁS fuertes son cuando MÚLTIPLES fuentes convergen:
- Insider BUY + 13F institutional BUY + Unusual call activity = HIGH CONVICTION

**13F Filings:**
- Instituciones con ≥$100M AUM reportan holdings cada trimestre
- Si Citadel, Bridgewater, Renaissance compran = strong signal

**Herramienta:** `sec-edgar-downloader` (same as Month 1)
```python
# Descargar 13F-HR filings
dl.get("13F-HR", ticker="AAPL", after="2024-10-01")

# Parse XML → extraer:
# - Institution name
# - Shares held
# - Change vs previous quarter (+/-)
```

**Unusual Options Activity:**
- Call/Put ratio anormal
- Volumen >> Open Interest
- Premium inusualmente grande

**Herramienta:** `unusual-whales-python` (open source API wrapper)
```python
from unusual_whales import UnusualWhales

uw = UnusualWhales(api_key="your_key")
unusual = uw.option_activity(ticker="AAPL", min_premium=100000)
```

**Archivo nuevo:** `convergence_detector.py`
- Función: `detect_convergence(ticker)` → score 0-100
  - +30 pts: Insider buy (high WR insider)
  - +30 pts: 13F institutional buy (≥2 big players)
  - +20 pts: Unusual call activity (volume > 5x avg)
  - +20 pts: Positive momentum (≥3%)

**Modificar:** `multi_trader.py`
- Agregar filtro: `convergence_score >= 70` para Ultra Conservative
- Agregar filtro: `convergence_score >= 50` para otras estrategias

**Métricas de éxito:**
- Sistema detecta 3-7 convergencias/semana
- Win rate de convergencias ≥ 65%

---

### MONTH 4: ML Classification (Not Prediction!)
**Objetivo:** $600-900 MXN/month | Usar ML para filtrar CALIDAD de señales

#### Importante: ML NO predice precio, FILTRA señales
**Mal uso de ML:** "Predecir si AAPL subirá 10%"
**Buen uso de ML:** "Clasificar si esta oportunidad es High/Medium/Low quality"

**Features a usar:**
```python
# Insider characteristics
- insider_track_record (win rate histórico)
- position (CEO=1, CFO=0.8, Director=0.5)
- transaction_size_usd
- days_since_transaction

# Market characteristics
- momentum_pct
- relative_strength_index (RSI)
- volume_vs_avg
- price_vs_52w_high

# Convergence
- convergence_score (from Month 3)
- num_institutional_buyers
- unusual_options_score

# Historical
- sector_performance_30d
- correlation_to_spy
```

**Target Variable:**
- Binary: `is_winner` (1 if return > +15% in 30d, else 0)

**Modelo:** Random Forest Classifier (scikit-learn)
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# Train en datos históricos (últimos 12 meses)
X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.3)

model = RandomForestClassifier(n_estimators=100, max_depth=8)
model.fit(X_train, y_train)

# Predict probability de éxito
prob_success = model.predict_proba(new_opportunity)[1]

# Solo trade si prob >= 0.65
if prob_success >= 0.65:
    buy()
```

**Archivo nuevo:** `ml_classifier.py`
- Función: `train_model()` → entrena con últimos 12 meses
- Función: `classify_opportunity(opp)` → retorna prob_success
- Función: `retrain_monthly()` → walk-forward optimization

**Critical: Avoid Overfitting**
- Walk-forward validation: Train en Mes 1-6, test en Mes 7
- Never train y test en mismo período
- Re-entrenar cada mes con nuevos datos

**Métricas de éxito:**
- Modelo con AUC ≥ 0.65 en validation set
- Filtro funcional: Solo trades con ML prob ≥ 65%
- Win rate post-ML ≥ 68%

---

### MONTH 5: Portfolio Optimization
**Objetivo:** $700-1,000 MXN/month | Optimizar position sizing y diversificación

#### Kelly Criterion + Correlation-Aware Sizing
**Kelly Criterion:**
```python
# Formula: f* = (p*b - q) / b
# f* = fracción óptima de capital
# p = probabilidad de ganar
# b = win/loss ratio (avg_win / avg_loss)
# q = 1 - p

# Ejemplo:
p = 0.65  # 65% win rate
avg_win = 0.18  # +18% average
avg_loss = 0.08  # -8% average
b = avg_win / avg_loss  # 2.25

kelly_fraction = (p * b - (1 - p)) / b
# kelly_fraction ≈ 0.41 (41% de capital)

# CRITICAL: Use Half-Kelly (más conservador)
position_size = kelly_fraction * 0.5  # 20.5%
```

**Correlation-Aware Sizing:**
- Si tienes AAPL, reduce size en MSFT (tech correlation alta)
- Si tienes XOM, ok full size en JPM (sectores no correlacionados)

```python
import pandas as pd

# Calcular matriz de correlación
returns = pd.DataFrame({
    'AAPL': aapl_returns,
    'MSFT': msft_returns,
    'XOM': xom_returns
})

corr_matrix = returns.corr()

# Si correlation > 0.7 → reduce size
if corr_matrix['AAPL']['MSFT'] > 0.7:
    msft_size *= 0.5
```

**Archivo nuevo:** `portfolio_optimizer.py`
- Función: `calculate_kelly_size(win_rate, avg_win, avg_loss)` → optimal %
- Función: `adjust_for_correlation(positions, new_ticker)` → adjusted %
- Modificar: `multi_trader.buy_position()` → usar kelly size instead of fixed 10%

**Métricas de éxito:**
- Position sizing dinámico (winners get bigger size)
- Reducción de drawdown por correlación (evitar sector concentration)
- Sharpe ratio mejora ≥ 0.3 puntos

---

### MONTH 6: Scaling & Refinement
**Objetivo:** $800-1,200 MXN/month | Escalar lo que funciona, eliminar lo que no

#### Focus: Data-Driven Elimination
**Revisar cada layer:**
1. **Insider Layer:** ¿Win rate real ≥ 60% post-costs?
   - SI → Keep, aumentar allocation
   - NO → Reduce peso o eliminar

2. **Options Income:** ¿Premium collection consistente?
   - SI → Aumentar a 30% de estrategia
   - NO → Solo usar en alta volatilidad

3. **Convergence:** ¿Convergence signals outperform insider solo?
   - SI → Require convergence_score ≥ 60 para todos
   - NO → Usar solo como tie-breaker

4. **ML Classifier:** ¿AUC ≥ 0.65 consistente?
   - SI → Aumentar threshold a prob ≥ 0.70
   - NO → Simplificar features o eliminar

**Actividades:**
- A/B testing: Mes con ML vs mes sin ML
- Backtest walk-forward: 6 meses de datos reales
- Calcular Sharpe, Sortino, Calmar ratios
- Identificar mejor estrategia de las 5 (o crear 6ta híbrida)

**Archivo nuevo:** `performance_analyzer.py`
- Función: `compare_strategies(period='6M')` → tabla comparativa
- Función: `attribution_analysis()` → ¿Qué layer aporta más edge?
- Función: `optimize_strategy_weights()` → Si BO outperforms UC, aumentar peso

**Deliverable Final:**
- Documento: `6_MONTH_RESULTS.md`
  - Win rate real de cada estrategia
  - Income mensual promedio
  - Mejor estrategia identificada
  - Recomendación: ¿Listo para dinero real? ¿Cuánto?

---

## PROYECCIÓN DE INCOME (Conservadora)

| Mes | Layers Activos | Income Esperado (MXN) | Notas |
|-----|----------------|----------------------|-------|
| 1 | Insider mejorado | $100-200 | Track record + ATR exits |
| 2 | + Options income | $300-500 | CSPs en 2-3 tickers/semana |
| 3 | + Convergence | $500-700 | Solo high-conviction signals |
| 4 | + ML filter | $600-900 | Reduce false positives |
| 5 | + Kelly sizing | $700-1,000 | Optimize winners |
| 6 | Scaling | $800-1,200 | Scale best performers |

**Total acumulado 6 meses:** ~$3,200-4,200 MXN
**Average mensual final:** ~$800-1,000 MXN

**Con capital inicial $20K MXN:**
- Mes 1-2: Returns ~5-10%/mes → $100-200
- Mes 3-4: Returns ~8-12%/mes → $500-900
- Mes 5-6: Returns ~10-15%/mes → $800-1,200

---

## HERRAMIENTAS OPEN SOURCE A INTEGRAR

### Mes 1-2:
- `sec-edgar-downloader` - Download SEC filings
- `pandas-ta` - Technical indicators (ATR, RSI, etc.)

### Mes 3:
- `unusual-whales-python` - Unusual options API wrapper
- `beautifulsoup4` - Parse 13F XMLs

### Mes 4:
- `scikit-learn` - Random Forest Classifier
- `xgboost` - (opcional) Gradient boosting
- `mlflow` - Track model performance

### Mes 5-6:
- `pyfolio` - Portfolio analytics (Sharpe, drawdown, etc.)
- `cvxpy` - Portfolio optimization (correlaciones)

**Total costo herramientas:** $0 (todo open source)
**Único costo:** Unusual Whales API ~$50 USD/month (opcional, hay alternativas gratis)

---

## CRITERIOS DE ÉXITO POR MES

### Mes 1: Validation
- [ ] Insider track record DB con ≥500 insiders
- [ ] ATR exits implementados y funcionando
- [ ] Costos reales reflejados (comisión + slippage)
- [ ] Win rate ≥ 55% (mejor que random, peor que objetivo)
- [ ] Income: $100-200 MXN

### Mes 2: Income Layer
- [ ] Sistema options_income.py funcional
- [ ] 5-10 CSP suggestions/semana
- [ ] Premium collected ≥ $50 USD/mes
- [ ] Income: $300-500 MXN

### Mes 3: Convergence
- [ ] 13F parser funcional (top 20 instituciones)
- [ ] Unusual options integrado
- [ ] Convergence score 0-100 calculado
- [ ] Win rate convergencias ≥ 65%
- [ ] Income: $500-700 MXN

### Mes 4: ML
- [ ] Random Forest con AUC ≥ 0.65
- [ ] Walk-forward validation implementado
- [ ] Win rate post-ML ≥ 68%
- [ ] Income: $600-900 MXN

### Mes 5: Optimization
- [ ] Kelly sizing implementado
- [ ] Correlation matrix funcional
- [ ] Sharpe ratio aumenta ≥ 0.3
- [ ] Income: $700-1,000 MXN

### Mes 6: Scaling
- [ ] 6 meses de track record real
- [ ] Estrategia ganadora identificada
- [ ] Decision: ¿Dinero real? ¿Cuánto?
- [ ] Income: $800-1,200 MXN

---

## CRITICAL: "ZERO FEELINGS" RULES

### Rule 1: Data Over Intuition
Si los datos dicen que insider trading no funciona → ELIMINAR.
No defender una idea porque "suena bien" o "debería funcionar".

### Rule 2: Walk-Forward Only
NUNCA optimizar en datos que ya viste.
Train en Mes 1-6, test en Mes 7. Siempre forward.

### Rule 3: Real Costs Always
Comisiones, slippage, spreads, impuestos.
Si ignoras costos, estás mintiendo.

### Rule 4: Small Sample = No Decision
15 trades NO son suficientes para decidir.
Necesitas 100+ trades (6 meses) antes de conclusiones.

### Rule 5: Kill Your Darlings
Si un layer NO agrega edge después de 2 meses → ELIMINAR.
No acumular complejidad sin retorno.

### Rule 6: Progressive Growth
No esperar $10,000/mes en Mes 1.
$100 → $200 → $500 → $1,000 es VICTORIA.

### Rule 7: One Change at a Time
No agregar ML + Options + Kelly en mismo mes.
Un cambio/mes → medir impacto → iterar.

---

## INTEGRACIÓN CON SISTEMA ACTUAL

### ¿Qué MANTENER del multi-trader?
- ✅ Framework de 5 estrategias paralelas
- ✅ Base de datos SQLite
- ✅ Dashboard comparativo
- ✅ Telegram alerts
- ✅ Portfolio tracking

### ¿Qué MODIFICAR?
- 🔧 Filtros de cada estrategia (agregar layers progresivamente)
- 🔧 Exit conditions (de fixed days → ATR-based)
- 🔧 Position sizing (de fixed 10% → Kelly)
- 🔧 Costs (agregar comisiones/slippage)

### ¿Qué AGREGAR?
- ➕ `insider_track_record.py` (Mes 1)
- ➕ `options_income.py` (Mes 2)
- ➕ `convergence_detector.py` (Mes 3)
- ➕ `ml_classifier.py` (Mes 4)
- ➕ `portfolio_optimizer.py` (Mes 5)
- ➕ `performance_analyzer.py` (Mes 6)

### Arquitectura Final (Mes 6):
```
daily_scraper.py
├── insider_track_record.py (filter insiders con WR ≥ 60%)
├── convergence_detector.py (13F + unusual options)
├── ml_classifier.py (classify opportunity quality)
├── multi_trader.py (5 strategies con layers)
│   ├── Ultra Conservative (insider + convergence + ML + kelly)
│   ├── Balanced Optimal (insider + ML + kelly)
│   ├── Momentum Hunter (insider + kelly)
│   ├── Early Stage Master (insider + convergence)
│   └── Diversified Portfolio (insider + options income)
├── options_income.py (CSP/CC suggestions)
├── portfolio_optimizer.py (kelly + correlation)
└── performance_analyzer.py (attribution + comparison)
```

---

## PRÓXIMA SESIÓN: START MONTH 1

**Tareas inmediatas:**
1. Instalar `sec-edgar-downloader`:
   ```bash
   pip install sec-edgar-downloader
   ```

2. Crear `insider_track_record.py`:
   - Descargar Form 4s (últimos 12 meses)
   - Parse XMLs → extraer trades
   - Calcular win rate por insider
   - Guardar en DB

3. Modificar `multi_trader.py`:
   - Agregar filtro: `insider_wr >= 0.60`
   - Agregar columna en opportunities: `insider_track_record`

4. Test con datos reales:
   - Ejecutar scraping histórico (1 ticker test)
   - Validar cálculo de win rate
   - Verificar filtro funciona

**Comando para siguiente sesión:**
```bash
python insider_track_record.py --ticker AAPL --lookback 12M
```

**Métrica de éxito Sesión 1:**
- DB con track records de ≥50 insiders (test)
- Win rate promedio calculado (~55-58% esperado)
- Filtro reduce oportunidades en ~40-50%

---

## FILOSOFÍA FINAL

Este plan NO promete:
- ❌ Hacerte rico rápido
- ❌ 100% win rate
- ❌ Sistema "secreto" que nadie conoce
- ❌ Eliminar riesgo

Este plan SÍ promete:
- ✅ Enfoque científico (data-driven)
- ✅ Crecimiento progresivo ($100 → $1,000)
- ✅ Honestidad brutal (si no funciona, eliminar)
- ✅ Aprendizaje real sobre trading algorítmico
- ✅ Sistema útil que PUEDE generar income suplementario

**Si después de 6 meses win rate < 55% → El sistema NO funciona.**
**Y eso está BIEN. Aprendiste qué NO hacer.**

**Si después de 6 meses win rate ≥ 62% → Tienes algo real.**
**Entonces SÍ considerar dinero real (empezando con $5K, no $50K).**

---

**NEXT STEP:** Month 1, Week 1 → Insider Track Record System

Let's build something USEFUL. 🚀
