"""
╔══════════════════════════════════════════════════════════╗
║           JB MULTI SPORTS — BOT DE TELEGRAM              ║
║         Bot completo de pronósticos deportivos           ║
╚══════════════════════════════════════════════════════════╝

INSTALACIÓN:
    pip install python-telegram-bot==20.7 apscheduler

CONFIGURACIÓN:
    1. Habla con @BotFather en Telegram
    2. Escribe /newbot → pon el nombre: JB Multi Sports → usuario: jbmultisports_bot
    3. Copia el TOKEN que te da
    4. Pégalo en BOT_TOKEN abajo
    5. Crea tu canal de Telegram → obtén el CHANNEL_ID (empieza con -100...)
    6. Agrega el bot como administrador del canal

DEPLOY EN RAILWAY:
    1. Sube este archivo a un repositorio de GitHub
    2. Entra a railway.app → New Project → Deploy from GitHub
    3. Agrega variables de entorno: BOT_TOKEN y CHANNEL_ID
    4. ¡Listo! Corre 24/7 gratis
"""

import os
import json
import logging
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ══════════════════════════════════════════
#  CONFIGURACIÓN — CAMBIA ESTOS VALORES
# ══════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "TU_TOKEN_AQUI")
CHANNEL_ID = os.getenv("CHANNEL_ID", "TU_CHANNEL_ID_AQUI")  # ej: -1001234567890
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",")]  # Tu ID de Telegram

# ══════════════════════════════════════════
#  BASE DE DATOS (archivo JSON simple)
# ══════════════════════════════════════════
DB_FILE = "picks_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"picks": [], "stats": {"total": 0, "ganados": 0, "perdidos": 0, "anulados": 0}}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ══════════════════════════════════════════
#  EMOJIS POR DEPORTE
# ══════════════════════════════════════════
SPORT_EMOJI = {
    "futbol": "⚽",
    "beisbol": "⚾",
    "basquet": "🏀",
    "otro": "🏆"
}

RESULT_EMOJI = {
    "ganado": "✅",
    "perdido": "❌",
    "pendiente": "⏳",
    "anulado": "⚪"
}

# ══════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def get_stats_text(stats: dict) -> str:
    total = stats["total"]
    ganados = stats["ganados"]
    perdidos = stats["perdidos"]
    pct = round((ganados / (ganados + perdidos)) * 100) if (ganados + perdidos) > 0 else 0
    racha = calcular_racha()
    return (
        f"📊 *Estadísticas JB Multi Sports*\n"
        f"{'─' * 30}\n"
        f"✅ Ganados: *{ganados}*\n"
        f"❌ Perdidos: *{perdidos}*\n"
        f"⚪ Anulados: *{stats['anulados']}*\n"
        f"📈 Efectividad: *{pct}%*\n"
        f"🔥 Racha actual: *{racha}*\n"
        f"{'─' * 30}\n"
        f"📌 Total de picks: *{total}*"
    )

def calcular_racha() -> str:
    db = load_db()
    picks = [p for p in db["picks"] if p["resultado"] in ["ganado", "perdido"]]
    picks = sorted(picks, key=lambda x: x["fecha"], reverse=True)
    
    if not picks:
        return "Sin picks aún"
    
    racha = 0
    tipo = picks[0]["resultado"]
    for p in picks:
        if p["resultado"] == tipo:
            racha += 1
        else:
            break
    
    emoji = "🔥" if tipo == "ganado" else "❄️"
    return f"{racha} {tipo}s seguidos {emoji}"

def format_pick(pick: dict) -> str:
    emoji = SPORT_EMOJI.get(pick.get("deporte", "otro"), "🏆")
    resultado_emoji = RESULT_EMOJI.get(pick.get("resultado", "pendiente"), "⏳")
    
    texto = (
        f"{emoji} *{pick['partido']}*\n"
        f"📋 Pick: {pick['pick']}\n"
        f"💰 Cuota: {pick.get('cuota', 'N/D')}\n"
        f"🏆 Deporte: {pick.get('deporte', 'N/D').capitalize()}\n"
        f"📅 Fecha: {pick['fecha']}\n"
        f"Estado: {resultado_emoji} {pick.get('resultado', 'pendiente').capitalize()}"
    )
    return texto

# ══════════════════════════════════════════
#  COMANDOS PÚBLICOS
# ══════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "🏆 *Bienvenido a JB Multi Sports* 🏆\n\n"
        "Tu fuente de análisis deportivo profesional.\n"
        "Fútbol ⚽ | Béisbol ⚾ | Básquet 🏀\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📌 *Comandos disponibles:*\n\n"
        "⚡ /picks — Ver pronósticos de hoy\n"
        "📊 /stats — Estadísticas y efectividad\n"
        "🔥 /racha — Racha actual\n"
        "📋 /historial — Últimos 10 picks\n"
        "ℹ️ /ayuda — Guía de comandos\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎯 _Análisis serio. Resultados reales._"
    )
    keyboard = [
        [InlineKeyboardButton("⚡ Picks de hoy", callback_data="picks_hoy")],
        [InlineKeyboardButton("📊 Estadísticas", callback_data="stats"),
         InlineKeyboardButton("🔥 Racha", callback_data="racha")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=reply_markup)

async def cmd_picks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    hoy = date.today().isoformat()
    picks_hoy = [p for p in db["picks"] if p["fecha"] == hoy]
    
    if not picks_hoy:
        await update.message.reply_text(
            "⏳ *No hay picks publicados para hoy aún.*\n\n"
            "Activa las notificaciones para recibirlos en cuanto se publiquen 🔔",
            parse_mode="Markdown"
        )
        return
    
    texto = f"⚡ *PICKS DEL DÍA — {hoy}*\n{'━' * 28}\n\n"
    for i, pick in enumerate(picks_hoy, 1):
        texto += f"*Pick #{i}*\n{format_pick(pick)}\n\n"
    
    texto += "━" * 28 + "\n🎯 _JB Multi Sports — Análisis profesional_"
    await update.message.reply_text(texto, parse_mode="Markdown")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    await update.message.reply_text(get_stats_text(db["stats"]), parse_mode="Markdown")

async def cmd_racha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    racha = calcular_racha()
    await update.message.reply_text(
        f"🔥 *Racha actual de JB Multi Sports*\n\n{racha}",
        parse_mode="Markdown"
    )

async def cmd_historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    picks = sorted(db["picks"], key=lambda x: x["fecha"], reverse=True)[:10]
    
    if not picks:
        await update.message.reply_text("📋 No hay picks en el historial aún.")
        return
    
    texto = "📋 *Últimos 10 picks*\n" + "━" * 28 + "\n\n"
    for pick in picks:
        emoji = RESULT_EMOJI.get(pick.get("resultado", "pendiente"), "⏳")
        texto += f"{emoji} {pick['partido']} — {pick['pick']}\n"
    
    texto += "\n" + "━" * 28 + "\nUsa /stats para ver el porcentaje de acierto 📊"
    await update.message.reply_text(texto, parse_mode="Markdown")

async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "ℹ️ *Guía JB Multi Sports Bot*\n\n"
        "*/picks* — Pronósticos publicados hoy\n"
        "*/stats* — Tu porcentaje de acierto histórico\n"
        "*/racha* — Cuántos picks seguidos llevas ganando\n"
        "*/historial* — Los últimos 10 picks con resultados\n\n"
        "💡 _Activa notificaciones del canal para no perderte ningún pick._"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")

# ══════════════════════════════════════════
#  COMANDOS DE ADMIN
# ══════════════════════════════════════════
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ No tienes permisos de administrador.")
        return
    
    texto = (
        "🔧 *Panel de Administrador JB Multi Sports*\n\n"
        "*/newpick* — Publicar nuevo pronóstico\n"
        "*/resultado [id] [ganado|perdido|anulado]* — Actualizar resultado\n"
        "*/listpicks* — Ver picks pendientes\n"
        "*/broadcast [mensaje]* — Enviar mensaje al canal\n"
        "*/resetstats* — Reiniciar estadísticas\n"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")

# Estados para ConversationHandler del newpick
PARTIDO, DEPORTE, PICK_TEXT, CUOTA = range(4)

async def cmd_newpick_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Sin permisos.")
        return ConversationHandler.END
    
    await update.message.reply_text("⚽ *Nuevo Pick*\n\n¿Cuál es el partido? (ej: Real Madrid vs Barcelona)", parse_mode="Markdown")
    return PARTIDO

async def newpick_partido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["partido"] = update.message.text
    keyboard = [
        [InlineKeyboardButton("⚽ Fútbol", callback_data="dep_futbol"),
         InlineKeyboardButton("⚾ Béisbol", callback_data="dep_beisbol")],
        [InlineKeyboardButton("🏀 Básquet", callback_data="dep_basquet"),
         InlineKeyboardButton("🏆 Otro", callback_data="dep_otro")]
    ]
    await update.message.reply_text("¿Qué deporte?", reply_markup=InlineKeyboardMarkup(keyboard))
    return DEPORTE

async def newpick_deporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["deporte"] = query.data.replace("dep_", "")
    await query.edit_message_text("📋 ¿Cuál es tu pick? (ej: Victoria local, Over 2.5, etc.)")
    return PICK_TEXT

async def newpick_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pick_text"] = update.message.text
    await update.message.reply_text("💰 ¿Cuál es la cuota? (ej: 1.85) — escribe 'N/D' si no aplica")
    return CUOTA

async def newpick_cuota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cuota"] = update.message.text
    
    db = load_db()
    nuevo_pick = {
        "id": len(db["picks"]) + 1,
        "partido": context.user_data["partido"],
        "deporte": context.user_data["deporte"],
        "pick": context.user_data["pick_text"],
        "cuota": context.user_data["cuota"],
        "fecha": date.today().isoformat(),
        "resultado": "pendiente"
    }
    db["picks"].append(nuevo_pick)
    db["stats"]["total"] += 1
    save_db(db)
    
    # Publicar al canal
    texto_canal = (
        f"🚨 *NUEVO PICK JB MULTI SPORTS* 🚨\n"
        f"{'━' * 30}\n\n"
        f"{format_pick(nuevo_pick)}\n\n"
        f"{'━' * 30}\n"
        f"🎯 _Sigue el canal para más análisis_"
    )
    
    try:
        await context.bot.send_message(CHANNEL_ID, texto_canal, parse_mode="Markdown")
        await update.message.reply_text(f"✅ Pick #{nuevo_pick['id']} publicado en el canal!")
    except Exception as e:
        await update.message.reply_text(f"✅ Pick guardado (error al enviar al canal: {e})")
    
    return ConversationHandler.END

async def cmd_resultado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Uso: /resultado [id] [ganado|perdido|anulado]")
        return
    
    pick_id = int(args[0])
    resultado = args[1].lower()
    
    if resultado not in ["ganado", "perdido", "anulado"]:
        await update.message.reply_text("Resultado debe ser: ganado, perdido o anulado")
        return
    
    db = load_db()
    for pick in db["picks"]:
        if pick["id"] == pick_id:
            pick["resultado"] = resultado
            db["stats"][resultado + "s" if resultado != "anulado" else "anulados"] += 1
            save_db(db)
            
            # Notificar al canal
            emoji = RESULT_EMOJI[resultado]
            texto = (
                f"{emoji} *RESULTADO — Pick #{pick_id}*\n\n"
                f"⚽ {pick['partido']}\n"
                f"📋 {pick['pick']}\n"
                f"Estado: *{resultado.upper()}*\n\n"
                f"📊 Stats actualizadas → /stats"
            )
            await context.bot.send_message(CHANNEL_ID, texto, parse_mode="Markdown")
            await update.message.reply_text(f"✅ Pick #{pick_id} marcado como {resultado}")
            return
    
    await update.message.reply_text(f"Pick #{pick_id} no encontrado.")

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text("Uso: /broadcast [mensaje]")
        return
    
    mensaje = " ".join(context.args)
    texto = f"📣 *JB MULTI SPORTS*\n\n{mensaje}\n\n_— JB Multi Sports_"
    await context.bot.send_message(CHANNEL_ID, texto, parse_mode="Markdown")
    await update.message.reply_text("✅ Mensaje enviado al canal.")

async def cmd_listpicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    db = load_db()
    pendientes = [p for p in db["picks"] if p["resultado"] == "pendiente"]
    
    if not pendientes:
        await update.message.reply_text("No hay picks pendientes.")
        return
    
    texto = "⏳ *Picks Pendientes*\n\n"
    for p in pendientes:
        texto += f"ID #{p['id']} — {p['partido']} | {p['pick']} ({p['fecha']})\n"
    
    texto += "\nUsa /resultado [id] [ganado|perdido|anulado] para actualizar"
    await update.message.reply_text(texto, parse_mode="Markdown")

# ══════════════════════════════════════════
#  CALLBACKS DE BOTONES
# ══════════════════════════════════════════
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "picks_hoy":
        db = load_db()
        hoy = date.today().isoformat()
        picks_hoy = [p for p in db["picks"] if p["fecha"] == hoy]
        if not picks_hoy:
            await query.edit_message_text("⏳ Sin picks publicados hoy aún. Activa notificaciones 🔔")
        else:
            texto = f"⚡ *PICKS DEL DÍA*\n{'━' * 25}\n\n"
            for i, pick in enumerate(picks_hoy, 1):
                texto += f"*#{i}* {format_pick(pick)}\n\n"
            await query.edit_message_text(texto, parse_mode="Markdown")
    
    elif query.data == "stats":
        db = load_db()
        await query.edit_message_text(get_stats_text(db["stats"]), parse_mode="Markdown")
    
    elif query.data == "racha":
        racha = calcular_racha()
        await query.edit_message_text(f"🔥 *Racha actual:*\n\n{racha}", parse_mode="Markdown")

# ══════════════════════════════════════════
#  TAREA PROGRAMADA — RESUMEN DIARIO
# ══════════════════════════════════════════
async def resumen_diario(bot):
    db = load_db()
    hoy = date.today().isoformat()
    picks_hoy = [p for p in db["picks"] if p["fecha"] == hoy]
    
    if not picks_hoy:
        return
    
    ganados = sum(1 for p in picks_hoy if p["resultado"] == "ganado")
    perdidos = sum(1 for p in picks_hoy if p["resultado"] == "perdido")
    
    texto = (
        f"🌙 *RESUMEN DEL DÍA — {hoy}*\n"
        f"{'━' * 30}\n\n"
        f"📊 Picks publicados: *{len(picks_hoy)}*\n"
        f"✅ Ganados: *{ganados}*\n"
        f"❌ Perdidos: *{perdidos}*\n\n"
        f"{'━' * 30}\n"
        f"_JB Multi Sports — Hasta mañana_ 🏆"
    )
    
    try:
        await bot.send_message(CHANNEL_ID, texto, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error enviando resumen diario: {e}")

# ══════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════
def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ConversationHandler para /newpick
    newpick_handler = ConversationHandler(
        entry_points=[CommandHandler("newpick", cmd_newpick_start)],
        states={
            PARTIDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, newpick_partido)],
            DEPORTE: [CallbackQueryHandler(newpick_deporte, pattern="^dep_")],
            PICK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, newpick_pick)],
            CUOTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, newpick_cuota)],
        },
        fallbacks=[]
    )
    
    # Registrar handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("picks", cmd_picks))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("racha", cmd_racha))
    app.add_handler(CommandHandler("historial", cmd_historial))
    app.add_handler(CommandHandler("ayuda", cmd_ayuda))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("resultado", cmd_resultado))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("listpicks", cmd_listpicks))
    app.add_handler(newpick_handler)
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Scheduler para resumen diario a las 11:30 PM
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        lambda: app.create_task(resumen_diario(app.bot)),
        "cron", hour=23, minute=30
    )
    scheduler.start()
    
    print("🏆 JB Multi Sports Bot corriendo...")
    app.run_polling()

if __name__ == "__main__":
    main()
