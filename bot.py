# bots/ardayda_bot/bot.py
"""
Telegram bot entry point.
Routes updates to appropriate handlers and rejects invalid callbacks.
"""

import os
import logging
import telebot
from telebot.types import Message, CallbackQuery

# Import handlers and database functions
import handlers
import database as db

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize bot
#TOKEN = os.environ.get("BOT_TOKEN")
TOKEN = "7134963817:AAEWGOC_haI0Te-TC4AygXDhP89vYoljQE8"
if not TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")
bot = telebot.TeleBot(TOKEN)

# ----------------------------------------------------------------------
# Message handlers
# ----------------------------------------------------------------------

@bot.message_handler(commands=['start'])
def handle_start(message: Message):
    """Handle /start command - delegate to handlers."""
    handlers.start_handler(bot, message)

@bot.message_handler(func=lambda msg: msg.text and not msg.text.startswith('/'))
def handle_text(message: Message):
    """Handle all non-command text messages."""
    handlers.text_message_handler(bot, message)

@bot.message_handler(content_types=['document'])
def handle_document(message: Message):
    """Handle document uploads (PDFs)."""
    handlers.document_handler(bot, message)

# ----------------------------------------------------------------------
# Callback query handler
# ----------------------------------------------------------------------

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call: CallbackQuery):
    """
    Handle all callback queries.
    Validates that the user's current state allows this callback.
    """
    user_id = call.from_user.id
    callback_data = call.data

    # Get current user status from database
    current_status = db.get_user_status(user_id)

    # If user has no status, assume they need to register.
    # But callbacks are usually not expected before registration.
    if not current_status:
        bot.answer_callback_query(
            call.id,
            "Please start the bot with /start first.",
            show_alert=False
        )
        return

    # Determine allowed statuses for this callback based on prefix.
    # We'll define a simple mapping: callback data starts with domain or flow.
    # For example, callbacks starting with "upload_" require status in upload domain.
    # More specific checks can be done inside handlers, but here we do basic filtering.
    allowed_domain = None
    if callback_data.startswith("upload_"):
        allowed_domain = "upload"
    elif callback_data.startswith("search_"):
        allowed_domain = "search"
    elif callback_data.startswith("view_"):
        allowed_domain = "view"
    elif callback_data.startswith("auth_"):
        allowed_domain = "auth"
    elif callback_data.startswith("sys_"):
        allowed_domain = "sys"
    else:
        # If no prefix matches, we cannot validate; let the handler decide.
        # But we'll pass through and let the handler handle it.
        pass

    if allowed_domain and not current_status.startswith(allowed_domain):
        # Current status does not belong to the required domain
        logger.warning(
            f"User {user_id} attempted callback {callback_data} "
            f"with status {current_status} – rejected."
        )
        bot.answer_callback_query(
            call.id,
            "This action is not allowed right now.",
            show_alert=False
        )
        return

    # If validation passes, delegate to the handlers module.
    handlers.callback_handler(bot, call)

# ----------------------------------------------------------------------
# Error handler (optional)
# ----------------------------------------------------------------------

@bot.message_handler(func=lambda msg: True)
def fallback_handler(message: Message):
    """Catch any unmatched messages (e.g., commands not handled)."""
    bot.reply_to(message, "I don't understand that command.")

# ----------------------------------------------------------------------
# Start polling
# ----------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Bot started polling...")
    bot.infinity_polling()