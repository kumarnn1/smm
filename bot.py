import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import requests
import json
from typing import Dict, Any

# Configuration
API_URL = "https://smmxz.com/api/v2"
API_KEY = "e6110bb9e5ba22a7b104254a8a01af5f"
BOT_TOKEN = "8680663184:AAFi5T8aQX8mO4WT0g7eewS1orcIVqE2szk"

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# User session storage
user_sessions = {}

class SMMAPI:
    """Handle all SMM API interactions"""
    
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            'Content-Type': 'application/json'
        }
    
    def make_request(self, action, data=None):
        """Make API request to SMM panel"""
        if data is None:
            data = {}
        
        payload = {
            'key': self.api_key,
            'action': action,
            **data
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=self.headers)
            return response.json()
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return {'error': str(e)}
    
    def get_services(self):
        """Get all available services"""
        return self.make_request('services')
    
    def get_balance(self):
        """Get account balance"""
        return self.make_request('balance')
    
    def place_order(self, service_id, link, quantity):
        """Place a new order"""
        data = {
            'service': service_id,
            'link': link,
            'quantity': quantity
        }
        return self.make_request('add', data)
    
    def get_order_status(self, order_id):
        """Check order status"""
        data = {'order': order_id}
        return self.make_request('status', data)

# Initialize API
smm_api = SMMAPI(API_URL, API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued."""
    user = update.effective_user
    welcome_message = f"""
👋 Welcome {user.first_name} to SMM Bot!

I can help you with social media marketing services:
✅ Instagram followers
✅ Instagram likes
✅ YouTube views
✅ Telegram members
✅ And much more!

Use /menu to see available options
Use /balance to check your credits
Use /help for assistance
    """
    
    await update.message.reply_text(welcome_message)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu with options."""
    keyboard = [
        [InlineKeyboardButton("📊 Check Balance", callback_data='balance')],
        [InlineKeyboardButton("🛍️ View Services", callback_data='services')],
        [InlineKeyboardButton("📝 New Order", callback_data='new_order')],
        [InlineKeyboardButton("📦 Order Status", callback_data='order_status')],
        [InlineKeyboardButton("❓ Help", callback_data='help')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 Main Menu - Choose an option:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == 'balance':
        await check_balance(query, context)
    
    elif query.data == 'services':
        await show_services(query, context)
    
    elif query.data == 'new_order':
        await start_order(query, context)
    
    elif query.data == 'order_status':
        await query.edit_message_text("Please enter your Order ID:")
        user_sessions[user_id] = {'state': 'awaiting_order_id'}
    
    elif query.data == 'help':
        await show_help(query)
    
    elif query.data.startswith('cat_'):
        category = query.data.replace('cat_', '')
        await show_category_services(query, context, category)
    
    elif query.data.startswith('service_'):
        service_id = query.data.replace('service_', '')
        user_sessions[user_id] = {
            'state': 'awaiting_link',
            'service_id': service_id
        }
        await query.edit_message_text("Please enter the link (URL) for your order:")

async def check_balance(query, context):
    """Check and display account balance."""
    balance_data = smm_api.get_balance()
    
    if 'error' in balance_data:
        await query.edit_message_text("❌ Error fetching balance. Please try again later.")
    else:
        balance = balance_data.get('balance', 0)
        currency = balance_data.get('currency', 'USD')
        await query.edit_message_text(f"💰 Your Balance: **{balance} {currency}**", parse_mode='Markdown')

async def show_services(query, context):
    """Show service categories."""
    # You can categorize services based on your panel's structure
    keyboard = [
        [InlineKeyboardButton("📱 Instagram", callback_data='cat_instagram')],
        [InlineKeyboardButton("▶️ YouTube", callback_data='cat_youtube')],
        [InlineKeyboardButton("🐦 Twitter", callback_data='cat_twitter')],
        [InlineKeyboardButton("📘 Facebook", callback_data='cat_facebook')],
        [InlineKeyboardButton("📨 Telegram", callback_data='cat_telegram')],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Select a category:", reply_markup=reply_markup)

async def show_category_services(query, context, category):
    """Show services for a specific category."""
    services_data = smm_api.get_services()
    
    if 'error' in services_data:
        await query.edit_message_text("❌ Error fetching services.")
        return
    
    keyboard = []
    # Filter services by category (you may need to adjust based on your API response)
    for service in services_data[:10]:  # Limit to 10 services to avoid message too long
        if category.lower() in service.get('name', '').lower() or category.lower() in service.get('category', '').lower():
            button_text = f"{service.get('name')[:30]} - {service.get('price')} {service.get('currency', '')}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"service_{service.get('service')}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data='services')])
    
    if not keyboard[:-1]:  # If no services found
        keyboard.insert(0, [InlineKeyboardButton("❌ No services found", callback_data='none')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"📋 {category.title()} Services:", reply_markup=reply_markup)

async def start_order(query, context):
    """Start the order process."""
    user_id = query.from_user.id
    user_sessions[user_id] = {'state': 'awaiting_service_selection'}
    
    # Show services first
    await show_services(query, context)

async def show_help(query):
    """Show help information."""
    help_text = """
❓ **Help & Support**

**How to use this bot:**
1️⃣ Check your balance using /balance
2️⃣ Browse services from the menu
3️⃣ Place an order by providing:
   - Service link
   - Quantity
   - Service type

**Commands:**
/start - Start the bot
/menu - Show main menu
/balance - Check balance
/help - Show this help

**Need support?** Contact @support_username
    """
    await query.edit_message_text(help_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages."""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in user_sessions:
        await update.message.reply_text("Please use /menu to start.")
        return
    
    session = user_sessions[user_id]
    state = session.get('state')
    
    if state == 'awaiting_link':
        session['link'] = text
        session['state'] = 'awaiting_quantity'
        await update.message.reply_text("Please enter the quantity:")
    
    elif state == 'awaiting_quantity':
        try:
            quantity = int(text)
            if quantity <= 0:
                await update.message.reply_text("Please enter a valid positive number.")
                return
            
            # Place the order
            service_id = session.get('service_id')
            link = session.get('link')
            
            order_data = smm_api.place_order(service_id, link, quantity)
            
            if 'error' in order_data:
                await update.message.reply_text(f"❌ Error placing order: {order_data['error']}")
            else:
                order_id = order_data.get('order')
                await update.message.reply_text(
                    f"✅ **Order Placed Successfully!**\n\n"
                    f"📦 Order ID: `{order_id}`\n"
                    f"🔗 Link: {link}\n"
                    f"📊 Quantity: {quantity}\n\n"
                    f"Use /status {order_id} to check your order.",
                    parse_mode='Markdown'
                )
            
            # Clear session
            del user_sessions[user_id]
            
        except ValueError:
            await update.message.reply_text("Please enter a valid number.")
    
    elif state == 'awaiting_order_id':
        try:
            order_id = int(text)
            status_data = smm_api.get_order_status(order_id)
            
            if 'error' in status_data:
                await update.message.reply_text(f"❌ Error: {status_data['error']}")
            else:
                status = status_data.get('status', 'Unknown')
                charge = status_data.get('charge', 'N/A')
                start_count = status_data.get('start_count', 'N/A')
                remains = status_data.get('remains', 'N/A')
                
                await update.message.reply_text(
                    f"📦 **Order #{order_id} Status**\n\n"
                    f"Status: **{status}**\n"
                    f"Charge: {charge}\n"
                    f"Started: {start_count}\n"
                    f"Remaining: {remains}",
                    parse_mode='Markdown'
                )
            
            # Clear session
            del user_sessions[user_id]
            
        except ValueError:
            await update.message.reply_text("Please enter a valid Order ID.")
    
    else:
        await update.message.reply_text("Please use /menu to start.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check order status by command."""
    if context.args:
        try:
            order_id = int(context.args[0])
            status_data = smm_api.get_order_status(order_id)
            
            if 'error' in status_data:
                await update.message.reply_text(f"❌ Error: {status_data['error']}")
            else:
                status = status_data.get('status', 'Unknown')
                charge = status_data.get('charge', 'N/A')
                start_count = status_data.get('start_count', 'N/A')
                remains = status_data.get('remains', 'N/A')
                
                await update.message.reply_text(
                    f"📦 **Order #{order_id} Status**\n\n"
                    f"Status: **{status}**\n"
                    f"Charge: {charge}\n"
                    f"Started: {start_count}\n"
                    f"Remaining: {remains}",
                    parse_mode='Markdown'
                )
        except ValueError:
            await update.message.reply_text("Please provide a valid Order ID.")
    else:
        await update.message.reply_text("Please provide an Order ID. Example: /status 123456")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check balance command."""
    balance_data = smm_api.get_balance()
    
    if 'error' in balance_data:
        await update.message.reply_text("❌ Error fetching balance. Please try again later.")
    else:
        balance = balance_data.get('balance', 0)
        currency = balance_data.get('currency', 'USD')
        await update.message.reply_text(f"💰 Your Balance: **{balance} {currency}**", parse_mode='Markdown')

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("help", show_help))

    # Register callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_handler))

    # Register message handler for user input
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    print("🤖 SMM Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()