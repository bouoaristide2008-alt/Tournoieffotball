# main.py
import os
import random
import sqlite3
from threading import Lock
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ====== CONFIGURATION ======
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Le token Telegram n'est pas défini !")

DB_FILE = "tournoi.db"
TEAMS = ["PSG","Real Madrid","Chelsea","Barça","Bayern","Man City","Man United",
         "Liverpool","Juventus","Milan AC","Inter","Arsenal","Atlético Madrid",
         "Dortmund","Napoli","Tottenham"]
ADMIN_IDS = [6357925694]        # Ton ID Telegram
GROUP_ID = -1002365829730       # ID du groupe Telegram
CHANNEL_ID = -1002934569853     # ID du canal Telegram
MAX_PLAYERS = 16                # Max joueurs par ligue

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
db_lock = Lock()

# ====== BASE DE DONNÉES ======
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS joueurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            username TEXT,
            nom TEXT,
            equipe TEXT,
            whatsapp TEXT,
            code TEXT,
            ligue TEXT,
            statut TEXT DEFAULT 'Qualifié'
            )""")
c.execute("""CREATE TABLE IF NOT EXISTS ligues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER
            )""")
conn.commit()

# ====== MENU PRINCIPAL ======
def menu_principal():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📝 S'inscrire au tournoi", callback_data="inscription"))
    markup.add(InlineKeyboardButton("📊 Voir mon statut", callback_data="statut"))
    markup.add(InlineKeyboardButton("📋 Participants", callback_data="participants"))
    markup.add(InlineKeyboardButton("❓ Comment fonctionne le bot", callback_data="help"))
    markup.add(InlineKeyboardButton("📢 Canal officiel"https://t.me/ytabdNbZ0qJlZWU0"))
    return markup

# ====== START ======
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Bienvenue au tournoi eFootball !", reply_markup=menu_principal())

# ====== CALLBACK ======
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == "inscription":
        bot.send_message(call.message.chat.id, "Quel est ton nom d’utilisateur eFootball ?")
        bot.register_next_step_handler(call.message, get_nom)

    elif call.data == "statut":
        bot.send_message(call.message.chat.id, "Entre ton code de participation :")
        bot.register_next_step_handler(call.message, get_code_status)

    elif call.data.startswith("team_"):
        _, nom, equipe, ligue_name = call.data.split("_")
        bot.send_message(call.message.chat.id, "Quel est ton numéro WhatsApp (+225...) ?")
        bot.register_next_step_handler(call.message, lambda msg: save_inscription(msg, nom, equipe, ligue_name))

    elif call.data == "participants":
        send_participants(call.message.chat.id)

    elif call.data == "help":
        msg = ("ℹ️ Fonctionnement du bot :\n\n"
               "1️⃣ S’inscrire au tournoi → Choisir ton équipe et entrer ton WhatsApp.\n"
               "2️⃣ Voir mon statut → Vérifier ton code de participation et statut.\n"
               "3️⃣ Participants → Voir la liste des participants.\n"
               "⚠️ Un utilisateur ne peut s’inscrire qu’une seule fois par ligue.\n"
               "Le bot envoie les inscriptions et tirages dans le groupe et le canal officiel.")
        bot.send_message(call.message.chat.id, msg)

# ====== INSCRIPTION ======
def get_nom(message):
    nom = message.text
    with db_lock:
        # Déterminer la ligue actuelle
        c.execute("SELECT numero FROM ligues ORDER BY numero DESC LIMIT 1")
        row = c.fetchone()
        if not row:
            ligue_num = 1
            c.execute("INSERT INTO ligues (numero) VALUES (?)", (ligue_num,))
            conn.commit()
        else:
            c.execute("SELECT COUNT(*) FROM joueurs WHERE ligue=?", (f"L{row[0]}",))
            count = c.fetchone()[0]
            if count >= MAX_PLAYERS:
                ligue_num = row[0] + 1
                c.execute("INSERT INTO ligues (numero) VALUES (?)", (ligue_num,))
                conn.commit()
            else:
                ligue_num = row[0]
        ligue_name = f"L{ligue_num}"

        # Vérifier équipes disponibles
        c.execute("SELECT equipe FROM joueurs WHERE ligue=?", (ligue_name,))
        used_teams = [r[0] for r in c.fetchall()]
    available_teams = [team for team in TEAMS if team not in used_teams]
    if not available_teams:
        bot.send_message(message.chat.id, "Toutes les équipes sont prises pour cette ligue !")
        return

    keyboard = InlineKeyboardMarkup()
    for team in available_teams:
        keyboard.add(InlineKeyboardButton(team, callback_data=f"team_{nom}_{team}_{ligue_name}"))

    bot.send_message(message.chat.id, "Choisis ton équipe :", reply_markup=keyboard)

def save_inscription(message, nom, equipe, ligue_name):
    whatsapp = message.text
    username = message.from_user.username or message.from_user.first_name
    with db_lock:
        # Vérifier doublon
        c.execute("SELECT * FROM joueurs WHERE telegram_id=? AND ligue=?", (message.from_user.id, ligue_name))
        if c.fetchone():
            bot.send_message(message.chat.id, "❌ Tu es déjà inscrit dans cette ligue !")
            return
        code = str(random.randint(1000,9999))
        c.execute("INSERT INTO joueurs (telegram_id, username, nom, equipe, whatsapp, code, ligue) VALUES (?,?,?,?,?,?,?)",
                  (message.from_user.id, username, nom, equipe, whatsapp, code, ligue_name))
        conn.commit()

    # Message récapitulatif à l'utilisateur
    msg_user = (f"✅ Inscription réussie !\n"
                f"Nom : {nom}\nÉquipe : {equipe}\nWhatsApp : {whatsapp}\n"
                f"Code : {code}\nLigue : {ligue_name}\n"
                f"👉 Rejoins le canal officiel : https://t.me/clicpourrejointicitoites")
    bot.send_message(message.chat.id, msg_user)

    # Envoyer message dans groupe et canal
    msg = f"📢 Nouvelle inscription !\n@{username} - {nom} - {equipe} - {whatsapp} - {ligue_name}"
    bot.send_message(GROUP_ID, msg)
    bot.send_message(CHANNEL_ID, msg)

    # Tirage si 16 joueurs
    with db_lock:
        c.execute("SELECT * FROM joueurs WHERE ligue=?", (ligue_name,))
        joueurs = c.fetchall()
    if len(joueurs) == MAX_PLAYERS:
        tirage_ligue(ligue_name, joueurs)

# ====== TIRAGE ======
def tirage_ligue(ligue_name, joueurs):
    random.shuffle(joueurs)
    msg = f"🎮 Tirage {ligue_name} - Matchs\n\n"
    for i in range(0, len(joueurs), 2):
        if i+1 < len(joueurs):
            msg += f"@{joueurs[i][2]} ({joueurs[i][4]}) vs @{joueurs[i+1][2]} ({joueurs[i+1][4]})\n"
        else:
            msg += f"@{joueurs[i][2]} ({joueurs[i][4]}) reçoit un bye\n"
    bot.send_message(GROUP_ID, msg)
    bot.send_message(CHANNEL_ID, msg)

# ====== STATUT ======
def get_code_status(message):
    code = message.text
    with db_lock:
        c.execute("SELECT nom,equipe,statut,ligue FROM joueurs WHERE code=?", (code,))
        row = c.fetchone()
    if row:
        bot.send_message(message.chat.id, f"Nom : {row[0]}\nÉquipe : {row[1]}\nStatut : {row[2]}\nLigue : {row[3]}")
    else:
        bot.send_message(message.chat.id, "❌ Code invalide !")

# ====== PARTICIPANTS ======
def send_participants(chat_id):
    with db_lock:
        c.execute("SELECT nom,equipe,ligue,statut,username FROM joueurs ORDER BY ligue,nom")
        rows = c.fetchall()
    if not rows:
        bot.send_message(chat_id, "Aucun participant pour le moment.")
        return
    msg = "🎮 Participants au tournoi :\n\n"
    for r in rows:
        msg += f"Nom : {r[0]} | Équipe : {r[1]} | Ligue : {r[2]} | Statut : {r[3]} | Telegram : @{r[4]}\n"
    bot.send_message(chat_id, msg)

# ====== ADMIN ======
@bot.message_handler(commands=['equipe'])
def set_statut(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ Tu n’es pas autorisé !")
        return
    try:
        args = message.text.split()
        nom = args[1]
        statut = args[2]
        if statut not in ["Éliminé", "Qualifié"]:
            bot.send_message(message.chat.id, "⚠️ Statut invalide (Éliminé ou Qualifié).")
            return
        with db_lock:
            c.execute("UPDATE joueurs SET statut=? WHERE nom=?", (statut, nom))
            conn.commit()
        bot.send_message(message.chat.id, f"{nom} est maintenant {statut}")
    except:
        bot.send_message(message.chat.id, "Usage: /equipe <nom> <Éliminé/Qualifié>")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ Pas autorisé !")
        return
    try:
        text = message.text.split(" ", 1)[1]
        with db_lock:
            c.execute("SELECT telegram_id FROM joueurs")
            users = c.fetchall()
        for u in users:
            try:
                bot.send_message(u[0], f"📢 Message du bot :\n\n{text}")
            except:
                pass
        bot.send_message(message.chat.id, "✅ Broadcast envoyé à tous les participants.")
    except IndexError:
        bot.send_message(message.chat.id, "Usage: /broadcast <message>")

# ====== WEBHOOK FLASK ======
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "", 200

# ====== LANCER LE BOT ======
if __name__ == "__main__":
    bot.remove_webhook()
    PORT = int(os.environ.get("PORT", 5000))
    SERVICE_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}"
    bot.set_webhook(url=f"{SERVICE_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=PORT)
