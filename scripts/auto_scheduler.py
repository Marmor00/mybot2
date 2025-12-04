#!/usr/bin/env python3
"""
AUTO SCHEDULER - Ejecuta scraper automaticamente cada dia
Alternativa a Windows Task Scheduler (no requiere permisos admin)
"""
import schedule
import time
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def check_if_should_send_alerts():
    """
    Verifica si hay oportunidades buenas que ameritan enviar alertas

    Returns:
        bool: True si debe enviar alertas, False si no
    """
    try:
        import pandas as pd
        import json

        # Leer oportunidades actuales
        opportunities_file = Path("data/insider_opportunities.csv")
        if not opportunities_file.exists():
            return False

        df = pd.read_csv(opportunities_file)

        # Filtrar oportunidades buenas (Score 85+, HOT 0-3 días)
        if 'latest_purchase' in df.columns:
            df['days_old'] = (datetime.now() - pd.to_datetime(df['latest_purchase'])).dt.days
            hot_good = df[(df['days_old'] <= 3) & (df['score'] >= 85)]

            if len(hot_good) > 0:
                print(f"   -> Encontradas {len(hot_good)} oportunidades HOT (Score 85+)")
                return True

        # Verificar si hubo auto-compras en paper trading hoy
        try:
            from paper_trading import PaperTradingSystem
            pts = PaperTradingSystem()
            positions = pts.get_all_positions()
            pts.close()

            # Verificar si hay posiciones abiertas hoy
            today = datetime.now().strftime('%Y-%m-%d')
            today_positions = [p for p in positions if p.get('entry_date') == today]

            if len(today_positions) > 0:
                print(f"   -> Paper trading ejecuto {len(today_positions)} auto-compras HOY")
                return True
        except:
            pass

        return False

    except Exception as e:
        print(f"   -> Error verificando oportunidades: {e}")
        return False


def run_daily_scraper():
    """Ejecuta el daily scraper con alertas inteligentes"""
    print("\n" + "=" * 70)
    print(f"EJECUTANDO SCRAPER AUTOMATICO - {datetime.now()}")
    print("=" * 70)

    try:
        # PASO 1: Ejecutar scraper SIN alertas primero
        print("\n[1/2] Ejecutando scraper (sin alertas)...")
        result = subprocess.run(
            [sys.executable, "core/daily_scraper.py", "--no-alerts"],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutos max
        )

        # Guardar log
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"auto_scraper_{datetime.now().strftime('%Y%m%d')}.log"

        with open(log_file, "w", encoding='utf-8') as f:
            f.write(f"Ejecutado: {datetime.now()}\n")
            f.write(f"Exit code: {result.returncode}\n\n")
            f.write("STDOUT:\n")
            f.write(result.stdout)
            f.write("\n\nSTDERR:\n")
            f.write(result.stderr)

        if result.returncode == 0:
            print(f"   OK: Scraper ejecutado exitosamente")
            print(f"   Log guardado en: {log_file}")

            # PASO 2: Verificar si hay algo importante para enviar alertas
            print("\n[2/2] Verificando si hay oportunidades importantes...")
            should_alert = check_if_should_send_alerts()

            if should_alert:
                print("   -> SI hay oportunidades importantes!")
                print("   -> Enviando alertas Telegram...")

                # Ejecutar de nuevo CON alertas
                alert_result = subprocess.run(
                    [sys.executable, "core/daily_scraper.py"],
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                if alert_result.returncode == 0:
                    print("   OK: Alertas Telegram enviadas")
                else:
                    print("   WARNING: Error enviando alertas")
            else:
                print("   -> No hay oportunidades importantes hoy")
                print("   -> No se enviaran alertas (evitar spam)")

        else:
            print(f"   ERROR: Scraper fallo (exit code: {result.returncode})")
            print(f"   Ver detalles en: {log_file}")

    except subprocess.TimeoutExpired:
        print("   ERROR: TIMEOUT - El scraper tardo mas de 10 minutos")
    except Exception as e:
        print(f"   ERROR: {e}")

    print("=" * 70)


def main():
    """Scheduler principal"""
    print("\n" + "=" * 70)
    print("AUTO SCHEDULER INICIADO - ALERTAS INTELIGENTES")
    print("=" * 70)
    print("\nEste programa se quedara ejecutando en segundo plano")
    print("y ejecutara el scraper automaticamente todos los dias.")
    print("\nConfiguracion:")
    print("  - Hora de ejecucion: 18:00 (6 PM)")
    print("  - Frecuencia: Diaria")
    print("  - Logs: logs/auto_scraper_YYYYMMDD.log")
    print("\nAlertas Telegram INTELIGENTES:")
    print("  - Solo si hay oportunidades Score 85+ HOT (0-3 dias)")
    print("  - Solo si paper trading ejecuto auto-compras HOY")
    print("  - Evita spam en dias sin oportunidades buenas")
    print("\nPresiona Ctrl+C para detener")
    print("=" * 70 + "\n")

    # Programar tarea diaria a las 18:00
    schedule.every().day.at("18:00").do(run_daily_scraper)

    print(f"⏰ Proxima ejecucion: {schedule.next_run()}")
    print()

    # Loop infinito
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Revisar cada minuto
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("AUTO SCHEDULER DETENIDO")
        print("=" * 70)
        print("El scheduler ha sido detenido manualmente.")
        print("Para reactivarlo, ejecuta de nuevo: python auto_scheduler.py")
        print("=" * 70)


if __name__ == "__main__":
    main()
