import telebot
import sqlite3, random, os
from flask import Flask, request

# --- Configuration ---
TOKEN = os.environ.get("8377020931:AAHGv8FI4i4xJjNUuUEN3Gp2Tjwn9FG7a2c")  # Token depuis variable d'environnement Render
URL = os.environ.get("WEBHOOK_URL")  # L'URL publique de ton Render Web Service
DB_FILE = "tournoi.db"
TEAMS = ["PSG","Real Madrid","Chelsea","Barça","Bayern","Man City","Man United",
         "Liverpool","Juventus","Milan AC","Inter","Arsenal","Atlético Madrid",
         "Dortmund","Napoli","Tottenham"]
ADMIN_IDS = [6357925694]  # Ton ID Telegram

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

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

# --- Commande start ---
@bot.message_handler(commands=['start'])
def start(message):
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📝 S'inscrire", callback_data="inscription"))
    keyboard.add(InlineKeyboardButton("📊 Voir mon statut", callback_data="statut"))
    keyboard.add(InlineKeyboardButton("📢 Canal officiel", url="https://t.me/clicpourrejointicitoites"))
    bot.send_message(message.chat.id, "Bienvenue au tournoi eFootball !", reply_markup=keyboard)

# --- Autres handlers restent identiques ---
# Copie tes fonctions callback, get_nom, get_equipe, save_inscription, get_code_status, set_statut, tirer_matchs ici.

# --- Webhook pour Flask ---
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "", 200

if __name__ == "__main__":
    # Supprime tout long polling
    bot.remove_webhook()
    bot.set_webhook(url=f"{URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
