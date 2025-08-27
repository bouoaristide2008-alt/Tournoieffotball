   
# --- Configuration ---
TOKEN = os.environ.get("8377020931:AAHGv8FI4i4xJjNUuUEN3Gp2Tjwn9FG7a2c")  # Ton token Telegram
DB_FILE = "tournoi.db"
TEAMS = ["PSG","Real Madrid","Chelsea","Barça","Bayern","Man City","Man United",
         "Liverpool","Juventus","Milan AC","Inter","Arsenal","Atlético Madrid",
         "Dortmund","Napoli","Tottenham"]
ADMIN_IDS = [6357925694]  # Remplace par ton ID Telegram

# --- SQLite ---
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS joueurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            nom TEXT,
            equipe TEXT,
            whatsapp TEXT,
            code TEXT,
            ligue INTEGER,
            statut TEXT DEFAULT 'Qualifié'
            )""")
c.execute("""CREATE TABLE IF NOT EXISTS ligues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER
            )""")
conn.commit()

# --- États pour ConversationHandler ---
NOM, EQUIPE, WHATSAPP = range(3)

# --- Fonctions ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 S'inscrire au tournoi", callback_data="inscription")],
        [InlineKeyboardButton("📊 Voir mon statut", callback_data="statut")],
        [InlineKeyboardButton("📢 Canal officiel", url="https://t.me/clicpourrejointicitoites")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Bienvenue au tournoi eFootball !", reply_markup=reply_markup)

# --- Gestion des boutons ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "inscription":
        await query.message.reply_text("Quel est ton nom d'utilisateur eFootball ?")
        return NOM
    elif query.data == "statut":
        await query.message.reply_text("Entre ton code de participation :")
        return 10  # état pour le code
    return ConversationHandler.END

# --- Inscription ---
async def get_nom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nom'] = update.message.text
    # Préparer les équipes disponibles
    c.execute("SELECT equipe FROM joueurs WHERE ligue=(SELECT COALESCE(MAX(numero),1) FROM ligues)")
    used_teams = [row[0] for row in c.fetchall()]
    available_teams = [team for team in TEAMS if team not in used_teams]
    keyboard = [[InlineKeyboardButton(team, callback_data=team)] for team in available_teams]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choisis ton équipe :", reply_markup=reply_markup)
    return EQUIPE

async def get_equipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['equipe'] = query.data
    await query.message.reply_text("Quel est ton numéro WhatsApp (+225...) ?")
    return WHATSAPP

async def get_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    whatsapp = update.message.text
    context.user_data['whatsapp'] = whatsapp
    nom = context.user_data['nom']
    equipe = context.user_data['equipe']
    # Générer code unique
    code = str(random.randint(1000,9999))
    context.user_data['code'] = code
    # Déterminer la ligue
    c.execute("SELECT MAX(numero) FROM ligues")
    row = c.fetchone()
    if row[0] is None or c.execute("SELECT COUNT(*) FROM joueurs WHERE ligue=?", (row[0],)).fetchone()[0]>=16:
        ligue_num = 1 if row[0] is None else row[0]+1
        c.execute("INSERT INTO ligues (numero) VALUES (?)",(ligue_num,))
        conn.commit()
    else:
        ligue_num = row[0]
    # Insérer joueur
    c.execute("INSERT INTO joueurs (telegram_id, nom, equipe, whatsapp, code, ligue) VALUES (?,?,?,?,?,?)",
              (update.message.from_user.id, nom, equipe, whatsapp, code, ligue_num))
    conn.commit()
    await update.message.reply_text(f"""✅ Inscription réussie !

Nom d’utilisateur : {nom}
Ton équipe : {equipe}
Numéro WhatsApp : {whatsapp}
Code de participation : {code}

👉 Rejoins le canal officiel : TON_LIEN_TELEGRAM""")
    # Envoyer recap dans canal (ici le chat actuel, tu peux mettre un canal)
    participants = c.execute("SELECT nom,equipe FROM joueurs WHERE ligue=?", (ligue_num,)).fetchall()
    msg = "📋 Liste des participants au tournoi eFootball Mobile\n\nNom d’utilisateur        Équipe\n"
    for i,row in enumerate(participants,1):
        msg += f"{i}. {row[0]}           {row[1]}\n"
    await update.message.reply_text(msg)
    return ConversationHandler.END

# --- Voir statut ---
async def get_code_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text
    c.execute("SELECT nom,equipe,statut,ligue FROM joueurs WHERE code=?",(code,))
    row = c.fetchone()
    if row:
        await update.message.reply_text(f"""Nom d’utilisateur : {row[0]}
Équipe : {row[1]}
Statut : {row[2]}
Ligue : {row[3]}""")
    else:
        await update.message.reply_text("Code invalide !")
    return ConversationHandler.END

# --- Commande admin pour éliminer/qualifier ---
async def set_statut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS:
        await update.message.reply_text("Tu n'es pas autorisé !")
        return
    try:
        args = context.args
        nom = args[0]
        statut = args[1]
        if statut not in ["Éliminé","Qualifié"]:
            await update.message.reply_text("Statut invalide, utiliser Éliminé ou Qualifié")
            return
        c.execute("UPDATE joueurs SET statut=? WHERE nom=?",(statut,nom))
        conn.commit()
        await update.message.reply_text(f"{nom} est maintenant {statut}")
    except:
        await update.message.reply_text("Usage: /equipe <nom> <Éliminé/Qualifié>")

# --- Commande admin pour tirer matchs ---
async def tirer_matchs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS:
        await update.message.reply_text("Tu n'es pas autorisé !")
        return
    try:
        ligue_num = int(context.args[0])
        participants = c.execute("SELECT nom,equipe FROM joueurs WHERE ligue=? AND statut='Qualifié'",(ligue_num,)).fetchall()
        random.shuffle(participants)
        msg = f"🎮 Ligue {ligue_num} - Phase éliminatoire\n\nMatchs :\n"
        for i in range(0,len(participants),2):
            if i+1<len(participants):
                msg += f"{participants[i][0]} ({participants[i][1]}) vs {participants[i+1][0]} ({participants[i+1][1]})\n"
            else:
                msg += f"{participants[i][0]} ({participants[i][1]}) reçoit un bye\n"
        await update.message.reply_text(msg)
    except:
        await update.message.reply_text("Usage: /ligue <numero>")

# --- Rappels participants (simulé) ---
async def rappel_participants(context: ContextTypes.DEFAULT_TYPE):
    c.execute("SELECT telegram_id, nom, equipe FROM joueurs WHERE statut='Qualifié'")
    for row in c.fetchall():
        chat_id = row[0]
        await context.bot.send_message(chat_id=chat_id, text=f"🔔 Rappel : Ton prochain match approche !\nJoueur : {row[1]}\nÉquipe : {row[2]}")

# --- Option remplaçant ---
def choisir_remplacant(ligue_num):
    # retourne le premier joueur disponible non dans la phase actuelle
    c.execute("SELECT nom,equipe FROM joueurs WHERE ligue=? AND statut='Qualifié'",(ligue_num,))
    participants = c.fetchall()
    if participants:
        return participants[0]  # simple remplacement
    return None

# --- Conversation Handler ---
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(button)],
    states={
        NOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nom)],
        EQUIPE: [CallbackQueryHandler(get_equipe)],
        WHATSAPP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_whatsapp)],
        10: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_code_status)]
    },
    fallbacks=[]
)

# --- Application ---
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("equipe", set_statut))
app.add_handler(CommandHandler("ligue", tirer_matchs))
app.add_handler(conv_handler)

# --- Webhook pour Render ---
PORT = int(os.environ.get("PORT", 8443))
app.run_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN,
                webhook_url=f"https://TON_APP.onrender.com/{TOKEN}")     
