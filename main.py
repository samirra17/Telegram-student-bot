import os
import sqlite3
import datetime
from telegram import Update, ReplyKeyboardMarkup, Document
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    ConversationHandler, CallbackContext
)

# CONFIGURATION
BOT_TOKEN = '8127190486:AAEPhd00S-Up4Z3HdP5oXHcc4IQdSp0xfQM'
ADMIN_ID = 5112046216  # Replace with your Telegram ID
BOOKS_DIR = 'books'

# Ensure books directory exists
os.makedirs(BOOKS_DIR, exist_ok=True)

# STATE ENUMS
ASK_NAME, ASK_ID, MAIN_MENU, SCHEDULE_DAY, BOOK_SUBJECT, FEEDBACK_TEXT, \
    ADD_HOMEWORK_SUBJECT, ADD_HOMEWORK_TEXT, ADD_HOMEWORK_DATE, BOOK_UPLOAD_SUBJECT = range(10)

# Connect to database
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()

# Create tables if not exist
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY, name TEXT, student_id TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS feedbacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER, text TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS deadlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT, text TEXT, due_date TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT, file_path TEXT
)''')
conn.commit()

# Dummy schedule
schedule_data = {
    'Monday': 'Calculus 2\n 9:00 - 11:25\n room:B202\n  German\n 11:30 - 12:55 \n room:B202',
    'Tuesday': 'Physical education\n 9:00 - 10:40\n room:Sport Hall\n  Discrete math\n 10:45 - 12:55 \n room:B202',
    'Wednesday': 'Russian Language\n 9:00 - 10:40\n room:B203\n  Programming language\n 10:45 - 12:55 \n room:B213',
    'Thursday': 'German\n 9:00 - 10:40\n room:B203\n  Programming language\n 10:45 - 12:55 \n room:B213 \n LUNCH \n 13:00-13:45 \n Calculus 2 \n 13:45-15:55 \n B103',
    'Friday': 'Russian Language\n 9:00 - 10:40\n room:B101\n  Discrete math\n 10:45 - 12:55 \n room:B205 \n LUNCH \n 13:00-14:25 \n Elective\n 14:30-17:25 \n B103'
}


def start(update: Update, context: CallbackContext):
    update.message.reply_text("Welcome! Please enter your full name:")
    return ASK_NAME


def ask_name(update: Update, context: CallbackContext):
    context.user_data['name'] = update.message.text
    update.message.reply_text("Now enter your student ID:")
    return ASK_ID


def ask_id(update: Update, context: CallbackContext):
    student_id = update.message.text
    telegram_id = update.message.from_user.id
    name = context.user_data['name']
    cursor.execute("INSERT OR REPLACE INTO users (telegram_id, name, student_id) VALUES (?, ?, ?)",
                   (telegram_id, name, student_id))
    conn.commit()
    update.message.reply_text("✅ Registered!", reply_markup=main_menu(telegram_id))
    return MAIN_MENU


def main_menu(user_id):
    keyboard = [['📅 Schedule', '📚 Books'], ['⏰ Deadlines', '👤 Profile'], ['📝 Feedback']]
    if user_id == ADMIN_ID:
        keyboard.append(['➕ Add Homework', '📤 Upload Book'])
    keyboard.append(['🏠 Main Menu'])  # Always show main menu button
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def back_to_menu(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    update.message.reply_text("Returning to main menu...", reply_markup=main_menu(user_id))
    return MAIN_MENU


def handle_menu(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text

    if text == '🏠 Main Menu':
        return back_to_menu(update, context)

    if text == '📅 Schedule':
        update.message.reply_text("Choose a day:", reply_markup=ReplyKeyboardMarkup(
            [['Monday', 'Tuesday'], ['Wednesday', 'Thursday', 'Friday'], ['🏠 Main Menu']],
            resize_keyboard=True
        ))
        return SCHEDULE_DAY

    elif text == '📚 Books':
        cursor.execute("SELECT DISTINCT subject FROM books")
        subjects = cursor.fetchall()
        if subjects:
            keyboard = [[s[0]] for s in subjects]
            keyboard.append(['🏠 Main Menu'])
            update.message.reply_text("Choose a subject:", reply_markup=ReplyKeyboardMarkup(
                keyboard, resize_keyboard=True
            ))
            return BOOK_SUBJECT
        else:
            update.message.reply_text("No books available yet.", reply_markup=main_menu(user_id))
            return MAIN_MENU

    elif text == '⏰ Deadlines':
        if user_id == ADMIN_ID:
            update.message.reply_text("Enter subject:", reply_markup=ReplyKeyboardMarkup(
                [['🏠 Main Menu']], resize_keyboard=True
            ))
            return ADD_HOMEWORK_SUBJECT
        else:
            cursor.execute("SELECT subject, text, due_date FROM deadlines ORDER BY due_date ASC")
            rows = cursor.fetchall()
            if rows:
                message = "📚 Deadlines:\n"
                for row in rows:
                    message += f"\n{row[0]}: {row[1]} (Due: {row[2]})"
                update.message.reply_text(message, reply_markup=main_menu(user_id))
            else:
                update.message.reply_text("No deadlines found.", reply_markup=main_menu(user_id))
            return MAIN_MENU

    elif text == '➕ Add Homework' and user_id == ADMIN_ID:
        update.message.reply_text("Enter subject:", reply_markup=ReplyKeyboardMarkup(
            [['🏠 Main Menu']], resize_keyboard=True
        ))
        return ADD_HOMEWORK_SUBJECT

    elif text == '👤 Profile':
        cursor.execute("SELECT name, student_id FROM users WHERE telegram_id=?", (user_id,))
        result = cursor.fetchone()
        if result:
            name, student_id = result
            update.message.reply_text(
                f"👤 Name: {name}\n🆔 ID: {student_id}\n🎓 Group: MATMIE24",
                reply_markup=main_menu(user_id)
            )
        return MAIN_MENU

    elif text == '📝 Feedback':
        if user_id == ADMIN_ID:
            cursor.execute("SELECT text FROM feedbacks")
            feedbacks = cursor.fetchall()
            if feedbacks:
                msg = "\n\n".join(f"• {f[0]}" for f in feedbacks)
                update.message.reply_text(f"🗣 Feedbacks:\n\n{msg}", reply_markup=main_menu(user_id))
            else:
                update.message.reply_text("No feedback yet.", reply_markup=main_menu(user_id))
            return MAIN_MENU
        else:
            update.message.reply_text("Please write your feedback:", reply_markup=ReplyKeyboardMarkup(
                [['🏠 Main Menu']], resize_keyboard=True
            ))
            return FEEDBACK_TEXT

    elif text == '📤 Upload Book' and user_id == ADMIN_ID:
        update.message.reply_text("Enter subject for the book you're about to upload:",
                                  reply_markup=ReplyKeyboardMarkup(
                                      [['🏠 Main Menu']], resize_keyboard=True
                                  ))
        return BOOK_UPLOAD_SUBJECT

    return MAIN_MENU


def handle_schedule(update: Update, context: CallbackContext):
    if update.message.text == '🏠 Main Menu':
        return back_to_menu(update, context)

    day = update.message.text
    schedule = schedule_data.get(day, "No schedule available.")
    update.message.reply_text(f"📅 {day} Schedule:\n{schedule}", reply_markup=main_menu(update.message.from_user.id))
    return MAIN_MENU


def handle_book_subject(update: Update, context: CallbackContext):
    if update.message.text == '🏠 Main Menu':
        return back_to_menu(update, context)

    subject = update.message.text
    cursor.execute("SELECT file_path FROM books WHERE subject=?", (subject,))
    row = cursor.fetchone()
    if row:
        file_path = row[0]
        try:
            with open(file_path, 'rb') as file:
                # Using chunked upload for large files
                update.message.reply_document(
                    document=file,
                    filename=os.path.basename(file_path),
                    reply_markup=main_menu(update.message.from_user.id)
                )
        except Exception as e:
            update.message.reply_text(f"Error sending file: {str(e)}",
                                      reply_markup=main_menu(update.message.from_user.id))
    else:
        update.message.reply_text("No book found.", reply_markup=main_menu(update.message.from_user.id))
    return MAIN_MENU


def receive_feedback(update: Update, context: CallbackContext):
    if update.message.text == '🏠 Main Menu':
        return back_to_menu(update, context)

    user_id = update.message.from_user.id
    text = update.message.text
    cursor.execute("INSERT INTO feedbacks (telegram_id, text) VALUES (?, ?)", (user_id, text))
    conn.commit()
    update.message.reply_text("✅ Feedback saved!", reply_markup=main_menu(user_id))
    return MAIN_MENU


def add_hw_subject(update: Update, context: CallbackContext):
    if update.message.text == '🏠 Main Menu':
        return back_to_menu(update, context)

    context.user_data['subject'] = update.message.text
    update.message.reply_text("Enter homework details:", reply_markup=ReplyKeyboardMarkup(
        [['🏠 Main Menu']], resize_keyboard=True
    ))
    return ADD_HOMEWORK_TEXT


def add_hw_text(update: Update, context: CallbackContext):
    if update.message.text == '🏠 Main Menu':
        return back_to_menu(update, context)

    context.user_data['text'] = update.message.text
    update.message.reply_text("Enter deadline (YYYY-MM-DD):", reply_markup=ReplyKeyboardMarkup(
        [['🏠 Main Menu']], resize_keyboard=True
    ))
    return ADD_HOMEWORK_DATE


def add_hw_date(update: Update, context: CallbackContext):
    if update.message.text == '🏠 Main Menu':
        return back_to_menu(update, context)

    try:
        due_date = datetime.datetime.strptime(update.message.text, '%Y-%m-%d').date()
        cursor.execute("INSERT INTO deadlines (subject, text, due_date) VALUES (?, ?, ?)",
                       (context.user_data['subject'], context.user_data['text'], str(due_date)))
        conn.commit()
        update.message.reply_text("✅ Homework added.", reply_markup=main_menu(update.message.from_user.id))
    except ValueError:
        update.message.reply_text("❌ Invalid date format. Please use YYYY-MM-DD.",
                                  reply_markup=main_menu(update.message.from_user.id))
    return MAIN_MENU


def book_upload_subject(update: Update, context: CallbackContext):
    if update.message.text == '🏠 Main Menu':
        return back_to_menu(update, context)

    context.user_data['book_subject'] = update.message.text
    update.message.reply_text("Now send the PDF file:", reply_markup=ReplyKeyboardMarkup(
        [['🏠 Main Menu']], resize_keyboard=True
    ))
    return MAIN_MENU


def document_handler(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id == ADMIN_ID and 'book_subject' in context.user_data:
        doc: Document = update.message.document

        # Create unique filename
        file_ext = os.path.splitext(doc.file_name)[1]
        file_name = f"{context.user_data['book_subject']}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{file_ext}"
        file_path = os.path.join(BOOKS_DIR, file_name)

        # Download file in chunks to handle large files
        file = doc.get_file()
        file.download(custom_path=file_path)

        cursor.execute("INSERT INTO books (subject, file_path) VALUES (?, ?)",
                       (context.user_data['book_subject'], file_path))
        conn.commit()

        update.message.reply_text(f"✅ Book saved as {file_name}", reply_markup=main_menu(user_id))
        context.user_data.pop('book_subject', None)
    else:
        update.message.reply_text("PDF ignored. Only admin can upload books.",
                                  reply_markup=main_menu(user_id))


def daily_deadline_notifier(context: CallbackContext):
    tomorrow = (datetime.datetime.today() + datetime.timedelta(days=1)).date()
    cursor.execute("SELECT subject, text FROM deadlines WHERE due_date=?", (str(tomorrow),))
    for row in cursor.fetchall():
        subject, text = row
        cursor.execute("SELECT telegram_id FROM users")
        for user in cursor.fetchall():
            try:
                context.bot.send_message(chat_id=user[0],
                                         text=f"📢 Reminder:\nDeadline for {subject} is tomorrow!\n{text}")
            except Exception as e:
                print(f"Failed to send reminder to {user[0]}: {str(e)}")


def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_NAME: [MessageHandler(Filters.text & ~Filters.command, ask_name)],
            ASK_ID: [MessageHandler(Filters.text & ~Filters.command, ask_id)],
            MAIN_MENU: [MessageHandler(Filters.text & ~Filters.command, handle_menu)],
            SCHEDULE_DAY: [MessageHandler(Filters.text & ~Filters.command, handle_schedule)],
            BOOK_SUBJECT: [MessageHandler(Filters.text & ~Filters.command, handle_book_subject)],
            FEEDBACK_TEXT: [MessageHandler(Filters.text & ~Filters.command, receive_feedback)],
            ADD_HOMEWORK_SUBJECT: [MessageHandler(Filters.text & ~Filters.command, add_hw_subject)],
            ADD_HOMEWORK_TEXT: [MessageHandler(Filters.text & ~Filters.command, add_hw_text)],
            ADD_HOMEWORK_DATE: [MessageHandler(Filters.text & ~Filters.command, add_hw_date)],
            BOOK_UPLOAD_SUBJECT: [MessageHandler(Filters.text & ~Filters.command, book_upload_subject)],
        },
        fallbacks=[MessageHandler(Filters.regex('^🏠 Main Menu$'), back_to_menu)]
    )

    dp.add_handler(conv_handler)
    dp.add_handler(MessageHandler(Filters.document, document_handler))

    # Daily job to remind students
    updater.job_queue.run_daily(daily_deadline_notifier, time=datetime.time(hour=9, minute=0))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()





