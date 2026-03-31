"""
JB MULTI SPORTS — BOT v2.0
Nuevas funciones:
- /hoy — Resumen matutino automático
- /encuesta — Encuestas a suscriptores
- Picks programados a hora fija
- Racha con barra visual
- Vista previa antes de publicar
- Compatible Python 3.11 + python-telegram-bot[job-queue]==20.7
"""

import os
import json
import logging
from datetime import date, time as dtime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "TU_TOKEN_AQUI")
CHANNEL_ID = os.getenv("CHANNEL_ID", "TU_CHANNEL_ID_AQUI")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DB_FILE = "picks_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"picks": [], "programados": [], "stats": {"total": 0, "ganados": 0, "perdidos": 0, "anulados": 0}}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

SPORT_EMOJI = {"futbol": "⚽", "beisbol": "⚾", "basquet": "🏀", "otro": "🏆"}
RESULT_EMOJI = {"ganado": "✅", "perdido": "❌", "pendiente": "⏳", "anulado": "⚪"}

def is_admin(uid): return uid in ADMIN_IDS

def calcular_racha():
    db = load_db()
    picks = sorted([p for p in db["picks"] if p["resultado"] in ["ganado","perdido"]], key=lambda x: x["fecha"], reverse=True)
    if not picks: return 0, "neutral", "Sin picks aún"
    racha, tipo = 0, picks[0]["resultado"]
    for p in picks:
        if p["resultado"] == tipo: racha += 1
        else: break
    return racha, tipo, f"{racha} {tipo}s seguidos {'🔥' if tipo=='ganado' else '❄️'}"

def racha_visual(n, tipo):
    b = "🟩" if tipo == "ganado" else "🟥"
    return b * min(n, 10) + "⬜" * max(0, 10 - n)

def format_pick(p):
    return (
        f"{SPORT_EMOJI.get(p.get('deporte','otro'),'🏆')} *{p['partido']}*\n"
        f"📋 Pick: {p['pick']}\n💰 Cuota: {p.get('cuota','N/D')}\n"
        f"🏆 {p.get('deporte','').capitalize()}\n📅 {p['fecha']}\n"
        f"Estado: {RESULT_EMOJI.get(p.get('resultado','pendiente'),'⏳')} {p.get('resultado','pendiente').capitalize()}"
    )

def get_stats_text():
    db = load_db(); s = db["stats"]
    tr = s["ganados"] + s["perdidos"]
    pct = round(s["ganados"]/tr*100) if tr > 0 else 0
    rn, rt, rtxt = calcular_racha()
    return (f"📊 *Estadísticas JB Multi Sports*\n{'─'*28}\n"
            f"✅ Ganados: *{s['ganados']}*\n❌ Perdidos: *{s['perdidos']}*\n"
            f"⚪ Anulados: *{s['anulados']}*\n📈 Efectividad: *{pct}%*\n{'─'*28}\n"
            f"🔥 Racha: *{rtxt}*\n{racha_visual(rn,rt)}\n{'─'*28}\n📌 Total: *{s['total']}*")

# ── ESTADOS ──
PARTIDO, DEPORTE, PICK_TEXT, CUOTA, CONFIRMAR = range(5)
P_PARTIDO, P_DEPORTE, P_PICK, P_CUOTA, P_HORA = range(5,10)
E_PREGUNTA, E_OPCIONES = range(10,12)
ED_CAMPO, ED_VALOR = range(12,14)

# ── COMANDOS PÚBLICOS ──
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("⚡ Picks de hoy", callback_data="picks_hoy")],
          [InlineKeyboardButton("📊 Stats", callback_data="stats"), InlineKeyboardButton("🔥 Racha", callback_data="racha")]]
    await update.message.reply_text(
        "🏆 *Bienvenido a JB Multi Sports* 🏆\n\n⚽ Fútbol | ⚾ Béisbol | 🏀 Básquet\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n⚡ /picks — Picks de hoy\n🌅 /hoy — Resumen matutino\n"
        "📊 /stats — Estadísticas\n🔥 /racha — Racha actual\n📋 /historial — Últimos picks\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n🎯 _Donde los datos mandan._",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def cmd_picks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db(); hoy = date.today().isoformat()
    ph = [p for p in db["picks"] if p["fecha"] == hoy]
    if not ph:
        await update.message.reply_text("⏳ *Sin picks hoy aún.* Activa notificaciones 🔔", parse_mode="Markdown"); return
    txt = f"⚡ *PICKS DEL DÍA — {hoy}*\n{'━'*26}\n\n"
    for i,p in enumerate(ph,1): txt += f"*Pick #{i}*\n{format_pick(p)}\n\n"
    await update.message.reply_text(txt + "━"*26 + "\n🎯 _JB Multi Sports_", parse_mode="Markdown")

async def cmd_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db(); hoy = date.today().isoformat()
    ph = [p for p in db["picks"] if p["fecha"] == hoy]
    rn, rt, rtxt = calcular_racha()
    txt = f"🌅 *BUENOS DÍAS — {hoy}*\n{'━'*28}\n\n🔥 Racha:\n{racha_visual(rn,rt)}\n{rtxt}\n\n"
    if ph:
        txt += f"📋 *{len(ph)} pick(s) para hoy:*\n"
        for p in ph: txt += f"{SPORT_EMOJI.get(p.get('deporte','otro'),'🏆')} {p['partido']} → {p['pick']}\n"
    else:
        txt += "📋 _Los picks se publicarán durante el día 🔔_\n"
    await update.message.reply_text(txt + f"\n{'━'*28}\n🎯 _JB Multi Sports_", parse_mode="Markdown")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_stats_text(), parse_mode="Markdown")

async def cmd_racha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rn, rt, rtxt = calcular_racha()
    await update.message.reply_text(f"🔥 *Racha actual JB Multi Sports*\n\n{racha_visual(rn,rt)}\n\n*{rtxt}*", parse_mode="Markdown")

async def cmd_historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    picks = sorted(db["picks"], key=lambda x: x["fecha"], reverse=True)[:10]
    if not picks: await update.message.reply_text("📋 No hay picks aún."); return
    txt = "📋 *Últimos 10 picks*\n" + "━"*26 + "\n\n"
    for p in picks: txt += f"{RESULT_EMOJI.get(p.get('resultado','pendiente'),'⏳')} {p['partido']} — {p['pick']}\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

# ── ADMIN ──
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text(
        "🔧 *Panel Admin JB v2*\n\n*/newpick* — Publicar pick\n*/programar* — Pick a hora fija\n"
        "*/resultado [id] [res]* — Actualizar resultado\n*/editpick [id]* — Editar pick\n"
        "*/listpicks* — Ver pendientes\n*/encuesta* — Encuesta al canal\n*/broadcast [msg]* — Mensaje libre",
        parse_mode="Markdown")

# ── NEWPICK ──
async def newpick_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    await update.message.reply_text("⚽ *Nuevo Pick*\n\n¿Cuál es el partido?", parse_mode="Markdown")
    return PARTIDO

async def newpick_partido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["partido"] = update.message.text
    kb = [[InlineKeyboardButton("⚽ Fútbol", callback_data="dep_futbol"), InlineKeyboardButton("⚾ Béisbol", callback_data="dep_beisbol")],
          [InlineKeyboardButton("🏀 Básquet", callback_data="dep_basquet"), InlineKeyboardButton("🏆 Otro", callback_data="dep_otro")]]
    await update.message.reply_text("¿Deporte?", reply_markup=InlineKeyboardMarkup(kb))
    return DEPORTE

async def newpick_deporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["deporte"] = q.data.replace("dep_","")
    await q.edit_message_text("📋 ¿Cuál es tu pick? (ej: Victoria local, Over 2.5)")
    return PICK_TEXT

async def newpick_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pick_text"] = update.message.text
    await update.message.reply_text("💰 ¿Cuota? (ej: 1.85 o N/D)")
    return CUOTA

async def newpick_cuota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cuota"] = update.message.text
    preview = (f"👁 *Vista previa:*\n\n⚽ *{context.user_data['partido']}*\n"
               f"📋 {context.user_data['pick_text']}\n💰 {context.user_data['cuota']}\n"
               f"🏆 {context.user_data['deporte'].capitalize()}\n\n¿Publicar al canal?")
    kb = [[InlineKeyboardButton("✅ Publicar", callback_data="conf_si"), InlineKeyboardButton("❌ Cancelar", callback_data="conf_no")]]
    await update.message.reply_text(preview, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return CONFIRMAR

async def newpick_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "conf_no":
        await q.edit_message_text("❌ Cancelado."); return ConversationHandler.END
    db = load_db()
    nuevo = {"id": len(db["picks"])+1, "partido": context.user_data["partido"],
             "deporte": context.user_data["deporte"], "pick": context.user_data["pick_text"],
             "cuota": context.user_data["cuota"], "fecha": date.today().isoformat(), "resultado": "pendiente"}
    db["picks"].append(nuevo); db["stats"]["total"] += 1; save_db(db)
    txt = f"🚨 *NUEVO PICK JB MULTI SPORTS* 🚨\n{'━'*30}\n\n{format_pick(nuevo)}\n\n{'━'*30}\n🎯 _Donde los datos mandan._"
    try:
        await context.bot.send_message(CHANNEL_ID, txt, parse_mode="Markdown")
        await q.edit_message_text(f"✅ Pick #{nuevo['id']} publicado!")
    except Exception as e:
        await q.edit_message_text(f"✅ Guardado. Error canal: {e}")
    return ConversationHandler.END

# ── PROGRAMAR ──
async def programar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    await update.message.reply_text("⏰ *Pick Programado*\n\n¿Cuál es el partido?", parse_mode="Markdown")
    return P_PARTIDO

async def programar_partido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["p_partido"] = update.message.text
    kb = [[InlineKeyboardButton("⚽ Fútbol", callback_data="pd_futbol"), InlineKeyboardButton("⚾ Béisbol", callback_data="pd_beisbol")],
          [InlineKeyboardButton("🏀 Básquet", callback_data="pd_basquet"), InlineKeyboardButton("🏆 Otro", callback_data="pd_otro")]]
    await update.message.reply_text("¿Deporte?", reply_markup=InlineKeyboardMarkup(kb))
    return P_DEPORTE

async def programar_deporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["p_deporte"] = q.data.replace("pd_","")
    await q.edit_message_text("📋 ¿Cuál es tu pick?")
    return P_PICK

async def programar_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["p_pick"] = update.message.text
    await update.message.reply_text("💰 ¿Cuota?")
    return P_CUOTA

async def programar_cuota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["p_cuota"] = update.message.text
    await update.message.reply_text("⏰ ¿A qué hora publicar? (formato HH:MM, ej: 09:00)")
    return P_HORA

async def programar_hora(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        h, m = map(int, update.message.text.strip().split(":"))
    except:
        await update.message.reply_text("❌ Formato inválido. Usa HH:MM (ej: 09:00)"); return P_HORA
    db = load_db()
    prog = {"id": len(db.get("programados",[]))+1, "partido": context.user_data["p_partido"],
            "deporte": context.user_data["p_deporte"], "pick": context.user_data["p_pick"],
            "cuota": context.user_data["p_cuota"], "hora": f"{h:02d}:{m:02d}", "fecha": date.today().isoformat()}
    if "programados" not in db: db["programados"] = []
    db["programados"].append(prog); save_db(db)
    context.job_queue.run_once(publicar_programado, dtime(h, m), data=prog)
    await update.message.reply_text(f"✅ Pick programado para las *{h:02d}:{m:02d}*\n\n⚽ {prog['partido']}\n📋 {prog['pick']}", parse_mode="Markdown")
    return ConversationHandler.END

async def publicar_programado(context: ContextTypes.DEFAULT_TYPE):
    p = context.job.data; db = load_db()
    nuevo = {"id": len(db["picks"])+1, "partido": p["partido"], "deporte": p["deporte"],
             "pick": p["pick"], "cuota": p["cuota"], "fecha": date.today().isoformat(), "resultado": "pendiente"}
    db["picks"].append(nuevo); db["stats"]["total"] += 1; save_db(db)
    await context.bot.send_message(CHANNEL_ID,
        f"🚨 *NUEVO PICK JB MULTI SPORTS* 🚨\n{'━'*30}\n\n{format_pick(nuevo)}\n\n{'━'*30}\n🎯 _Donde los datos mandan._",
        parse_mode="Markdown")

# ── ENCUESTA ──
async def encuesta_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    await update.message.reply_text("📊 *Nueva Encuesta*\n\n¿Cuál es la pregunta?\n_Ej: ¿Quién gana hoy?_", parse_mode="Markdown")
    return E_PREGUNTA

async def encuesta_pregunta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["e_pregunta"] = update.message.text
    await update.message.reply_text("📝 Opciones separadas por coma:\n_Ej: Real Madrid, Barcelona, Empate_", parse_mode="Markdown")
    return E_OPCIONES

async def encuesta_opciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    opciones = [o.strip() for o in update.message.text.split(",")]
    if len(opciones) < 2:
        await update.message.reply_text("❌ Necesitas al menos 2 opciones."); return E_OPCIONES
    try:
        await context.bot.send_poll(CHANNEL_ID, question=context.user_data["e_pregunta"],
                                    options=opciones, is_anonymous=True, allows_multiple_answers=False)
        await update.message.reply_text("✅ Encuesta publicada!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    return ConversationHandler.END

# ── EDITAR PICK ──
async def cmd_editpick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    if not context.args: await update.message.reply_text("Uso: /editpick [id]"); return ConversationHandler.END
    db = load_db(); pid = int(context.args[0])
    pick = next((p for p in db["picks"] if p["id"] == pid), None)
    if not pick: await update.message.reply_text(f"Pick #{pid} no encontrado."); return ConversationHandler.END
    context.user_data["edit_id"] = pid
    kb = [[InlineKeyboardButton("📋 Pick", callback_data="edit_pick"), InlineKeyboardButton("💰 Cuota", callback_data="edit_cuota")],
          [InlineKeyboardButton("⚽ Partido", callback_data="edit_partido")]]
    await update.message.reply_text(f"✏️ *Editando Pick #{pid}*\n{pick['partido']}\n\n¿Qué campo editar?",
                                     parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return ED_CAMPO

async def editpick_campo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["edit_campo"] = q.data.replace("edit_","")
    nombres = {"pick":"pronóstico","cuota":"cuota","partido":"partido"}
    await q.edit_message_text(f"✏️ Nuevo valor para *{nombres[context.user_data['edit_campo']]}*:", parse_mode="Markdown")
    return ED_VALOR

async def editpick_valor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db(); pid = context.user_data["edit_id"]; campo = context.user_data["edit_campo"]
    for p in db["picks"]:
        if p["id"] == pid:
            p[campo] = update.message.text; save_db(db)
            await update.message.reply_text(f"✅ Pick #{pid} actualizado.")
            return ConversationHandler.END
    await update.message.reply_text("❌ Error."); return ConversationHandler.END

# ── RESULTADO ──
async def cmd_resultado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    args = context.args
    if len(args) < 2: await update.message.reply_text("Uso: /resultado [id] [ganado|perdido|anulado]"); return
    pid, res = int(args[0]), args[1].lower()
    if res not in ["ganado","perdido","anulado"]: await update.message.reply_text("Resultado: ganado, perdido o anulado"); return
    db = load_db()
    for p in db["picks"]:
        if p["id"] == pid:
            p["resultado"] = res
            db["stats"]["anulados" if res=="anulado" else res+"s"] += 1; save_db(db)
            rn, rt, rtxt = calcular_racha()
            await context.bot.send_message(CHANNEL_ID,
                f"{RESULT_EMOJI[res]} *RESULTADO — Pick #{pid}*\n\n⚽ {p['partido']}\n📋 {p['pick']}\nEstado: *{res.upper()}*\n\n{'━'*26}\n🔥 Racha:\n{racha_visual(rn,rt)}\n{rtxt}",
                parse_mode="Markdown")
            await update.message.reply_text(f"✅ Pick #{pid} → {res}"); return
    await update.message.reply_text(f"Pick #{pid} no encontrado.")

async def cmd_listpicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    db = load_db(); pend = [p for p in db["picks"] if p["resultado"]=="pendiente"]
    if not pend: await update.message.reply_text("No hay picks pendientes."); return
    txt = "⏳ *Picks Pendientes*\n\n"
    for p in pend: txt += f"ID #{p['id']} — {p['partido']} | {p['pick']} ({p['fecha']})\n"
    await update.message.reply_text(txt + "\n/resultado [id] [ganado|perdido|anulado]", parse_mode="Markdown")

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args: await update.message.reply_text("Uso: /broadcast [mensaje]"); return
    await context.bot.send_message(CHANNEL_ID, f"📣 *JB MULTI SPORTS*\n\n{' '.join(context.args)}", parse_mode="Markdown")
    await update.message.reply_text("✅ Enviado.")

# ── CALLBACKS ──
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "picks_hoy":
        db = load_db(); hoy = date.today().isoformat(); ph = [p for p in db["picks"] if p["fecha"]==hoy]
        if not ph: await q.edit_message_text("⏳ Sin picks hoy aún 🔔"); return
        txt = f"⚡ *PICKS DEL DÍA*\n{'━'*24}\n\n"
        for i,p in enumerate(ph,1): txt += f"*#{i}* {format_pick(p)}\n\n"
        await q.edit_message_text(txt, parse_mode="Markdown")
    elif q.data == "stats":
        await q.edit_message_text(get_stats_text(), parse_mode="Markdown")
    elif q.data == "racha":
        rn, rt, rtxt = calcular_racha()
        await q.edit_message_text(f"🔥 *Racha actual:*\n\n{racha_visual(rn,rt)}\n\n*{rtxt}*", parse_mode="Markdown")

# ── JOBS ──
async def resumen_matutino(context: ContextTypes.DEFAULT_TYPE):
    db = load_db(); hoy = date.today().isoformat(); ph = [p for p in db["picks"] if p["fecha"]==hoy]
    rn, rt, rtxt = calcular_racha()
    txt = f"🌅 *BUENOS DÍAS — {hoy}*\n{'━'*28}\n\n🔥 Racha:\n{racha_visual(rn,rt)}\n{rtxt}\n\n"
    txt += (f"📋 *{len(ph)} pick(s) para hoy:*\n" + "".join(f"{SPORT_EMOJI.get(p.get('deporte','otro'),'🏆')} {p['partido']} → {p['pick']}\n" for p in ph)) if ph else "📋 _Los picks se publicarán durante el día 🔔_\n"
    await context.bot.send_message(CHANNEL_ID, txt + f"\n{'━'*28}\n🎯 _JB Multi Sports_", parse_mode="Markdown")

async def resumen_nocturno(context: ContextTypes.DEFAULT_TYPE):
    db = load_db(); hoy = date.today().isoformat(); ph = [p for p in db["picks"] if p["fecha"]==hoy]
    if not ph: return
    rn, rt, rtxt = calcular_racha()
    await context.bot.send_message(CHANNEL_ID,
        f"🌙 *RESUMEN — {hoy}*\n{'━'*28}\n\n📊 Picks: *{len(ph)}*\n✅ Ganados: *{sum(1 for p in ph if p['resultado']=='ganado')}*\n❌ Perdidos: *{sum(1 for p in ph if p['resultado']=='perdido')}*\n\n🔥 Racha:\n{racha_visual(rn,rt)}\n{rtxt}\n\n{'━'*28}\n_JB Multi Sports — Hasta mañana_ 🏆",
        parse_mode="Markdown")

# ══════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(ConversationHand
