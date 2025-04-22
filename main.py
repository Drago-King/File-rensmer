import os
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

print("PTB VERSION:", telegram.__version__)  # Debugging help

BOT_TOKEN = os.getenv("BOT_TOKEN")
TEMP_FOLDER = "downloads"
os.makedirs(TEMP_FOLDER, exist_ok=True)

user_files = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a file and I’ll help you rename it!")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document or update.message.video or update.message.audio
    if not file:
        await update.message.reply_text("Please send a valid document, video, or audio file.")
        return

    file_id = file.file_id
    file_name = file.file_name or "file"

    user_id = update.message.from_user.id
    user_files[user_id] = {
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
    if user_id not in user_files:
        return

    new_name = update.message.text.strip()
    ext = user_files[user_id]["ext"]
    full_name = new_name + ext
    user_files[user_id]["new_name"] = full_name

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
    user_id = query.from_user.id

    if query.data == "cancel":
        user_files.pop(user_id, None)
        await query.edit_message_text("❌ Rename cancelled.")
        return

    if query.data == "confirm":
        if user_id not in user_files:
            await query.edit_message_text("Session expired. Please resend your file.")
            return

        data = user_files.pop(user_id)
        file = await context.bot.get_file(data["file_id"])
        old_path = os.path.join(TEMP_FOLDER, "temp" + data["ext"])
        new_path = os.path.join(TEMP_FOLDER, data["new_name"])

        await file.download_to_drive(old_path)
        os.rename(old_path, new_path)

        await context.bot.send_document(chat_id=query.message.chat_id, document=open(new_path, 'rb'))
        await query.edit_message_text(f"✅ File renamed and sent as `{data['new_name']}`.", parse_mode="Markdown")
        os.remove(new_path)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.Video.ALL | filters.Audio.ALL, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button))
    print("Bot is running...")
    app.run_polling()
