"""
JB MULTI SPORTS — BOT DE TELEGRAM
Compatible con Python 3.13 + python-telegram-bot 20.7
"""

import os
import json
import logging
import asyncio
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ══════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "TU_TOKEN_AQUI")
CHANNEL_ID = os.getenv("CHANNEL_ID", "TU_CHANNEL_ID_AQUI")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ══════════════════════════════════════════
#  BASE DE DATOS JSON
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
#  HELPERS
# ══════════════════════════════════════════
SPORT_EMOJI = {"futbol": "⚽", "beisbol": "⚾", "basquet": "🏀", "otro": "🏆"}
RESULT_EMOJI = {"ganado": "✅", "perdido": "❌", "pendiente": "⏳", "anulado": "⚪"}

def is_admin(user_id):
    return user_id in ADMIN_IDS

def calcular_racha():
    db = load_db()
    picks = [p for p in db["picks"] if p["resultado"] in ["ganado", "perdido"]]
    picks = sorted(picks, key=lambda x: x["fecha"], reverse=True)
    if not picks:
        return "Sin picks aún"
    racha, tipo = 0, picks[0]["resultado"]
    for p in picks:
        if p["resultado"] == tipo:
            racha += 1
        else:
            break
    emoji = "🔥" if tipo == "ganado" else "❄️"
    return f"{racha} {tipo}s seguidos {emoji}"

def format_pick(pick):
    emoji = SPORT_EMOJI.get(pick.get("deporte", "otro"), "🏆")
    res_emoji = RESULT_EMOJI.get(pick.get("resultado", "pendiente"), "⏳")
    return (
        f"{emoji} *{pick['partido']}*\n"
        f"📋 Pick: {pick['pick']}\n"
        f"💰 Cuota: {pick.get('cuota', 'N/D')}\n"
        f"🏆 Deporte: {pick.get('deporte','').capitalize()}\n"
        f"📅 Fecha: {pick['fecha']}\n"
        f"Estado: {res_emoji} {pick.get('resultado','pendiente').capitalize()}"
    )

def get_stats_text():
    db = load_db()
    s = db["stats"]
    total_res = s["ganados"] + s["perdidos"]
    pct = round((s["ganados"] / total_res) * 100) if total_res > 0 else 0
    return (
        f"📊 *Estadísticas JB Multi Sports*\n"
        f"{'─' * 28}\n"
        f"✅ Ganados: *{s['ganados']}*\n"
        f"❌ Perdidos: *{s['perdidos']}*\n"
        f"⚪ Anulados: *{s['anulados']}*\n"
        f"📈 Efectividad: *{pct}%*\n"
        f"🔥 Racha: *{calcular_racha()}*\n"
        f"{'─' * 28}\n"
        f"📌 Total picks: *{s['total']}*"
    )

# ══════════════════════════════════════════
#  COMANDOS PÚBLICOS
# ══════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "🏆 *Bienvenido a JB Multi Sports* 🏆\n\n"
        "Tu fuente de análisis deportivo profesional.\n"
        "⚽ Fútbol | ⚾ Béisbol | 🏀 Básquet\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ /picks — Pronósticos de hoy\n"
        "📊 /stats — Estadísticas\n"
        "🔥 /racha — Racha actual\n"
        "📋 /historial — Últimos picks\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎯 _Análisis serio. Resultados reales._"
    )
    keyboard = [
        [InlineKeyboardButton("⚡ Picks de hoy", callback_data="picks_hoy")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats"),
         InlineKeyboardButton("🔥 Racha", callback_data="racha")]
    ]
    await update.message.reply_text(texto, parse_mode="Markdown",
                                     reply_markup=InlineKeyboardMarkup(keyboard))

async def cmd_picks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    hoy = date.today().isoformat()
    picks_hoy = [p for p in db["picks"] if p["fecha"] == hoy]
    if not picks_hoy:
        await update.message.reply_text(
            "⏳ *No hay picks publicados hoy aún.*\n\nActiva notificaciones 🔔",
            parse_mode="Markdown")
        return
    texto = f"⚡ *PICKS DEL DÍA — {hoy}*\n{'━'*26}\n\n"
    for i, p in enumerate(picks_hoy, 1):
        texto += f"*Pick #{i}*\n{format_pick(p)}\n\n"
    texto += "━"*26 + "\n🎯 _JB Multi Sports_"
    await update.message.reply_text(texto, parse_mode="Markdown")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_stats_text(), parse_mode="Markdown")

async def cmd_racha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🔥 *Racha actual JB Multi Sports*\n\n{calcular_racha()}", parse_mode="Markdown")

async def cmd_historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    picks = sorted(db["picks"], key=lambda x: x["fecha"], reverse=True)[:10]
    if not picks:
        await update.message.reply_text("📋 No hay picks aún.")
        return
    texto = "📋 *Últimos 10 picks*\n" + "━"*26 + "\n\n"
    for p in picks:
        e = RESULT_EMOJI.get(p.get("resultado", "pendiente"), "⏳")
        texto += f"{e} {p['partido']} — {p['pick']}\n"
    await update.message.reply_text(texto, parse_mode="Markdown")

async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Comandos JB Multi Sports*\n\n"
        "*/picks* — Picks de hoy\n"
        "*/stats* — Estadísticas\n"
        "*/racha* — Racha actual\n"
        "*/historial* — Últimos 10 picks",
        parse_mode="Markdown")

# ══════════════════════════════════════════
#  COMANDOS ADMIN
# ══════════════════════════════════════════
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Sin permisos.")
        return
    await update.message.reply_text(
        "🔧 *Panel Admin JB Multi Sports*\n\n"
        "*/newpick* — Publicar pronóstico\n"
        "*/resultado [id] [ganado|perdido|anulado]* — Actualizar\n"
        "*/listpicks* — Ver pendientes\n"
        "*/broadcast [msg]* — Mensaje al canal",
        parse_mode="Markdown")

# Estados para /newpick
PARTIDO, DEPORTE, PICK_TEXT, CUOTA = range(4)

async def newpick_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Sin permisos.")
        return ConversationHandler.END
    await update.message.reply_text("⚽ *Nuevo Pick*\n\n¿Cuál es el partido?", parse_mode="Markdown")
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
    await query.edit_message_text("📋 ¿Cuál es tu pick? (ej: Victoria local, Over 2.5)")
    return PICK_TEXT

async def newpick_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pick_text"] = update.message.text
    await update.message.reply_text("💰 ¿Cuál es la cuota? (ej: 1.85 — escribe N/D si no aplica)")
    return CUOTA

async def newpick_cuota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    nuevo = {
        "id": len(db["picks"]) + 1,
        "partido": context.user_data["partido"],
        "deporte": context.user_data["deporte"],
        "pick": context.user_data["pick_text"],
        "cuota": update.message.text,
        "fecha": date.today().isoformat(),
        "resultado": "pendiente"
    }
    db["picks"].append(nuevo)
    db["stats"]["total"] += 1
    save_db(db)

    texto_canal = (
        f"🚨 *NUEVO PICK JB MULTI SPORTS* 🚨\n"
        f"{'━'*30}\n\n"
        f"{format_pick(nuevo)}\n\n"
        f"{'━'*30}\n"
        f"🎯 _Sigue el canal para más análisis_"
    )
    try:
        await context.bot.send_message(CHANNEL_ID, texto_canal, parse_mode="Markdown")
        await update.message.reply_text(f"✅ Pick #{nuevo['id']} publicado en el canal!")
    except Exception as e:
        await update.message.reply_text(f"✅ Pick guardado. Error canal: {e}")
    return ConversationHandler.END

async def cmd_resultado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Uso: /resultado [id] [ganado|perdido|anulado]")
        return
    pick_id, resultado = int(args[0]), args[1].lower()
    if resultado not in ["ganado", "perdido", "anulado"]:
        await update.message.reply_text("Resultado: ganado, perdido o anulado")
        return
    db = load_db()
    for pick in db["picks"]:
        if pick["id"] == pick_id:
            pick["resultado"] = resultado
            key = "anulados" if resultado == "anulado" else resultado + "s"
            db["stats"][key] += 1
            save_db(db)
            emoji = RESULT_EMOJI[resultado]
            texto = (
                f"{emoji} *RESULTADO — Pick #{pick_id}*\n\n"
                f"⚽ {pick['partido']}\n"
                f"📋 {pick['pick']}\n"
                f"Estado: *{resultado.upper()}*"
            )
            await context.bot.send_message(CHANNEL_ID, texto, parse_mode="Markdown")
            await update.message.reply_text(f"✅ Pick #{pick_id} → {resultado}")
            return
    await update.message.reply_text(f"Pick #{pick_id} no encontrado.")

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
    texto += "\n/resultado [id] [ganado|perdido|anulado]"
    await update.message.reply_text(texto, parse_mode="Markdown")

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Uso: /broadcast [mensaje]")
        return
    msg = " ".join(context.args)
    await context.bot.send_message(CHANNEL_ID, f"📣 *JB MULTI SPORTS*\n\n{msg}", parse_mode="Markdown")
    await update.message.reply_text("✅ Enviado al canal.")

# ══════════════════════════════════════════
#  CALLBACKS
# ══════════════════════════════════════════
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "picks_hoy":
        db = load_db()
        hoy = date.today().isoformat()
        picks_hoy = [p for p in db["picks"] if p["fecha"] == hoy]
        if not picks_hoy:
            await query.edit_message_text("⏳ Sin picks hoy aún. Activa notificaciones 🔔")
        else:
            texto = f"⚡ *PICKS DEL DÍA*\n{'━'*24}\n\n"
            for i, p in enumerate(picks_hoy, 1):
                texto += f"*#{i}* {format_pick(p)}\n\n"
            await query.edit_message_text(texto, parse_mode="Markdown")
    elif query.data == "stats":
        await query.edit_message_text(get_stats_text(), parse_mode="Markdown")
    elif query.data == "racha":
        await query.edit_message_text(f"🔥 *Racha actual:*\n\n{calcular_racha()}", parse_mode="Markdown")

# ══════════════════════════════════════════
#  RESUMEN DIARIO
# ══════════════════════════════════════════
async def resumen_diario(context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    hoy = date.today().isoformat()
    picks_hoy = [p for p in db["picks"] if p["fecha"] == hoy]
    if not picks_hoy:
        return
    ganados = sum(1 for p in picks_hoy if p["resultado"] == "ganado")
    perdidos = sum(1 for p in picks_hoy if p["resultado"] == "perdido")
    texto = (
        f"🌙 *RESUMEN DEL DÍA — {hoy}*\n"
        f"{'━'*28}\n\n"
        f"📊 Picks: *{len(picks_hoy)}*\n"
        f"✅ Ganados: *{ganados}*\n"
        f"❌ Perdidos: *{perdidos}*\n\n"
        f"_JB Multi Sports — Hasta mañana_ 🏆"
    )
    await context.bot.send_message(CHANNEL_ID, texto, parse_mode="Markdown")

# ══════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler para /newpick
    conv = ConversationHandler(
        entry_points=[CommandHandler("newpick", newpick_start)],
        states={
            PARTIDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, newpick_partido)],
            DEPORTE: [CallbackQueryHandler(newpick_deporte, pattern="^dep_")],
            PICK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, newpick_pick)],
            CUOTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, newpick_cuota)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("picks", cmd_picks))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("racha", cmd_racha))
    app.add_handler(CommandHandler("historial", cmd_historial))
    app.add_handler(CommandHandler("ayuda", cmd_ayuda))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("resultado", cmd_resultado))
    app.add_handler(CommandHandler("listpicks", cmd_listpicks))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(button_callback))

    # Resumen diario a las 11:30 PM
    app.job_queue.run_daily(resumen_diario, time=__import__('datetime').time(23, 30))

    logging.info("🏆 JB Multi Sports Bot iniciado!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
    
