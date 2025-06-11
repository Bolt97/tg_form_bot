import os
import datetime
from html import escape
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# Загружаем переменные окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))

# Состояния для ConversationHandler
FIO, PHONE, VEHICLE, PHOTO_LIST = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚗 <b>Добро пожаловать!</b>\n\n"
        "Этот бот собирает заявки на участие в <b>автомобильной выставке BALALAYKA PICNIC </b>.\n\n"
        "<b>21.06.2025</b>\n\n"
        "📋 Сейчас мы последовательно соберём ваши данные.\n"
        "<i>В любой момент можно отменить командой /cancel</i>",
        parse_mode="HTML"
    )
    await update.message.reply_text("👤 Введите ваши <b>ФИО</b>:", parse_mode="HTML")
    return FIO

async def get_fio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["fio"] = update.message.text.strip()
    await update.message.reply_text("📞 Введите ваш <b>номер телефона</b>:", parse_mode="HTML")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text.strip()
    await update.message.reply_text("🚘 Введите <b>марку и год</b> авто/мото:", parse_mode="HTML")
    return VEHICLE

async def get_vehicle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["vehicle"] = update.message.text.strip()
    context.user_data["photos"] = []
    await update.message.reply_text(
        "📸 Отправьте <b>до 3-х фото</b> вашего авто/мото.\n\n"
        "Когда закончите — напишите <code>готово</code>.",
        parse_mode="HTML"
    )
    return PHOTO_LIST

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photos = context.user_data.get("photos", [])
    if len(photos) >= 3:
        await update.message.reply_text("❗ Лимит — 3 фото. Напишите <code>готово</code>.", parse_mode="HTML")
        return PHOTO_LIST

    file_id = update.message.photo[-1].file_id
    photos.append(file_id)
    context.user_data["photos"] = photos

    await update.message.reply_text(f"✅ Принято фото {len(photos)} из 3.")
    return PHOTO_LIST

async def confirm_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().strip()
    if text not in ["готово", "всё", "все", "готов"]:
        await update.message.reply_text("ℹ️ Напишите <code>готово</code>, когда закончите с фото.", parse_mode="HTML")
        return PHOTO_LIST

    photos = context.user_data.get("photos", [])
    if not photos:
        await update.message.reply_text("❗ Не получено ни одного фото.")
        return PHOTO_LIST

    user = update.effective_user
    safe_caption = escape(
        f"📬 Новая заявка на выставку:\n\n"
        f"👤 ФИО: {context.user_data['fio']}\n"
        f"📞 Телефон: {context.user_data['phone']}\n"
        f"🚗 Техника: {context.user_data['vehicle']}\n"
        f"🕒 Время: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"🆔 @{user.username or user.id}"
    )

    await context.bot.send_photo(
        chat_id=GROUP_CHAT_ID,
        photo=photos[0],
        caption=f"<pre>{safe_caption}</pre>",
        parse_mode="HTML"
    )

    for photo in photos[1:]:
        await context.bot.send_photo(chat_id=GROUP_CHAT_ID, photo=photo)

    await update.message.reply_text("✅ Заявка отправлена! Спасибо за участие.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Заявка отменена. Вы можете начать заново командой /start.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fio)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            VEHICLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_vehicle)],
            PHOTO_LIST: [
                MessageHandler(filters.PHOTO, get_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_photos),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()