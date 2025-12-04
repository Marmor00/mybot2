# Progressive Income Trading System

**Status:** Month 0 - Sistema Multi-Trader Operacional
**Next:** Month 1 - Insider Track Record + ATR Exits
**Goal:** $100 → $1,000 MXN/month en 6 meses (paper trading)

---

## Quick Start

### Ver estado actual
```bash
cd c:\Users\MM\expedientes-app\trading\Bot2
python core/multi_trader.py
```

### Ejecutar pipeline diario (manual)
```bash
python core/daily_scraper.py
```

### Ejecutar sin alertas Telegram
```bash
python core/daily_scraper.py --no-alerts
```

### Generar reporte para dashboard
```bash
python scripts/multi_trader_report.py
# Luego abrir: templates/multi_trader_dashboard.html
```

### Automatización
El sistema corre automáticamente a las 6 PM diario:
```bash
python scripts/auto_scheduler.py
```
Deja esta terminal abierta en segundo plano

---

## Estructura del Proyecto

```
Bot2/
├── core/                    # Sistema principal (ACTIVO)
│   ├── daily_scraper.py    # Pipeline principal
│   ├── multi_trader.py     # 5 estrategias paralelas
│   ├── telegram_bot.py     # Sistema de alertas
│   ├── scraper.py          # Scraping SEC
│   ├── asistente.py        # Research assistant
│   ├── database.py         # SQLite wrapper
│   ├── insider_tracker.py  # Pattern tracking
│   └── config.py           # Configuración
│
├── layers/                  # Capas progresivas (PENDIENTES)
│   ├── insider_track_record.py    # Month 1
│   ├── options_income.py          # Month 2
│   ├── convergence_detector.py    # Month 3
│   ├── ml_classifier.py           # Month 4
│   ├── portfolio_optimizer.py     # Month 5
│   └── performance_analyzer.py    # Month 6
│
├── scripts/                 # Automatización
│   ├── auto_scheduler.py
│   ├── multi_trader_report.py
│   └── setup/              # Scripts de instalación Windows
│
├── docs/                    # Documentación
│   ├── PROGRESSIVE_INCOME_PLAN.md      # ⭐ PLAN MAESTRO (leer primero)
│   ├── PROMPT_PROXIMA_SESION.md        # ⭐ CONTEXTO para Claude
│   ├── MULTI_TRADER_INTEGRATION.md
│   └── QUICK_START_MULTI_TRADER.md
│
├── data/                    # Bases de datos
│   ├── multi_trader.db
│   ├── multi_trader_report.json
│   └── insider_data.db
│
├── logs/                    # Logs del sistema
├── templates/               # Web dashboards
├── config/                  # API keys, env vars
└── requirements.txt
```

---

## Sistema Actual: Multi-Trader (5 Estrategias)

| ID | Estrategia | Filtros | Capital |
|----|-----------|---------|---------|
| UC | Ultra Conservative | Score ≥90, Mom ≥4% | $10,000 |
| BO | Balanced Optimal | Score ≥80, Mom ≥2.5% | $10,000 |
| MH | Momentum Hunter | Score ≥75, Mom ≥6% | $10,000 |
| ES | Early Stage Master | Score ≥78, Stage: early | $10,000 |
| DP | Diversified Portfolio | Score ≥75, Max 15 pos | $10,000 |

**Total:** $50,000 virtuales (paper trading)

---

## Roadmap de 6 Meses

| Mes | Layer | Objetivo | Status |
|-----|-------|----------|--------|
| **1** | Insider Track Record + ATR Exits | $100-200 MXN/mes | 🔜 NEXT |
| **2** | Options Income (CSPs/CCs) | $300-500 MXN/mes | ⏸️ Pending |
| **3** | Convergence Signals (13F + Options) | $500-700 MXN/mes | ⏸️ Pending |
| **4** | ML Classification | $600-900 MXN/mes | ⏸️ Pending |
| **5** | Portfolio Optimization (Kelly) | $700-1,000 MXN/mes | ⏸️ Pending |
| **6** | Scaling & Elimination | $800-1,200 MXN/mes | ⏸️ Pending |

**Filosofía:** "Zero Feelings" - Data-driven. Si no funciona → ELIMINAR.

---

## Next Steps (Month 1, Week 1)

1. **Instalar dependencias:**
   ```bash
   pip install sec-edgar-downloader pandas-ta
   ```

2. **Crear:** `layers/insider_track_record.py`
   - Descargar Form 4 históricos (12 meses)
   - Calcular win rate por insider
   - Filtrar solo WR ≥60%

3. **Modificar:** `core/multi_trader.py`
   - Integrar filtro de track record
   - Agregar columna `insider_historical_wr` en opportunities

4. **Criterio de éxito:**
   - DB con ≥500 insiders
   - Win rate promedio ~55-58%
   - Filtro funcional reduce opportunities ~40-50%

---

## Documentación Clave

- **[PROGRESSIVE_INCOME_PLAN.md](docs/PROGRESSIVE_INCOME_PLAN.md)** - Plan completo de 6 meses
- **[PROMPT_PROXIMA_SESION.md](docs/PROMPT_PROXIMA_SESION.md)** - Contexto para Claude
- **[MULTI_TRADER_INTEGRATION.md](docs/MULTI_TRADER_INTEGRATION.md)** - Cómo funciona el sistema actual

---

## Filosofía "Zero Feelings"

1. **Data over intuition** - Si no funciona → ELIMINAR
2. **Walk-forward only** - Nunca optimizar en datos ya vistos
3. **Real costs always** - Comisiones, slippage, impuestos
4. **Small sample = no decision** - Necesitas 100+ trades
5. **Kill your darlings** - Si no agrega edge en 2 meses → ELIMINAR
6. **Progressive growth** - $100 → $1,000 es VICTORIA
7. **One change at a time** - Un layer/mes → medir → iterar

---

## Reglas para Dinero Real

Solo considerar después de 6 meses SI:
- ✅ Win rate ≥ 62%
- ✅ Sharpe ratio ≥ 1.5
- ✅ Max drawdown ≤ -15%
- ✅ Mínimo 100 trades

Si NO cumple → NO invertir dinero real. Y eso está OK.

---

**Última actualización:** 2025-12-04
**Autor:** MM
**Stack:** Python, SQLite, Telegram, yfinance, SEC EDGAR
