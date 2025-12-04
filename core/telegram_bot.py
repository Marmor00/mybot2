#!/usr/bin/env python3
"""
TELEGRAM ALERT SYSTEM
Envía notificaciones automáticas de oportunidades frescas
"""
import requests
from datetime import datetime
from config import Config

class TelegramBot:
    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.enabled = Config.telegram_configured()

        if not self.enabled:
            print("⚠️  Telegram no configurado. Alertas deshabilitadas.")
            print("💡 Ejecuta setup_telegram() para configurar")

    def send_message(self, message, parse_mode='HTML'):
        """Envía mensaje a Telegram"""
        if not self.enabled:
            print(f"📱 [SIMULACIÓN] {message}")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }

            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()

            print("OK: Mensaje enviado a Telegram")
            return True

        except Exception as e:
            print(f"ERROR: Error enviando mensaje Telegram: {e}")
            return False

    def send_whale_alert(self, whale_opportunity):
        """Alerta de whale trade detectado"""
        ticker = whale_opportunity['ticker']
        insider = whale_opportunity['insider_name']
        value_m = whale_opportunity['purchase_value_millions']
        price = whale_opportunity['purchase_price']
        days = whale_opportunity.get('days_since_trade', 'N/A')

        message = f"""
🐋 <b>WHALE TRADE ALERT!</b> 🐋

<b>Ticker:</b> ${ticker}
<b>Insider:</b> {insider}
<b>Value:</b> ${value_m}M
<b>Price:</b> ${price}
<b>Days ago:</b> {days}

💰 Major insider buying detected!
"""
        self.send_message(message)

    def send_cluster_alert(self, cluster_opportunity):
        """Alerta de cluster buying detectado"""
        ticker = cluster_opportunity['ticker']
        insider_count = cluster_opportunity['insider_count']
        total_value_m = cluster_opportunity['total_value_millions']
        avg_price = cluster_opportunity['avg_purchase_price']
        days = cluster_opportunity.get('days_since_latest', 'N/A')

        message = f"""
📊 <b>CLUSTER BUYING ALERT!</b>

<b>Ticker:</b> ${ticker}
<b>Insiders:</b> {insider_count} executives buying
<b>Total Value:</b> ${total_value_m}M
<b>Avg Price:</b> ${avg_price}
<b>Days ago:</b> {days}

🎯 Multiple insiders accumulating!
"""
        self.send_message(message)

    def send_important_purchase_alert(self, opportunity):
        """Alerta de compra importante de CEO/Founder"""
        ticker = opportunity['ticker']
        insider = opportunity['insider_name']
        title = opportunity['title']
        value_m = round(opportunity['purchase_value_usd'] / 1000000, 1)
        price = opportunity['purchase_price']
        days = opportunity.get('days_since_trade', 'N/A')

        message = f"""
💰 <b>IMPORTANT PURCHASE!</b>

<b>Ticker:</b> ${ticker}
<b>Insider:</b> {insider}
<b>Title:</b> {title}
<b>Value:</b> ${value_m}M
<b>Price:</b> ${price}
<b>Days ago:</b> {days}

🔥 CEO/Founder buying aggressively!
"""
        self.send_message(message)

    def send_exit_alert(self, exit_info):
        """Alerta de exit detectado (insider vendió)"""
        ticker = exit_info['ticker']
        insider = exit_info['insider_name']
        sale_value_m = exit_info['sale_value_millions'] if 'sale_value_millions' in exit_info else round(exit_info['sale_value']/1000000, 1)
        sale_price = exit_info['sale_price']
        pnl_pct = exit_info.get('realized_pnl_pct', 'N/A')
        status = exit_info['exit_status']

        emoji = "🔴" if status == "EXITED" else "🟡"
        status_text = "FULL EXIT" if status == "EXITED" else "PARTIAL EXIT"

        message = f"""
{emoji} <b>EXIT ALERT!</b>

<b>Ticker:</b> ${ticker}
<b>Insider:</b> {insider}
<b>Status:</b> {status_text}
<b>Sale Value:</b> ${sale_value_m}M
<b>Sale Price:</b> ${sale_price}
<b>P&L:</b> {pnl_pct}%

⚠️ Insider is selling position!
"""
        self.send_message(message)

    def send_daily_summary(self, summary_data):
        """Resumen diario de actividad"""
        new_whales = summary_data.get('new_whales', 0)
        new_clusters = summary_data.get('new_clusters', 0)
        new_exits = summary_data.get('new_exits', 0)
        hot_opportunities = summary_data.get('hot_opportunities', [])

        if new_whales == 0 and new_clusters == 0 and new_exits == 0:
            # No enviar resumen si no hay novedades
            return

        message = f"""
📈 <b>DAILY INSIDER ACTIVITY SUMMARY</b>
{datetime.now().strftime('%Y-%m-%d')}

🐋 New Whales: {new_whales}
📊 New Clusters: {new_clusters}
🔴 New Exits: {new_exits}

"""

        if hot_opportunities:
            message += "<b>🔥 HOT Opportunities (0-3 days):</b>\n"
            for opp in hot_opportunities[:5]:
                ticker = opp.get('ticker', 'N/A')
                type_emoji = "🐋" if opp.get('type') == 'whale' else "📊"
                message += f"{type_emoji} ${ticker}\n"

        message += "\n💡 Check dashboard for details!"

        self.send_message(message)

    def send_multi_trader_summary(self, trade_actions):
        """
        Resumen de trades ejecutados por las 5 estrategias

        Args:
            trade_actions: Dict con {strategy_id: {'buys': [...], 'sells': [...]}}
        """
        # Verificar si hubo alguna acción
        total_buys = sum(len(actions.get('buys', [])) for actions in trade_actions.values())
        total_sells = sum(len(actions.get('sells', [])) for actions in trade_actions.values())

        if total_buys == 0 and total_sells == 0:
            # No enviar si no hubo trades
            return

        message = f"""
🤖 <b>MULTI-TRADER DAILY REPORT</b>
{datetime.now().strftime('%Y-%m-%d')}

"""

        # Mapeo de emojis
        emoji_map = {
            'ultra_conservative': '[UC]',
            'balanced_optimal': '[BO]',
            'momentum_hunter': '[MH]',
            'early_stage_master': '[ES]',
            'diversified_portfolio': '[DP]'
        }

        # Compras
        if total_buys > 0:
            message += f"<b>📥 COMPRAS ({total_buys}):</b>\n"
            for strategy_id, actions in trade_actions.items():
                buys = actions.get('buys', [])
                if buys:
                    emoji = emoji_map.get(strategy_id, strategy_id)
                    for buy in buys:
                        ticker = buy.get('ticker')
                        price = buy.get('price', 0)
                        score = buy.get('score', 0)
                        message += f"{emoji} {ticker} @ ${price:.2f} (Score {score})\n"
            message += "\n"

        # Ventas
        if total_sells > 0:
            message += f"<b>📤 VENTAS ({total_sells}):</b>\n"
            for strategy_id, actions in trade_actions.items():
                sells = actions.get('sells', [])
                if sells:
                    emoji = emoji_map.get(strategy_id, strategy_id)
                    for sell in sells:
                        ticker = sell.get('ticker')
                        return_pct = sell.get('return_pct', 0)
                        reason = sell.get('reason', 'N/A')
                        return_emoji = "✅" if return_pct > 0 else "❌"
                        message += f"{emoji} {ticker} {return_emoji} {return_pct:+.1f}% ({reason})\n"
            message += "\n"

        message += "💡 Check dashboard for full comparison!"

        self.send_message(message)

    def test_connection(self):
        """Prueba la conexión con Telegram"""
        message = """
🤖 <b>Telegram Bot Configured!</b>

Your Insider Trading Alert System is now active.

You'll receive alerts for:
🐋 Whale trades ($50M+)
📊 Cluster buying (3+ insiders)
💰 Important CEO/Founder purchases ($2M+)
🔴 Exit alerts (insider selling)

✅ System ready!
"""
        return self.send_message(message)


def setup_telegram():
    """Setup inicial del bot de Telegram"""
    print("=" * 60)
    print("🤖 TELEGRAM BOT SETUP")
    print("=" * 60)
    print()
    print("Pasos para configurar tu bot:")
    print()
    print("1. Abre Telegram y busca: @BotFather")
    print("2. Envía el comando: /newbot")
    print("3. Sigue las instrucciones (nombre y username del bot)")
    print("4. BotFather te dará un TOKEN (guárdalo)")
    print()
    print("5. Busca tu bot en Telegram y envíale: /start")
    print()
    print("6. Para obtener tu CHAT_ID:")
    print("   - Ve a: https://api.telegram.org/bot<TU_TOKEN>/getUpdates")
    print("   - Busca el campo 'chat' -> 'id'")
    print()
    print("-" * 60)
    print()

    bot_token = input("Ingresa tu BOT TOKEN: ").strip()
    chat_id = input("Ingresa tu CHAT ID: ").strip()

    if not bot_token or not chat_id:
        print("❌ Token o Chat ID vacío. Setup cancelado.")
        return

    # Guardar configuración
    Config.save_telegram_config(bot_token, chat_id)

    # Probar conexión
    print("\n🧪 Probando conexión...")
    bot = TelegramBot()

    if bot.test_connection():
        print("✅ Bot configurado exitosamente!")
        print("📱 Revisa Telegram - deberías haber recibido un mensaje de confirmación")
    else:
        print("❌ Error en la configuración. Verifica token y chat_id")


def send_test_alerts():
    """Envía alertas de prueba"""
    bot = TelegramBot()

    if not bot.enabled:
        print("⚠️  Ejecuta setup_telegram() primero")
        return

    print("Enviando alertas de prueba...")

    # Test whale alert
    test_whale = {
        'ticker': 'NVDA',
        'insider_name': 'Jensen Huang',
        'purchase_value_millions': 75.5,
        'purchase_price': 450.00,
        'days_since_trade': 1
    }
    bot.send_whale_alert(test_whale)

    # Test cluster alert
    test_cluster = {
        'ticker': 'TSLA',
        'insider_count': 4,
        'total_value_millions': 8.2,
        'avg_purchase_price': 245.50,
        'days_since_latest': 2
    }
    bot.send_cluster_alert(test_cluster)

    print("✅ Alertas de prueba enviadas!")


if __name__ == "__main__":
    # Si ejecutas este archivo directamente, abre setup
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'setup':
        setup_telegram()
    elif len(sys.argv) > 1 and sys.argv[1] == 'test':
        send_test_alerts()
    else:
        print("Uso:")
        print("  python telegram_bot.py setup    - Configurar bot")
        print("  python telegram_bot.py test     - Enviar alertas de prueba")
