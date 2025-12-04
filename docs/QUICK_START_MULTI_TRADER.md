# 🚀 QUICK START - Multi-Trader System

## VER DASHBOARD

### Opción 1: Dashboard Interactivo (Recomendado)
```bash
# 1. Generar reporte actual
python multi_trader_report.py

# 2. Abrir en navegador
templates/multi_trader_dashboard.html
```

### Opción 2: Ver en Consola
```bash
python multi_trader.py
```

---

## CÓMO FUNCIONA

### Sistema Automático (6 PM diario)
El script `auto_scheduler.py` ejecuta **automáticamente**:
1. Scraping de insider trades
2. Detección de oportunidades
3. **Multi-trader evalúa con 5 estrategias**
4. Alertas Telegram
5. Actualización dashboard

**No necesitas hacer nada.** El sistema corre solo.

---

## LAS 5 ESTRATEGIAS

| Estrategia | Emoji | Filosofía | Filtros Clave |
|-----------|-------|-----------|---------------|
| Ultra Conservative | [UC] | Calidad > Cantidad | Score ≥90, Momentum ≥4% |
| Balanced Optimal | [BO] | Balance óptimo | Score ≥80, Momentum ≥2.5% |
| Momentum Hunter | [MH] | Momentum fuerte | Score ≥75, Momentum ≥6% |
| Early Stage Master | [ES] | Early stage crítico | Score ≥78, Solo early_positive |
| Diversified Portfolio | [DP] | Más trades pequeños | Score ≥75, 15 posiciones max |

---

## CRITERIOS PARA DINERO REAL

Una estrategia está **lista para inversión real** cuando:

✅ Mínimo **15 trades** cerrados
✅ **Win Rate ≥ 60%**
✅ **Sharpe Ratio ≥ 1.5**
✅ **Max Drawdown ≤ -15%**

**Si NINGUNA cumple → NO invertir.**

---

## ARCHIVOS IMPORTANTES

```
multi_trader.py                      # Sistema base
multi_trader_report.py               # Generador reporte
templates/multi_trader_dashboard.html # Dashboard web
data/multi_trader.db                 # Base de datos SQLite
data/multi_trader_report.json        # Datos para dashboard
```

---

## COMANDOS ÚTILES

### Ver resumen actual
```bash
python multi_trader.py
```

### Generar reporte JSON
```bash
python multi_trader_report.py
```

### Ejecutar pipeline completo manualmente
```bash
python daily_scraper.py
```

### Ver qué estrategia va ganando
```bash
python multi_trader.py | findstr "RANKING"
```

---

## MÉTRICAS EXPLICADAS

### Sharpe Ratio
- **Qué es:** Retorno ajustado por riesgo
- **Bueno:** > 1.5
- **Excelente:** > 2.0

### Max Drawdown
- **Qué es:** Peor caída desde un pico
- **Bueno:** > -15%
- **Excelente:** > -10%

### Profit Factor
- **Qué es:** Ganancias totales / Pérdidas totales
- **Bueno:** > 1.5
- **Excelente:** > 2.0

### Win Rate
- **Qué es:** % de trades ganadores
- **Bueno:** ≥ 60%
- **Excelente:** ≥ 70%

---

## ROADMAP

### Semana 1-2: Acumulación
- Sistema ejecutando automáticamente
- Acumulando trades
- Monitoreando dashboard

### Semana 3-4: Validación
- Mínimo 15 trades por estrategia
- Comparar métricas
- Identificar ganadoras

### Día 30+: Decisión
- ¿Alguna estrategia cumple criterios?
  - **SÍ** → Considerar dinero real
  - **NO** → Ajustar o continuar validación

---

## TELEGRAM ALERTS

Si Telegram está configurado, recibirás **automáticamente**:

### Alertas de Oportunidades
- Whales ($50M+)
- Clusters (3+ insiders)
- Exits importantes

### Alertas Multi-Trader
- Compras: `[UC] NVDA @ $450 (Score 92)`
- Ventas: `[BO] AAPL ✅ +12.5% (Take Profit)`

**Solo se envía si hubo trades ese día.**

---

## TROUBLESHOOTING

### Dashboard no carga datos
```bash
# Generar reporte manualmente
python multi_trader_report.py

# Verificar que existe
dir data\multi_trader_report.json
```

### Ver estado de base de datos
```bash
python multi_trader.py
```

### Regenerar todo desde cero
```bash
# CUIDADO: Esto borra todos los datos
del data\multi_trader.db
python multi_trader.py
```

---

## PRÓXIMOS PASOS

1. **Espera 30 días** mientras el sistema acumula datos
2. **Revisa el dashboard** semanalmente
3. **Compara estrategias** cuando tengas ≥15 trades
4. **Toma decisión científica** basada en métricas reales

**No tomes decisiones hasta tener datos suficientes.**

---

## FILOSOFÍA

Este sistema responde **científicamente**:

> "¿En cuál estrategia invertiría YO (Claude) mis propios $10,000?"

La respuesta vendrá de **datos reales**, no de teoría.

---

**¿Preguntas?** Lee [MULTI_TRADER_INTEGRATION.md](MULTI_TRADER_INTEGRATION.md) para detalles técnicos completos.
