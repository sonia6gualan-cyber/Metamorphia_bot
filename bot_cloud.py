import os
import logging
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ==========================================
# CONFIGURACIÓN DE NUBE
# ==========================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ El Bot MetamorphIA está vivo y corriendo."

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# LÓGICA DEL BOT
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
    
    # Obtenemos la LISTA de resultados posibles
    resultados = clasificar_roca(context.user_data)
    
    if not resultados:
        # Caso: Ninguna coincidencia
        mensaje = (
            "⚠️ *RESULTADO: Indeterminado*\n\n"
            "Las características no coinciden con una roca estándar.\n"
            "_Escribe /start para intentar de nuevo._"
        )
    elif len(resultados) == 1:
        # Caso: Solo una coincidencia (Lo normal)
        res = resultados[0]
        mensaje = (
            f"🔬 *RESULTADO: {res['roca'].upper()}*\n\n"
            f"🌡️ *Grado:* {res['grado']}\n"
            f"🧱 *Protolito:* {res['protolito']}\n\n"
            "_Escribe /start para reiniciar._"
        )
    else:
        # Caso: Múltiples coincidencias (Gneis vs Migmatita, etc.)
        mensaje = "🔬 *RESULTADOS POSIBLES:*\nSe encontraron múltiples coincidencias:\n\n"
        for i, res in enumerate(resultados, 1):
            mensaje += (
                f"*{i}. {res['roca'].upper()}*\n"
                f"   🌡️ Grado: {res['grado']}\n"
                f"   🧱 Protolito: {res['protolito']}\n\n"
            )
        mensaje += "_Analiza el contexto geológico para decidir._\n_Escribe /start para reiniciar._"

    await update.message.reply_text(mensaje, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelado. /start", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- LÓGICA DE CLASIFICACIÓN (MULTI-RESPUESTA) ---
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
    posibles = [] # Lista para acumular resultados
    
    # 1. Rocas Foliadas
    if f == 'si':
        # Pizarra
        if g=='fino' and t!='satinada' and m=='clorita': 
            posibles.append({"roca": "Pizarra", "grado": "Muy Bajo", "protolito": "Lutita"})
        
        # Filita
        if g=='fino' and t=='satinada' and (m=='clorita' or m=='moscovita'): 
            posibles.append({"roca": "Filita", "grado": "Bajo", "protolito": "Lutita"})
        
        # Esquisto
        if g=='medio' and (m=='biotita' or m=='granate'): 
            posibles.append({"roca": "Esquisto", "grado": "Medio", "protolito": "Lutita"})
        
        # Gneis (Feldespato entra aquí)
        if g=='grueso' and (m=='feldespato' or m=='sillimanita'): 
            posibles.append({"roca": "Gneis", "grado": "Alto", "protolito": "Lutita/Granito"})
        
        # Migmatita (Feldespato TAMBIÉN entra aquí)
        # Nota: En tu regla original migmatita usaba 'cuarzo_cristalino', pero geológicamente el feldespato es clave en la anatexis.
        # Si queremos que aparezca como segunda opción con feldespato:
        if g=='grueso' and (m=='feldespato' or m=='cuarzo_cristalino'): 
            posibles.append({"roca": "Migmatita", "grado": "Muy Alto (Anatexis)", "protolito": "Gneis"})
            
        # Anfibolita
        if m=='anfibol': 
            posibles.append({"roca": "Anfibolita", "grado": "Medio-Alto", "protolito": "Basalto"})

    # 2. Rocas No Foliadas
    if f == 'no':
        match_found = False
        if m=='calcita': 
            posibles.append({"roca": "Mármol", "grado": "Variable", "protolito": "Caliza"})
            match_found = True
        if m=='cuarzo': 
            posibles.append({"roca": "Cuarcita", "grado": "Variable", "protolito": "Arenisca"})
            match_found = True
        if m=='anfibol': 
            posibles.append({"roca": "Anfibolita (Masiva)", "grado": "Medio-Alto", "protolito": "Basalto"})
            match_found = True
        
        # Solo sugerimos Hornfels si no encajó claramente en las anteriores
        if not match_found:
             posibles.append({"roca": "Hornfels", "grado": "Variable (Contacto)", "protolito": "Pelita/Arenisca"})
    
    return posibles

# ==========================================
# EJECUCIÓN
# ==========================================
def main() -> None:
    threading.Thread(target=run_flask).start()
    if not TOKEN:
        print("❌ ERROR: TOKEN no encontrado")
        return
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
