import os
import telebot
from telebot import types
import json

BOT_TOKEN = os.getenv("BOT_TOKEN", "8377020931:AAHGv8FI4i4xJjNUuUEN3Gp2Tjwn9FG7a2c")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6357925694"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1002884958871"))
GROUP_LINK = "https://t.me/htclicpourrejointicitoites"

bot = telebot.TeleBot(BOT_TOKEN)

DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

data = load_data()

LANGS = {
    "fr": {"welcome":"👋 Bienvenue sur le Bot eFootball !","menu":"📍 Menu principal","inscription":"📝 Inscription","infos":"ℹ️ Mes infos","tournoi":"🏆 Tournoi","classement":"📊 Classement","support":"📩 Support","lang":"🌍 Changer de langue","inscription_done":"🎉 Inscription validée !\n👤 Nom : {nom}\n🆔 ID eFootball : {id}\n🎮 Pseudo : {pseudo}\n✅ Ton inscription a été envoyée au canal officiel.\n➡️ Rejoins le groupe : "+GROUP_LINK},
    "en": {"welcome":"👋 Welcome to the eFootball Bot!","menu":"📍 Main menu","inscription":"📝 Register","infos":"ℹ️ My info","tournoi":"🏆 Tournament","classement":"📊 Ranking","support":"📩 Support","lang":"🌍 Change language","inscription_done":"🎉 Registration completed!\n👤 Name: {nom}\n🆔 eFootball ID: {id}\n🎮 Username: {pseudo}\n✅ Your registration has been sent to the official channel.\n➡️ Join the group: "+GROUP_LINK},
    "es": {"welcome":"👋 ¡Bienvenido al Bot de eFootball!","menu":"📍 Menú principal","inscription":"📝 Inscripción","infos":"ℹ️ Mi información","tournoi":"🏆 Torneo","classement":"📊 Clasificación","support":"📩 Soporte","lang":"🌍 Cambiar idioma","inscription_done":"🎉 ¡Inscripción completada!\n👤 Nombre: {nom}\n🆔 ID de eFootball: {id}\n🎮 Usuario: {pseudo}\n✅ Tu inscripción ha sido enviada al canal oficial.\n➡️ Únete al grupo: "+GROUP_LINK}
}

def get_lang(user_id):
    return data.get(str(user_id), {}).get("lang", "fr")

@bot.message_handler(commands=["start"])
def start(message):
    user_id = str(message.chat.id)
    if user_id not in data:
        data[user_id] = {"lang": "fr"}
        save_data(data)
    lang = get_lang(user_id)
    txt = LANGS[lang]["welcome"]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(LANGS[lang]["inscription"], LANGS[lang]["infos"])
    markup.add(LANGS[lang]["tournoi"], LANGS[lang]["classement"])
    markup.add(LANGS[lang]["support"], LANGS[lang]["lang"])
    bot.send_message(message.chat.id, txt, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in [LANGS[l]["inscription"] for l in LANGS])
def inscription(message):
    lang = get_lang(message.chat.id)
    msg = bot.send_message(message.chat.id, "👤 Ton nom ?")
    bot.register_next_step_handler(msg, ask_name)

def ask_name(message):
    user_id = str(message.chat.id)
    data[user_id]["nom"] = message.text
    msg = bot.send_message(message.chat.id, "🆔 Ton ID eFootball ?")
    bot.register_next_step_handler(msg, ask_id)

def ask_id(message):
    user_id = str(message.chat.id)
    data[user_id]["id"] = message.text
    msg = bot.send_message(message.chat.id, "🎮 Ton pseudo ?")
    bot.register_next_step_handler(msg, ask_pseudo)

def ask_pseudo(message):
    user_id = str(message.chat.id)
    data[user_id]["pseudo"] = message.text
    save_data(data)
    lang = get_lang(message.chat.id)
    txt = LANGS[lang]["inscription_done"].format(
        nom=data[user_id]["nom"], id=data[user_id]["id"], pseudo=data[user_id]["pseudo"]
    )
    bot.send_message(message.chat.id, txt)
    bot.send_message(CHANNEL_ID, f"📢 Nouvelle inscription :\n👤 {data[user_id]['nom']}\n🆔 {data[user_id]['id']}\n🎮 {data[user_id]['pseudo']}")

@bot.message_handler(func=lambda m: m.text in [LANGS[l]["lang"] for l in LANGS])
def change_lang(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🇫🇷 Français", callback_data="lang_fr"))
    markup.add(types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"))
    markup.add(types.InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es"))
    bot.send_message(message.chat.id, "Choisis ta langue :", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def set_lang(call):
    user_id = str(call.message.chat.id)
    lang = call.data.split("_")[1]
    data[user_id]["lang"] = lang
    save_data(data)
    bot.answer_callback_query(call.id, "✅ Langue changée !")
    start(call.message)

if __name__ == "__main__":
    bot.polling(none_stop=True)