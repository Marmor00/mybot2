#!/usr/bin/env python3
"""
CONFIGURACIÓN CENTRALIZADA
Todos los parámetros configurables de la app
"""
import os
from pathlib import Path

class Config:
    """Configuración global de la aplicación"""

    # Directorios
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"

    # API Keys
    FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY', 'd28176pr01qr2iau5o4gd28176pr01qr2iau5o50')

    # Telegram Bot (llenar después de crear bot con @BotFather)
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8464111172:AAFOd6oUT1ta-vcoGZJY-jEySnBw69ADosI')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '5542606013')

    # Scraper Configuration
    SCRAPER_CONFIG = {
        'days_back': 60,                    # Ventana de scraping
        'min_purchase_value': 500000,       # $500K mínimo individual
        'min_cluster_value': 1500000,       # $1.5M mínimo cluster
        'whale_threshold': 50000000,        # $50M para whale trades (BAJADO de $99M)
        'max_pe_ratio': 25,
        'min_market_cap': 500000000,        # $500M mínimo
        'max_market_cap': 50000000000,      # $50B máximo
        'min_daily_volume': 100000,
    }

    # Freshness Configuration
    FRESHNESS_CONFIG = {
        'hot_max_days': 3,      # 0-3 días = HOT 🔥
        'fresh_max_days': 7,    # 4-7 días = FRESH ✅
        'recent_max_days': 14,  # 8-14 días = RECENT ⚠️
        # 15+ días = OLD 🗑️ (oculto por default)
    }

    # Alert Thresholds (para Telegram)
    ALERT_THRESHOLDS = {
        'whale_min_value': 50000000,        # $50M+ = Whale alert
        'important_purchase': 2000000,      # $2M+ CEO/Founder
        'cluster_min_insiders': 3,          # 3+ insiders = cluster alert
        'cluster_timeframe_days': 7,        # dentro de 7 días
        'exit_alert_min_value': 1000000,    # $1M+ en ventas
    }

    # Momentum Stages
    MOMENTUM_CONFIG = {
        'early_max': 5.0,       # 0-5% = Early stage
        'confirmed_max': 15.0,  # 5-15% = Confirmed stage
        'late_min': 15.0        # 15%+ = Late stage
    }

    # Archivos de datos
    FILES = {
        'raw_trades': DATA_DIR / 'insider_trades_raw.csv',
        'opportunities': DATA_DIR / 'insider_opportunities.csv',
        'whales': DATA_DIR / 'whale_opportunities.csv',
        'sales': DATA_DIR / 'insider_sales.csv',
        'exit_tracking': DATA_DIR / 'exit_tracking.csv',
        'research_json': DATA_DIR / 'weekly_research_report.json',
        'research_csv': DATA_DIR / 'weekly_research_report.csv',
        'previous_scrape': DATA_DIR / 'previous_scrape.csv',  # NUEVO: para comparar
        'new_opportunities': DATA_DIR / 'new_opportunities.json',  # NUEVO: compras últimas 24h
    }

    # Insiders relevantes
    RELEVANT_INSIDERS = [
        'ceo', 'chief executive', 'founder', 'co-founder',
        'cfo', 'chief financial', 'president', 'chairman',
        'chair', '10%'
    ]

    WHALE_INSIDERS = [
        'ceo', 'chief executive', 'founder', 'co-founder', '10%'
    ]

    @classmethod
    def ensure_data_dir(cls):
        """Crea directorio de datos si no existe"""
        cls.DATA_DIR.mkdir(exist_ok=True)

    @classmethod
    def telegram_configured(cls):
        """Verifica si Telegram está configurado"""
        return bool(cls.TELEGRAM_BOT_TOKEN and cls.TELEGRAM_CHAT_ID)

    @classmethod
    def save_telegram_config(cls, bot_token, chat_id):
        """Guarda configuración de Telegram en archivo .env"""
        env_file = cls.BASE_DIR / '.env'

        # Leer .env existente o crear nuevo
        env_lines = []
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_lines = [line.strip() for line in f if line.strip() and not line.startswith('TELEGRAM_')]

        # Agregar configuración Telegram
        env_lines.append(f'TELEGRAM_BOT_TOKEN={bot_token}')
        env_lines.append(f'TELEGRAM_CHAT_ID={chat_id}')

        # Guardar
        with open(env_file, 'w') as f:
            f.write('\n'.join(env_lines) + '\n')

        print(f"✅ Configuración Telegram guardada en {env_file}")

        # Actualizar variables de clase
        cls.TELEGRAM_BOT_TOKEN = bot_token
        cls.TELEGRAM_CHAT_ID = chat_id

# Asegurar que directorio de datos existe
Config.ensure_data_dir()
