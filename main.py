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

DB_FILE = "cashback.db"
ADMIN_IDS = [6357925694]        # Ton ID Telegram
CHANNEL_URL = "https://t.me/kingpronosbs"  # Ton canal
GROUP_URL = "https://t.me/htclicpourrejointicitoites"      # Ton groupe
SITE_URL = "https://reffpa.com/L?tag=d_3684565m_97c_&site=3684565&ad=97&r=bienvenuaridtlrbj"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
db_lock = Lock()

# ====== BASE DE DONNÉES ======
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS demandes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    bookmaker TEXT,
    bookmaker_id TEXT,
    statut TEXT DEFAULT 'En attente',
    code_cashback TEXT,
    montant INTEGER DEFAULT 0
)
""")
conn.commit()

# ====== MENUS ======
def menu_principal():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💰 Cashback", callback_data="cashback"))
    markup.add(InlineKeyboardButton("📢 Rejoindre canal", url=CHANNEL_URL))
    markup.add(InlineKeyboardButton("🌐 Visiter le site", url=SITE_URL))
    markup.add(InlineKeyboardButton("🆘 Support", callback_data="support"))
    markup.add(InlineKeyboardButton("❓ Aide", callback_data="aide"))
    markup.add(InlineKeyboardButton("👥 Rejoindre le groupe", url=GROUP_URL))
    return markup

def bookmaker_buttons():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("1️⃣ 1xBet", callback_data="bookmaker_1xbet"),
        InlineKeyboardButton("2️⃣ Melbet", callback_data="bookmaker_melbet"),
        InlineKeyboardButton("3️⃣ BetWinner", callback_data="bookmaker_betwinner")
    )
    return markup

# ====== START ======
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Bienvenue sur le bot Cashback !\n\nQuel bookmaker utilisez-vous ?",
        reply_markup=bookmaker_buttons()
    )

# ====== CALLBACK HANDLER ======
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data.startswith("bookmaker_"):
        bookmaker = call.data.split("_")[1]
        bot.send_message(call.message.chat.id, f"📌 Entrez votre ID {bookmaker} :")
        bot.register_next_step_handler(call.message, save_demande, call.from_user.id, bookmaker)

    elif call.data == "cashback":
        show_cashback(call.message)

    elif call.data == "support":
        bot.send_message(call.message.chat.id, f"🆘 Contacte l'admin en PV : @{bot.get_me().username}")

    elif call.data == "aide":
        bot.send_message(call.message.chat.id,
                         "❓ Pour réclamer votre cashback :\n"
                         "1. Choisissez votre bookmaker\n"
                         "2. Saisissez votre ID\n"
                         "3. Attendez l'acceptation de l'admin\n"
                         "4. Recevez votre code cashback")

# ====== SAVE DEMANDE ======
def save_demande(message, user_id, bookmaker):
    if message.from_user.id != user_id:
        return
    bookmaker_id = message.text.strip()
    username = message.from_user.username or message.from_user.first_name

    with db_lock:
        c.execute("INSERT INTO demandes (user_id, username, bookmaker, bookmaker_id) VALUES (?,?,?,?)",
                  (user_id, username, bookmaker, bookmaker_id))
        demande_id = c.lastrowid
        conn.commit()

    bot.send_message(message.chat.id, "✅ Votre demande a été enregistrée. Veuillez patienter que l'admin la valide.")

    # Notification admin
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Accepter", callback_data=f"accepter_{demande_id}"),
        InlineKeyboardButton("❌ Rejeter", callback_data=f"rejeter_{demande_id}")
    )
    bot.send_message(
        ADMIN_IDS[0],
        f"📢 Nouvelle demande\nNom : {username}\nBookmaker : {bookmaker}\nID : {bookmaker_id}\nStatut : En attente\nLien groupe : {GROUP_URL}",
        reply_markup=markup
    )

# ====== SHOW CASHBACK ======
def show_cashback(message):
    with db_lock:
        c.execute("SELECT montant FROM demandes WHERE user_id=? AND statut='Acceptée'", (message.from_user.id,))
        rows = c.fetchall()
    if not rows:
        bot.send_message(message.chat.id, "💰 Vous n'avez aucun cashback disponible.")
    else:
        total = sum([r[0] for r in rows])
        bot.send_message(message.chat.id, f"💰 Votre cashback total : {total} CFA")

# ====== ADMIN ACCEPT/REJECT ======
@bot.callback_query_handler(func=lambda call: call.data.startswith("accepter_") or call.data.startswith("rejeter_"))
def admin_accept_reject(call):
    if call.from_user.id not in ADMIN_IDS:
        return

    demande_id = int(call.data.split("_")[1])
    if call.data.startswith("accepter_"):
        code_cash = ''.join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=8))
        with db_lock:
            c.execute("UPDATE demandes SET statut='Acceptée', code_cashback=? WHERE id=?", (code_cash, demande_id))
            conn.commit()
            c.execute("SELECT user_id, username FROM demandes WHERE id=?", (demande_id,))
            row = c.fetchone()
        if row:
            user_id, username = row
            bot.send_message(user_id, f"✅ Votre demande a été acceptée !\nVotre code cashback : {code_cash}")
        bot.edit_message_text("✅ Demande acceptée", call.message.chat.id, call.message.message_id)
    else:
        with db_lock:
            c.execute("UPDATE demandes SET statut='Rejetée' WHERE id=?", (demande_id,))
            conn.commit()
            c.execute("SELECT user_id FROM demandes WHERE id=?", (demande_id,))
            row = c.fetchone()
        if row:
            bot.send_message(row[0], "❌ Votre demande a été rejetée.")
        bot.edit_message_text("❌ Demande rejetée", call.message.chat.id, call.message.message_id)

# ====== ADMIN AJOUT MONTANT ======
@bot.message_handler(commands=['ajouter_montant'])
def add_montant(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        _, demande_id, montant = message.text.split()
        demande_id, montant = int(demande_id), int(montant)
        with db_lock:
            c.execute("UPDATE demandes SET montant=? WHERE id=?", (montant, demande_id))
            conn.commit()
        bot.send_message(message.chat.id, f"✅ Montant {montant} CFA ajouté à la demande {demande_id}.")
    except:
        bot.send_message(message.chat.id, "Usage: /ajouter_montant <id_demande> <montant>")

# ====== WEBHOOK FLASK ======
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "", 200

# ====== PAGE TEST ======
@app.route("/", methods=["GET"])
def index():
    return "✅ Bot Cashback est en ligne !", 200

# ====== LANCER LE BOT ======
if __name__ == "__main__":
    bot.remove_webhook()
    PORT = int(os.environ.get("PORT", 5000))
    SERVICE_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}"
    bot.set_webhook(url=f"{SERVICE_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=PORT)
