import os
import logging
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ==========================================
# CONFIGURACIÓN DE NUBE
# ==========================================
# Leemos el Token desde las variables de entorno de Render
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Servidor Web "Falso" para mantener vivo a Render
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ El Bot MetamorphIA está vivo y corriendo."

def run_flask():
    # Render asigna un puerto dinámicamente, por defecto usamos 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# LÓGICA DEL BOT (Igual que antes)
# ==========================================
FOLIACION, GRANO, TEXTURA, MINERAL = range(4)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "⚒️ *MetamorphIA Cloud*\nSistema Experto Online.\n\n*¿La roca presenta foliación?*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["Sí, es foliada"], ["No, es masiva"]], one_time_keyboard=True, resize_keyboard=True),
    )
    return FOLIACION

async def foliacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.lower()
    context.user_data['foliacion'] = 'si' if 'sí' in text or 'si' in text else 'no'
    
    if context.user_data['foliacion'] == 'si':
        await update.message.reply_text("📏 *Tamaño de Grano*", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup([["Fino (No visible)"], ["Medio (Visible)"], ["Grueso (>1mm)"]], one_time_keyboard=True, resize_keyboard=True))
        return GRANO
    else:
        context.user_data['grano'] = 'no_aplica'; context.user_data['textura'] = 'normal'
        await update.message.reply_text("💎 *Mineralogía*", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup([["Calcita"], ["Cuarzo"], ["Anfíbol"], ["Otros"]], one_time_keyboard=True, resize_keyboard=True))
        return MINERAL

async def grano(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.lower()
    if "fino" in text:
        context.user_data['grano'] = 'fino'
        await update.message.reply_text("✨ *Textura Satinada?*", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup([["Sí"], ["No"]], one_time_keyboard=True, resize_keyboard=True))
        return TEXTURA
    else:
        context.user_data['grano'] = 'medio' if 'medio' in text else 'grueso'
        context.user_data['textura'] = 'normal'
        await update.message.reply_text("💎 *Mineralogía*", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup([["Biotita / Granate"], ["Feldespato"], ["Anfíbol"], ["Cuarzo"]], one_time_keyboard=True, resize_keyboard=True))
        return MINERAL

async def textura(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.lower()
    context.user_data['textura'] = 'satinada' if 'sí' in text or 'si' in text else 'normal'
    await update.message.reply_text("💎 *Mineralogía*", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup([["Clorita / Sericita"], ["Moscovita"], ["Otros"]], one_time_keyboard=True, resize_keyboard=True))
    return MINERAL

async def mineral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.lower()
    context.user_data['mineral'] = identificar_mineral(text)
    resultado = clasificar_roca(context.user_data)
    await update.message.reply_text(f"🔬 *RESULTADO: {resultado['roca'].upper()}*\n🌡️ {resultado['grado']}\n🧱 {resultado['protolito']}\n\n/start de nuevo", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelado. /start", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- AUXILIARES (Lógica pura) ---
def identificar_mineral(t):
    if "clorita" in t or "sericita" in t: return "clorita"
    if "moscovita" in t: return "moscovita"
    if "biotita" in t: return "biotita"
    if "granate" in t: return "granate"
    if "feldespato" in t: return "feldespato"
    if "sillimanita" in t: return "sillimanita"
    if "calcita" in t: return "calcita"
    if "cuarzo" in t: return "cuarzo"
    if "anfíbol" in t or "anfibol" in t: return "anfibol"
    return "desconocido"

def clasificar_roca(d):
    f, g, t, m = d['foliacion'], d['grano'], d['textura'], d['mineral']
    if f=='si' and g=='fino' and t!='satinada' and m=='clorita': return {"roca": "Pizarra", "grado": "Muy Bajo", "protolito": "Lutita"}
    if f=='si' and g=='fino' and t=='satinada' and (m=='clorita' or m=='moscovita'): return {"roca": "Filita", "grado": "Bajo", "protolito": "Lutita"}
    if f=='si' and g=='medio' and (m=='biotita' or m=='granate'): return {"roca": "Esquisto", "grado": "Medio", "protolito": "Lutita"}
    if f=='si' and g=='grueso' and (m=='feldespato' or m=='sillimanita'): return {"roca": "Gneis", "grado": "Alto", "protolito": "Lutita/Granito"}
    if f=='no' and m=='calcita': return {"roca": "Mármol", "grado": "Variable", "protolito": "Caliza"}
    if f=='no' and m=='cuarzo': return {"roca": "Cuarcita", "grado": "Variable", "protolito": "Arenisca"}
    if f=='si' and m=='anfibol': return {"roca": "Anfibolita", "grado": "Medio-Alto", "protolito": "Basalto"}
    return {"roca": "Hornfels/Indet.", "grado": "Variable", "protolito": "?"}

# ==========================================
# EJECUCIÓN HÍBRIDA (Flask + Telegram)
# ==========================================
def main() -> None:
    # 1. Iniciar servidor web en segundo plano
    threading.Thread(target=run_flask).start()

    # 2. Verificar Token
    if not TOKEN:
        print("❌ ERROR: No se encontró la variable de entorno TELEGRAM_TOKEN")
        return

    # 3. Iniciar Bot
    application = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FOLIACION: [MessageHandler(filters.TEXT & ~filters.COMMAND, foliacion)],
            GRANO: [MessageHandler(filters.TEXT & ~filters.COMMAND, grano)],
            TEXTURA: [MessageHandler(filters.TEXT & ~filters.COMMAND, textura)],
            MINERAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, mineral)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    print("🤖 Bot Cloud Iniciado...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()