# main.py
import os
import random
import sqlite3
from threading import Lock
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- Configuration ---
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Le token Telegram n'est pas défini !")

DB_FILE = "tournoi.db"
TEAMS = ["PSG","Real Madrid","Chelsea","Barça","Bayern","Man City","Man United",
         "Liverpool","Juventus","Milan AC","Inter","Arsenal","Atlético Madrid",
         "Dortmund","Napoli","Tottenham"]
ADMIN_IDS = [6357925694]  # Ton ID Telegram

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
db_lock = Lock()

# --- Base SQLite ---
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

# --- Commande /start ---
@bot.message_handler(commands=['start'])
def start(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📝 S'inscrire", callback_data="inscription"))
    keyboard.add(InlineKeyboardButton("📊 Voir mon statut", callback_data="statut"))
    keyboard.add(InlineKeyboardButton("📢 Canal officiel", url="https://t.me/clicpourrejointicitoites"))
    bot.send_message(message.chat.id, "Bienvenue au tournoi eFootball !", reply_markup=keyboard)

# --- Callback buttons fusionné ---
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == "inscription":
        bot.send_message(call.message.chat.id, "Quel est ton nom d’utilisateur eFootball ?")
        bot.register_next_step_handler(call.message, get_nom)

    elif call.data == "statut":
        bot.send_message(call.message.chat.id, "Entre ton code de participation :")
        bot.register_next_step_handler(call.message, get_code_status)

    elif call.data.startswith("team_"):
        _, nom, equipe = call.data.split("_")
        bot.send_message(call.message.chat.id, "Quel est ton numéro WhatsApp (+225...) ?")
        bot.register_next_step_handler(call.message, lambda msg: save_inscription(msg, nom, equipe))

# --- Inscription ---
def get_nom(message):
    nom = message.text
    with db_lock:
        c.execute("SELECT equipe FROM joueurs WHERE ligue=(SELECT COALESCE(MAX(numero),1) FROM ligues)")
        used_teams = [row[0] for row in c.fetchall()]
    available_teams = [team for team in TEAMS if team not in used_teams]

    if not available_teams:
        bot.send_message(message.chat.id, "Toutes les équipes sont prises, attends la prochaine ligue.")
        return

    keyboard = InlineKeyboardMarkup()
    for team in available_teams:
        keyboard.add(InlineKeyboardButton(team, callback_data=f"team_{nom}_{team}"))

    bot.send_message(message.chat.id, "Choisis ton équipe :", reply_markup=keyboard)

def save_inscription(message, nom, equipe):
    whatsapp = message.text
    code = str(random.randint(1000, 9999))

    with db_lock:
        c.execute("SELECT MAX(numero) FROM ligues")
        row = c.fetchone()
        if row[0] is None or c.execute("SELECT COUNT(*) FROM joueurs WHERE ligue=?", (row[0],)).fetchone()[0] >= 16:
            ligue_num = 1 if row[0] is None else row[0] + 1
            c.execute("INSERT INTO ligues (numero) VALUES (?)", (ligue_num,))
            conn.commit()
        else:
            ligue_num = row[0]

        c.execute("INSERT INTO joueurs (telegram_id, nom, equipe, whatsapp, code, ligue) VALUES (?,?,?,?,?,?)",
                  (message.from_user.id, nom, equipe, whatsapp, code, ligue_num))
        conn.commit()

    bot.send_message(message.chat.id, f"""✅ Inscription réussie !

Nom : {nom}
Équipe : {equipe}
WhatsApp : {whatsapp}
Code participation : {code}

👉 Rejoins le canal officiel : https://t.me/clicpourrejointicitoites
""")

# --- Voir statut ---
def get_code_status(message):
    code = message.text
    with db_lock:
        c.execute("SELECT nom,equipe,statut,ligue FROM joueurs WHERE code=?", (code,))
        row = c.fetchone()
    if row:
        bot.send_message(message.chat.id, f"""Nom : {row[0]}
Équipe : {row[1]}
Statut : {row[2]}
Ligue : {row[3]}""")
    else:
        bot.send_message(message.chat.id, "❌ Code invalide !")

# --- Admin ---
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

@bot.message_handler(commands=['ligue'])
def tirer_matchs(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ Tu n’es pas autorisé !")
        return
    try:
        ligue_num = int(message.text.split()[1])
        with db_lock:
            participants = c.execute("SELECT nom,equipe FROM joueurs WHERE ligue=? AND statut='Qualifié'", (ligue_num,)).fetchall()
        random.shuffle(participants)
        msg = f"🎮 Ligue {ligue_num} - Matchs\n\n"
        for i in range(0, len(participants), 2):
            if i + 1 < len(participants):
                msg += f"{participants[i][0]} ({participants[i][1]}) vs {participants[i+1][0]} ({participants[i+1][1]})\n"
            else:
                msg += f"{participants[i][0]} ({participants[i][1]}) reçoit un bye\n"
        bot.send_message(message.chat.id, msg)
    except:
        bot.send_message(message.chat.id, "Usage: /ligue <numero>")

# --- Webhook Flask ---
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "", 200

# --- Lancer le bot ---
if __name__ == "__main__":
    bot.remove_webhook()
    PORT = int(os.environ.get("PORT", 5000))
    SERVICE_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}"
    bot.set_webhook(url=f"{SERVICE_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=PORT)
