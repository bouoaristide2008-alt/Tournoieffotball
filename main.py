import os
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes, ConversationHandler
)

# ------------------------- CONFIG -------------------------
NOM, EQUIPE, WHATSAPP = range(3)
inscriptions = {}

clubs_disponibles = [
    "Real Madrid", "FC Barcelone", "Manchester City", "Manchester United",
    "Liverpool", "Chelsea", "Arsenal", "Tottenham",
    "Paris Saint-Germain", "Bayern Munich", "Borussia Dortmund", "RB Leipzig",
    "Juventus", "AC Milan", "Inter Milan", "Napoli",
    "AS Roma", "Atletico Madrid", "Sevilla FC", "Valencia",
    "Ajax Amsterdam", "PSV Eindhoven", "Feyenoord", "Porto",
    "Benfica", "Sporting CP", "Galatasaray", "Fenerbahçe",
    "Besiktas", "Flamengo", "Palmeiras", "River Plate"
]

# Variables d'environnement
BOT_TOKEN = os.environ.get("8377020931:AAHGv8FI4i4xJjNUuUEN3Gp2Tjwn9FG7a2c")
ADMIN_ID = int(os.environ.get("6357925694"))
CANAL_ID = int(os.environ.get("CANAL_ID"))
LIEN_GROUPE = os.environ.get("")

# ------------------------- MENU -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 S'inscrire", callback_data="inscrire")],
        [InlineKeyboardButton("🏆 Tournoi", callback_data="tournoi")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Bienvenue sur le Bot Tournoi eFootball ⚽", reply_markup=reply_markup)

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "inscrire":
        if user_id in inscriptions:
            await query.edit_message_text("❌ Tu es déjà inscrit au tournoi.")
            return ConversationHandler.END
        await query.edit_message_text("✍️ Entre ton nom pour le tournoi :")
        return NOM
    elif query.data == "tournoi":
        await query.edit_message_text("🏆 Le tournoi commencera bientôt, reste connecté !")
        return ConversationHandler.END

# ------------------------- INSCRIPTION -------------------------
async def recevoir_nom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nom"] = update.message.text
    keyboard = []
    equipes_prises = [data["equipe"] for data in inscriptions.values()]
    for i, club in enumerate(clubs_disponibles, start=1):
        if club not in equipes_prises:
            keyboard.append([InlineKeyboardButton(f"{i}. {club}", callback_data=f"club_{i}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⚽ Sélectionne ton équipe :", reply_markup=reply_markup)
    return EQUIPE

async def recevoir_equipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choix = int(query.data.split("_")[1])
    equipe = clubs_disponibles[choix - 1]
    equipes_prises = [data["equipe"] for data in inscriptions.values()]
    if equipe in equipes_prises:
        await query.edit_message_text(f"❌ L'équipe {equipe} est déjà prise.\nRelance /start pour réessayer.")
        return ConversationHandler.END
    context.user_data["equipe"] = equipe
    await query.edit_message_text("📱 Envoie maintenant ton numéro WhatsApp (+225XXXXXXXX) :")
    return WHATSAPP

async def recevoir_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    numero = update.message.text
    context.user_data["whatsapp"] = numero
    user_id = update.message.from_user.id
    inscriptions[user_id] = context.user_data.copy()

    # Récap privé
    recap = (f"✅ Inscription réussie !\n\n"
             f"👤 Nom : {context.user_data['nom']}\n"
             f"⚽ Équipe : {context.user_data['equipe']}\n"
             f"📱 WhatsApp : {context.user_data['whatsapp']}\n\n"
             f"👉 Clique ici pour rejoindre le groupe : {LIEN_GROUPE}")
    await update.message.reply_text(recap)

    # Nouveau joueur dans canal
    recap_canal = (f"🆕 Nouveau joueur inscrit !\n\n"
                   f"👤 Nom : {context.user_data['nom']}\n"
                   f"⚽ Équipe : {context.user_data['equipe']}\n"
                   f"📱 WhatsApp : {context.user_data['whatsapp']}")
    await context.bot.send_message(chat_id=CANAL_ID, text=recap_canal)

    # Liste complète
    liste = "📋 Liste des participants :\n\n"
    for i, data in enumerate(inscriptions.values(), start=1):
        liste += f"{i}. 👤 {data['nom']} — ⚽ {data['equipe']}\n"
    await context.bot.send_message(chat_id=CANAL_ID, text=liste)
    return ConversationHandler.END

# ------------------------- ADMIN -------------------------
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Accès refusé.")
        return
    keyboard = [
        [InlineKeyboardButton("📋 Voir les inscrits", callback_data="admin_inscrits")],
        [InlineKeyboardButton("⚽ Équipes restantes", callback_data="admin_equipes")],
        [InlineKeyboardButton("❌ Supprimer un joueur", callback_data="admin_supprimer")],
        [InlineKeyboardButton("📤 Exporter en Excel", callback_data="admin_export")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔐 Menu Admin :", reply_markup=reply_markup)

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Accès refusé.")
        return
    if query.data == "admin_inscrits":
        if inscriptions:
            msg = "📋 Liste des inscrits :\n\n"
            for data in inscriptions.values():
                msg += f"👤 {data['nom']} | ⚽ {data['equipe']} | 📱 {data['whatsapp']}\n"
        else:
            msg = "❌ Aucun joueur inscrit."
        await query.edit_message_text(msg)
    elif query.data == "admin_equipes":
        equipes_prises = [data["equipe"] for data in inscriptions.values()]
        libres = [club for club in clubs_disponibles if club not in equipes_prises]
        msg = "⚽ Équipes disponibles :\n" + "\n".join(libres) if libres else "✅ Toutes les équipes sont prises."
        await query.edit_message_text(msg)
    elif query.data == "admin_supprimer":
        await query.edit_message_text("❌ Utilise la commande : /supprimer <nom>")
    elif query.data == "admin_export":
        if not inscriptions:
            await query.edit_message_text("❌ Aucune inscription à exporter.")
            return
        df = pd.DataFrame(inscriptions.values())
        file_path = "inscriptions.xlsx"
        df.to_excel(file_path, index=False)
        await query.message.reply_document(InputFile(file_path), caption="📤 Export des inscrits en Excel")

async def supprimer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Tu n'as pas accès.")
        return
    if len(context.args) == 0:
        await update.message.reply_text("Usage : /supprimer <nom>")
        return
    nom = " ".join(context.args)
    joueur_id = None
    for uid, data in inscriptions.items():
        if data["nom"].lower() == nom.lower():
            joueur_id = uid
            break
    if joueur_id:
        del inscriptions[joueur_id]
        await update.message.reply_text(f"✅ Joueur {nom} supprimé.")
    else:
        await update.message.reply_text(f"❌ Aucun joueur trouvé avec le nom : {nom}")

# ------------------------- APPLICATION -------------------------
# Exposé pour Gunicorn
app = Application.builder().token(BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        NOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_nom)],
        EQUIPE: [CallbackQueryHandler(recevoir_equipe, pattern="^club_")],
        WHATSAPP: [MessageHandler(filters.TEXT & ~filters.COMMAND, recevoir_whatsapp)],
    },
    fallbacks=[],
)

app.add_handler(conv_handler)
app.add_handler(CallbackQueryHandler(menu_callback, pattern="^(inscrire|tournoi)$"))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
app.add_handler(CommandHandler("supprimer", supprimer))
