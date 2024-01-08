from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from database import SQLiteDBManager
from create_order import create_order
from conf_check import check_order_status
from delete_order import delete_sellix_order
from datetime import datetime, timedelta
import logging

SELLIX_API_KEY = ""  # Your Sellix API Key Obtainable from sellix.io
TOKEN = "" #Your telegram Bot token

db_manager = SQLiteDBManager('order_status.sqlite3')

# Define the indexes based on your database schema
UNIQID_INDEX = 0
CHAT_ID_INDEX = 1 
USER_ID_INDEX = 2  
USERNAME_INDEX = 3
STATUS_INDEX = 4  
CRYPTO_INDEX = 5
AMOUNT_INDEX = 6
PLAN_INDEX = 7
HASH_INDEX = 8 

def start_periodic_check(context: CallbackContext):
    job_context = {}
    raw_context = context.job.context
    if isinstance(raw_context, dict):
        job_context = raw_context
    elif isinstance(raw_context, tuple) and all(isinstance(item, tuple) and len(item) == 2 for item in raw_context):
        job_context = dict(raw_context)
    else:
        logging.error("Unexpected job context format. Ensure it's a dictionary or an iterable of key-value pairs.")
        return  

    chat_id, uniqid = job_context.get('chat_id'), job_context.get('uniqid')
    
    if not chat_id or not uniqid:
        logging.error("Chat ID or Uniqid missing from the job context.")
        return  

    now = datetime.now()

    first_check_time = job_context.get('first_check_time', now)
    job_context['first_check_time'] = first_check_time

    time_diff = now - first_check_time

    delete_after = timedelta(hours=2)

    current_status, crypto_hash = check_order_status(SELLIX_API_KEY, uniqid)

    if current_status:
        last_status = db_manager.get_order_status(uniqid)

        valid_transitions = [("PENDING", "WAITING_FOR_CONFIRMATIONS"),
                             ("PENDING", "COMPLETED"),
                             ("WAITING_FOR_CONFIRMATIONS", "COMPLETED")]

        if (last_status, current_status) in valid_transitions:
            message = f"Order <code>{uniqid}</code> status changed from <code>{last_status}</code> to <code>{current_status}</code>"
            context.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            logging.info(f"Order {uniqid} status changed from {last_status} to {current_status}")
            db_manager.update_order_status(uniqid, current_status)

            order_details = db_manager.get_order_details(uniqid)
            if crypto_hash and order_details and order_details[HASH_INDEX] != crypto_hash:
                db_manager.update_order_hash(uniqid, crypto_hash)
                context.bot.send_message(chat_id=chat_id, text=f"Transaction hash: <code>{crypto_hash}</code>", parse_mode='HTML')

        if last_status == "PENDING" and time_diff > delete_after:
            success, message = delete_sellix_order(SELLIX_API_KEY, uniqid)
            if success:
                context.bot.send_message(chat_id=chat_id, text=f"Order <code>{uniqid}</code> has been automatically cancelled due to timeout.", parse_mode='HTML')
                db_manager.update_order_status(uniqid, "CANCELLED")
                logging.info(f"Order {uniqid} has been automatically cancelled due to timeout, Placed by: {chat_id}")
                context.job.schedule_removal()  
            else:
                logging.error(f"Failed to automatically cancel order {uniqid}: {message}")

        if current_status == "COMPLETED":
            context.job.enabled = False  
            logging.info(f"Order {uniqid} is successfully completed, Buyer: {chat_id}, Removing the Job")
            context.job.schedule_removal()  
        elif current_status == "VOIDED":
            context.job.enabled = False  
            logging.info(f"Order {uniqid} Was Cancelled, Buyer: {chat_id}, Removing the Job")
            context.job.schedule_removal()

    else:
        logging.error(f"No current status for order {uniqid}. It might be an API error or network issue.")

def status(update: Update, context: CallbackContext):
    username = update.effective_user.username
    userid = update.effective_user.id
    args = context.args
    if len(args) == 1:
        uniqid = args[0]
        order_status = db_manager.get_order_status(uniqid)
        if order_status:
            update.message.reply_text(f"Current status of order <code>{uniqid}</code> is <code>{order_status}</code>", parse_mode='HTML')
            logging.info(f'{username} - {userid}: Executed /status, Current status of order {uniqid} is {order_status}')
        else:
            update.message.reply_text("Unable to fetch the status. Please check the uniqid and try again.")
            logging.error(f'{username} - {userid}: Executed /status, Unable to fetch the status. Please check the uniqid and try again.')
    else:
        update.message.reply_text("Usage: /status <uniqid>")

def cancel(update: Update, context: CallbackContext):
    args = context.args
    if len(args) == 1:
        uniqid = args[0]

        current_chat_id = update.effective_chat.id
        current_user_id = update.effective_user.id
        username = update.effective_user.username

        order_details = db_manager.get_order_details(uniqid)

        if order_details and order_details[CHAT_ID_INDEX] == current_chat_id and order_details[USER_ID_INDEX] == current_user_id:
            if order_details[STATUS_INDEX].upper() == "PENDING":
                success, message = delete_sellix_order(SELLIX_API_KEY, uniqid)
                if success:
                    db_manager.update_order_status(uniqid, "Cancelled")
                    update.message.reply_text(f"Order <code>{uniqid}</code> has been cancelled successfully.", parse_mode='HTML')
                    logging.info(f"{username} - {current_user_id} Executed /Cancel, Order {uniqid} has been cancelled successfully.")
                else:
                    update.message.reply_text(f"Failed to cancel order <code>{uniqid}</code>: {message}", parse_mode='HTML')
                    logging.error(f"{username} - {current_user_id} Failed to cancel order {uniqid}: {message}")
            elif order_details[STATUS_INDEX].upper() == 'CANCELLED':
                update.message.reply_text(f"Order <code>{uniqid}</code> is already cancelled.", parse_mode='HTML')
            else:
                update.message.reply_text("The order cannot be cancelled.")
        else:
            update.message.reply_text("You do not have permission to cancel this order")
            logging.info(f"{username} - {current_user_id} Tried to Cancel an order they did not place.")
    else:
        update.message.reply_text("Usage: /cancel <Order ID>")
            

def start(update: Update, context: CallbackContext) -> None:
    username = update.effective_user.username
    userid = update.effective_user.id
    welcome_message = f"Welcome @{username} to <name placeholder> Bot!"
    logging.info(f"{username} - {userid} Pressed /start")

    keyboard = [
        [InlineKeyboardButton("License", callback_data='license')],
        [InlineKeyboardButton("Generic 1", callback_data='generic1')],
        [InlineKeyboardButton("Generic 2", callback_data='generic2')],
        [InlineKeyboardButton("Generic 3", callback_data='generic3')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(welcome_message, reply_markup=reply_markup)


def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    original_message = query.message
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username

    if query.data == 'license':
        logging.info(f"{username} - {user_id} Pressed License button.")
        keyboard = [
            [InlineKeyboardButton("Buy new License", callback_data='buy_new_license')],
            [InlineKeyboardButton("Renew License (Not Developed)", callback_data='renew_license')],
            [InlineKeyboardButton("Activate License (Not Developed)", callback_data='renew_license')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        original_message.edit_text('Please choose an option:', reply_markup=reply_markup)

    elif query.data == 'buy_new_license':
        logging.info(f"{username} - {user_id} Pressed Buy License button.")
        keyboard = [
            [InlineKeyboardButton("Basic Plan: $599", callback_data='basicplan')],
            [InlineKeyboardButton("Gold Plan: $999", callback_data='goldplan')],
            [InlineKeyboardButton("Diamond Plan: $1,499", callback_data='diamondplan')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        original_message.edit_text(text="Choose your plan:", reply_markup=reply_markup)

    elif query.data in ['basicplan', 'goldplan', 'diamondplan']:
        selected_plan = query.data
        logging.info(f"{username} - {user_id} Selected {selected_plan}.")
        keyboard = [
            [InlineKeyboardButton("Bitcoin", callback_data=f'{selected_plan}_Bitcoin')],
            [InlineKeyboardButton("Litecoin", callback_data=f'{selected_plan}_Litecoin')],
            [InlineKeyboardButton("Ethereum", callback_data=f'{selected_plan}_Ethereum')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        original_message.edit_text(text="Choose the cryptocurrency you want to use for payment:", reply_markup=reply_markup)
    
    elif query.data in ['basicplan_Bitcoin', 'basicplan_Litecoin', 'basicplan_Ethereum', 
                    'goldplan_Bitcoin', 'goldplan_Litecoin', 'goldplan_Ethereum',
                    'diamondplan_Bitcoin', 'diamondplan_Litecoin', 'diamondplan_Ethereum']:
        original_message.edit_text("Generating Invoice...")
        selected_plan, gateway = query.data.split('_')
        gateway = gateway.upper()
        if gateway == 'BITCOIN':
            flag = 'BTC'
        elif gateway ==  'LITECOIN':
            flag = 'LTC'
        elif gateway == 'ETHEREUM':
            flag = 'ETH'
        
        address, amount, uniqid, protocol, usdvalue = create_order(SELLIX_API_KEY, gateway, selected_plan)
        db_manager.insert_order(chat_id, user_id, username, uniqid, 'PENDING',protocol, usdvalue,selected_plan,'None')
        
        original_message.edit_text(
            text=f"To complete your purchase with {gateway}\nPlease send <code>{amount}</code> {flag}\nTo Address: <code>{address}</code>\nYour Order ID is: <code>{uniqid}</code>\nWe are checking for payment status, please wait for 2 Confirmations.",
            parse_mode='HTML'
        )
        logging.info(f"{username} - {user_id} Placed an Order {uniqid} for {selected_plan}: ${usdvalue} , Payment with: {protocol}, Amount to be sent: {amount}, ")
        context.job_queue.run_repeating(start_periodic_check, interval=10, first=0, context={'chat_id': chat_id, 'uniqid': uniqid})

    # Add here your existing handlers for 'activate_license' and 'renew_license' if needed

def main() -> None:
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s",datefmt="%d-%m-%Y %H:%M:%S")
    updater = Updater(TOKEN, use_context=True)
    
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.dispatcher.add_handler(CommandHandler('status', status, pass_args=True))
    updater.dispatcher.add_handler(CommandHandler('cancel',cancel,pass_args=True))


    updater.start_polling()
    print("Bot is polling...")
    updater.idle()

if __name__ == '__main__':
    main()
