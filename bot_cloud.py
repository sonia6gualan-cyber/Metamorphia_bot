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
    logger.info("Comando /start recibido")
    await update.message.reply_text(
        "⚒️ *MetamorphIA Cloud*\nSistema Experto Online.\n\n*¿La roca presenta foliación?*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["Sí, es foliada"], ["No, es masiva"]], one_time_keyboard=True, resize_keyboard=True),
    )
    return FOLIACION

async def foliacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.lower()
    logger.info(f"Respuesta foliación: {text}")
    
    es_foliada = False
    
    # Detección de respuesta
    if "no" in text.split() or "masiva" in text:
        es_foliada = False
    elif "si" in text.split() or "sí" in text.split() or "foliada" in text:
        es_foliada = True
    else:
        await update.message.reply_text("Por favor responde Sí o No.")
        return FOLIACION

    context.user_data['foliacion'] = 'si' if es_foliada else 'no'
    
    if es_foliada:
        # Camino FOLIADA -> Pregunta Grano
        await update.message.reply_text("📏 *Tamaño de Grano*", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup([["Fino (No visible)"], ["Medio (Visible)"], ["Grueso (>1mm)"]], one_time_keyboard=True, resize_keyboard=True))
        return GRANO
    else:
        # Camino NO FOLIADA -> Salta a Mineral Diagnóstico
        context.user_data['grano'] = 'no_aplica'
        context.user_data['textura'] = 'normal'
        
        # Teclado limpio (sin nombres de roca) + Nueva opción Dolomita
        teclado_no_foliado = [
            ["Calcita"], 
            ["Dolomita"], 
            ["Cuarzo"], 
            ["Anfíbol"],
            ["Otros"]
        ]
        await update.message.reply_text("💎 *Mineral Diagnóstico (Roca Masiva)*\nSelecciona el mineral predominante:", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup(teclado_no_foliado, one_time_keyboard=True, resize_keyboard=True))
        return MINERAL

async def grano(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.lower()
    if "fino" in text:
        context.user_data['grano'] = 'fino'
        await update.message.reply_text("✨ *Textura Satinada?*", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup([["Sí, satinada"], ["No, es mate"]], one_time_keyboard=True, resize_keyboard=True))
        return TEXTURA
    else:
        context.user_data['grano'] = 'medio' if 'medio' in text else 'grueso'
        context.user_data['textura'] = 'normal'
        
        # Minerales para foliadas de grano medio/grueso
        teclado_foliado = [
            ["Biotita", "Granate"], 
            ["Feldespato", "Sillimanita"], 
            ["Anfíbol"],
            ["Cuarzo Cristalino"]
        ]
        # Pregunta específica "Mineral Guía" para foliadas
        await update.message.reply_text("💎 *Mineral Guía*", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup(teclado_foliado, one_time_keyboard=True, resize_keyboard=True))
        return MINERAL

async def textura(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.lower()
    if "satinada" in text or "sí" in text.split() or "si" in text.split():
        context.user_data['textura'] = 'satinada'
    else:
        context.user_data['textura'] = 'normal'
        
    teclado_fino = [
        ["Clorita", "Sericita"], 
        ["Moscovita"], 
        ["Otros"]
    ]
    # Pregunta específica "Mineral Guía" para foliadas
    await update.message.reply_text("💎 *Mineral Guía*", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup(teclado_fino, one_time_keyboard=True, resize_keyboard=True))
    return MINERAL

async def mineral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.lower()
    context.user_data['mineral'] = identificar_mineral(text)
    
    resultados = clasificar_roca(context.user_data)
    
    if not resultados:
        mensaje = "⚠️ *RESULTADO: Indeterminado*\n\nCaracterísticas inusuales.\n_Escribe /start para intentar de nuevo._"
    elif len(resultados) == 1:
        res = resultados[0]
        mensaje = (
            f"🔬 *RESULTADO: {res['roca'].upper()}*\n\n"
            f"🌡️ *Grado Metamórfico:* {res['grado']}\n"
            f"🧱 *Protolito Posible:* {res['protolito']}\n\n"
            "_Escribe /start para reiniciar._"
        )
    else:
        mensaje = "🔬 *RESULTADOS POSIBLES:*\n\n"
        for i, res in enumerate(resultados, 1):
            mensaje += f"*{i}. {res['roca'].upper()}*\n   🌡️ Grado: {res['grado']}\n   🧱 Protolito: {res['protolito']}\n\n"
        mensaje += "_Escribe /start para reiniciar._"

    await update.message.reply_text(mensaje, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelado. /start", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- LÓGICA DE CLASIFICACIÓN ---
def identificar_mineral(t):
    if "dolomita" in t: return "dolomita" # Nuevo
    if "clorita" in t: return "clorita"
    if "sericita" in t: return "sericita"
    if "moscovita" in t: return "moscovita"
    if "biotita" in t: return "biotita"
    if "granate" in t: return "granate"
    if "feldespato" in t: return "feldespato"
    if "sillimanita" in t: return "sillimanita"
    if "calcita" in t: return "calcita"
    if "cuarzo" in t: return "cuarzo"
    if "anfíbol" in t or "anfibol" in t: return "anfibol"
    if "cristalino" in t: return "cuarzo_cristalino"
    return "desconocido"

def clasificar_roca(d):
    f, g, t, m = d['foliacion'], d['grano'], d['textura'], d['mineral']
    posibles = []
    
    # 1. Rocas Foliadas
    if f == 'si':
        if g=='fino' and t!='satinada' and (m=='clorita' or m=='sericita'): 
            posibles.append({"roca": "Pizarra", "grado": "Muy Bajo", "protolito": "Lutita"})
        
        if g=='fino' and t=='satinada' and (m=='sericita' or m=='moscovita'): 
            posibles.append({"roca": "Filita", "grado": "Bajo", "protolito": "Lutita"})
        
        if g=='medio' and (m=='biotita' or m=='granate'): 
            posibles.append({"roca": "Esquisto", "grado": "Medio", "protolito": "Lutita"})
        
        if g=='grueso' and (m=='feldespato' or m=='sillimanita'): 
            posibles.append({"roca": "Gneis", "grado": "Alto", "protolito": "Lutita/Granito/Diorita"})
        
        if g=='grueso' and (m=='feldespato' or m=='cuarzo_cristalino'): 
            posibles.append({"roca": "Migmatita", "grado": "Muy Alto", "protolito": "Gneis"})
            
        if m=='anfibol': 
            posibles.append({"roca": "Anfibolita", "grado": "Medio a Alto", "protolito": "Basalto"})

    # 2. Rocas No Foliadas
    if f == 'no':
        match_found = False
        
        # MÁRMOL (Calcita -> Caliza)
        if m=='calcita': 
            posibles.append({"roca": "Mármol", "grado": "Variable", "protolito": "Caliza"})
            match_found = True
            
        # MÁRMOL (Dolomita -> Dolomía) - NUEVA REGLA
        if m=='dolomita': 
            posibles.append({"roca": "Mármol", "grado": "Variable", "protolito": "Dolomía"})
            match_found = True
            
        # CUARCITA
        if m=='cuarzo': 
            posibles.append({"roca": "Cuarcita", "grado": "Variable", "protolito": "Arenisca"})
            match_found = True
        
        # ANFIBOLITA (Masiva)
        if m=='anfibol': 
            posibles.append({"roca": "Anfibolita (Masiva)", "grado": "Medio a Alto", "protolito": "Basalto"})
            match_found = True
        
        # HORNFELS (Por defecto si no es ninguna de las anteriores)
        if not match_found:
             posibles.append({"roca": "Hornfels", "grado": "Variable (Contacto)", "protolito": "Cualquier roca"})
    
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
