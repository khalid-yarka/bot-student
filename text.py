# bots/ardayda_bot/text.py
"""
All user-facing text messages for the bot.
Centralized for easy editing and future localization.
"""

# ----------------------------------------------------------------------
# Registration flow
# ----------------------------------------------------------------------

REGISTER_NAME = "📝 Welcome! Let's get you registered.\n\nPlease enter your full name:"
REGISTER_REGION = "🌍 Great! Now, which region are you from?"
REGISTER_SCHOOL = "🏫 Please enter the name of your school:"
REGISTER_CLASS = "📚 Finally, what is your class/form? (e.g., Form 1, Form 2, etc.)"
REGISTER_COMPLETE = "✅ Registration complete! You can now upload and search for PDFs."

# ----------------------------------------------------------------------
# Main menu
# ----------------------------------------------------------------------

MAIN_MENU = "🏠 *Main Menu*\n\nWhat would you like to do?"
INVALID_OPTION = "❌ Invalid option. Please use the buttons below."

# ----------------------------------------------------------------------
# Upload flow
# ----------------------------------------------------------------------

UPLOAD_PROMPT = "📎 Please send me the PDF file you want to upload."
UPLOAD_ONLY_PDF = "❌ Only PDF files are allowed. Please send a PDF."
UPLOAD_NOT_EXPECTED = "❌ You are not in upload mode. Use /start to return to menu."
UPLOAD_EXPECT_FILE = "📎 Please send a PDF file first."
UPLOAD_SUCCESS = "✅ PDF uploaded successfully!"
UPLOAD_CANCELLED = "❌ Upload cancelled."
TAG_SELECTION_PROMPT = "🏷️ Select tags for this PDF. You can select multiple. Click Done when finished."
TAG_REQUIRED = "⚠️ Please select at least one tag."

# ----------------------------------------------------------------------
# Search flow
# ----------------------------------------------------------------------

SEARCH_USE_BUTTONS = "🔍 Use the buttons below to select filters."
SEARCH_REQUIRED_TAG = "⚠️ Please select at least one tag to search."
SEARCH_CANCELLED = "❌ Search cancelled."
NO_RESULTS = "😕 No PDFs found matching your filters."
PDF_LIST_HEADER = "📄 *Search Results* (Page {page} of {total})\n\n"

# ----------------------------------------------------------------------
# PDF viewing
# ----------------------------------------------------------------------

PDF_DETAIL = """📄 *{title}*

🏷️ Tags: {tags}
❤️ Likes: {likes}
📥 Downloads: {downloads}

Use the buttons below to interact."""

PDF_NOT_FOUND = "❌ PDF not found."
LIKE_UPDATED = "✅ Like updated!"

# ----------------------------------------------------------------------
# General errors and messages
# ----------------------------------------------------------------------

ACTION_NOT_ALLOWED = "⛔ This action is not allowed right now."
SESSION_EXPIRED = "⌛ Your session has expired. Please start again."
VIEW_USE_BUTTONS = "👆 Use the buttons below to navigate."

# ----------------------------------------------------------------------
# Callback data related text (for alert messages)
# ----------------------------------------------------------------------

# (No direct user messages here; but could be used in bot.answer_callback_query)