import os
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    app_flask.run(host='0.0.0.0', port=10000)

TEMP_FOLDER = "downloads"
os.makedirs(TEMP_FOLDER, exist_ok=True)
user_files = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a file and I’ll help you rename it!")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document
    if not file:
        await update.message.reply_text("Please send the file as a document.")
        return

    file_id = file.file_id
    file_name = file.file_name or "file"
    user_id = update.message.from_user.id

    # Store in context.user_data instead of global dict (safer)
    context.user_data["file_info"] = {
        "file_id": file_id,
        "original_name": file_name,
        "ext": os.path.splitext(file_name)[1],
    }

    await update.message.reply_text(
        f"Original File: `{file_name}`\n\nSend me the new name **(without extension)**.",
        parse_mode="Markdown"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if "file_info" not in context.user_data:
        await update.message.reply_text("No file found. Please send a file first.")
        return

    new_name = update.message.text.strip()
    ext = context.user_data["file_info"]["ext"]
    full_name = new_name + ext
    context.user_data["file_info"]["new_name"] = full_name

    keyboard = [
        [InlineKeyboardButton("✅ Confirm Rename", callback_data="confirm")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ]
    await update.message.reply_text(
        f"New filename will be: `{full_name}`\nConfirm?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if "file_info" not in context.user_data:
        await query.edit_message_text("❌ Session expired. Please send the file again.")
        return

    if query.data == "cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Rename cancelled.")
        return

    if query.data == "confirm":
        data = context.user_data.pop("file_info")
        file = await context.bot.get_file(data["file_id"])

        old_path = os.path.join(TEMP_FOLDER, "temp" + data["ext"])
        new_path = os.path.join(TEMP_FOLDER, data["new_name"])

        await file.download_to_drive(old_path)
        os.rename(old_path, new_path)

        await context.bot.send_document(chat_id=query.message.chat.id, document=open(new_path, 'rb'))
        await query.edit_message_text(f"✅ File renamed and sent as `{data['new_name']}`.", parse_mode="Markdown")
        os.remove(new_path)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button))
    print("Bot is running...")
    app.run_polling()
