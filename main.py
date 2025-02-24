import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import json
from GetInfoToken import (
    token_info_handler, 
    search_by_contract_callback, 
    get_token_info_by_contract_address,
    search_by_token_name_callback,
    get_token_info_by_name_handler
)
import TonWallet
import os
from aiogram.utils.keyboard import InlineKeyboardBuilder
from itertools import zip_longest
import re

# Initialization of constants
TG_BOT_TOKEN_API = '' # Telegram bot API
IMAGE_FOLDER = 'images'
CONFIG_FILE = 'config.json'
DATABASE = TonWallet.DATABASE

# Initialization of Telegram Bot
bot = Bot(token=TG_BOT_TOKEN_API)
dp = Dispatcher()
router = Router()
dp.include_router(router)

if not os.path.exists(DATABASE) or os.path.getsize(DATABASE) == 0:
    with open(DATABASE, "w", encoding="utf-8") as file:
        json.dump({}, file)

# Load config file with text data
with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    config = json.load(f)

def escape_markdown(text: str) -> str:
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def get_main_menu():
    buttons = [
        [KeyboardButton(text="Wallet 🏦")],
        [KeyboardButton(text="Buy 📈"), KeyboardButton(text="Sell 📉")],
        [KeyboardButton(text="Token Info ℹ️"), KeyboardButton(text="TP/SL Orders 🎯")],
        [KeyboardButton(text="Limit Orders 📊"), KeyboardButton(text="Copy Trade 🔄")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_return_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Return to Menu 🔙")]], resize_keyboard=True)

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    image_path = f"{IMAGE_FOLDER}/start.png"
    photo = FSInputFile(image_path)
    text = config["start_message"]
    await message.answer_photo(photo=photo, caption=text, reply_markup=get_main_menu())

# -- WALLET -- START --

@dp.message(lambda message: message.text == "Wallet 🏦")
async def wallet_handler(message: types.Message):
    button1_1 = InlineKeyboardButton(text="Deposite 📥", callback_data="deposite")
    button1_2 = InlineKeyboardButton(text="Withdrawal 📤", callback_data="withdrawal")
    keyboard1 = InlineKeyboardMarkup(inline_keyboard=[[button1_1, button1_2]])
    
    user_id = message.from_user.id
    image_path = f"{IMAGE_FOLDER}/wallet.png"
    photo = FSInputFile(image_path)
    
    with open(DATABASE, "r", encoding="utf-8") as file:
        data = json.load(file)
        
    if data.get(str(user_id)) is None:
        await TonWallet.create_new_wallet(user_id)

    user_list_tokens = await TonWallet.get_all_user_tokens(user_id)
    user_list_tokens = "\n".join([f"{name} (\${symbol}): {amount}\n".replace("(", "\(").replace(")", "\)") for symbol, (amount, name, _) in user_list_tokens.items()])
    text = f"\n{user_list_tokens}".replace("{", "\{").replace("}", "\}")
    
    await message.answer_photo(photo=photo, parse_mode="MarkdownV2", caption=text, reply_markup=keyboard1)

@dp.callback_query(lambda c: c.data == 'deposite')
async def process_deposit_callback(query: types.CallbackQuery):
    user_id = query.from_user.id
    user_wallet = await TonWallet.get_wallet(user_id)
    message_text = f"📥 Deposite TON adress: `{user_wallet}`"
    
    await bot.send_message(
        user_id, 
        message_text,
        parse_mode="MarkdownV2"
    )
    
    await query.answer()
@dp.callback_query(lambda c: c.data == 'withdrawal')
async def process_withdrawal_callback(query: types.CallbackQuery):
    user_id = query.from_user.id
    user_wallet = await TonWallet.get_wallet(user_id)
    message_text = f"Select token to withdrawal"
    user_list_tokens = await TonWallet.get_all_user_tokens(user_id)

    buttons = []
    for x in user_list_tokens:
        text_button = user_list_tokens[x][1] + f" (${x})"
        button = InlineKeyboardButton(text=text_button, callback_data=(x+"_withdrawal"))
        buttons.append(button)

    keyboard_buttons = [
        list(filter(None, pair)) for pair in zip_longest(*[iter(buttons)] * 2)
    ]

    keyboardj = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await bot.send_message(
        user_id, 
        message_text,
        parse_mode="MarkdownV2",
        reply_markup=keyboardj
    )
    await query.answer()

class WithdrawalTokenState(StatesGroup):
    waiting_for_address = State()
    waiting_for_amount = State()
    waiting_for_confirmation = State()

@router.callback_query(F.data.endswith("_withdrawal"))
async def withdrawal_callback_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    token = callback.data.replace("_withdrawal", "")

    user_list_tokens = await TonWallet.get_all_user_tokens(user_id)

    await state.update_data(token=token, user_id=user_id)
    
    await callback.message.answer("Enter the destination address:")
    await state.set_state(WithdrawalTokenState.waiting_for_address)
    await callback.answer()

@dp.message(WithdrawalTokenState.waiting_for_address)
async def process_withdrawal_address(message: types.Message, state: FSMContext):
    to_address = message.text

    await state.update_data(to_address=to_address)
    data = await state.get_data()
    token = data["token"]

    user_list_tokens = await TonWallet.get_all_user_tokens(message.from_user.id)
    user_balance = user_list_tokens.get(token, [0])[0]

    await message.answer(f"Enter the quantity of ${token} you wish to withdraw (max {user_balance}):")
    await state.set_state(WithdrawalTokenState.waiting_for_amount)


@router.message(WithdrawalTokenState.waiting_for_amount)
async def process_token_amount_withdrawal(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0:
            await message.answer("Non-correct number")
            return

        await state.update_data(amount=amount)
        data = await state.get_data()
        token = str(data["token"])
        to_address = data["to_address"]

        buttons = [
            InlineKeyboardButton(text="✅ Yes", callback_data="confirm_withdrawal"),
            InlineKeyboardButton(text="❌ No", callback_data="cancel_withdrawal")
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
        
        safe_amount = escape_markdown(str(amount))
        safe_token = escape_markdown(token)
        safe_intro = escape_markdown("Do you really want to withdraw ")
        safe_dollar = escape_markdown(" $")
        safe_to = escape_markdown(" to ")
        
        text = safe_intro + safe_amount + safe_dollar + safe_token + safe_to + f"`{to_address}`"
        
        await message.answer(
            text=text,
            parse_mode="MarkdownV2",
            reply_markup=keyboard
        )
        await state.set_state(WithdrawalTokenState.waiting_for_confirmation)

    except ValueError:
        await message.answer("Pls, enter correct number.")




@dp.callback_query(F.data == "confirm_withdrawal")
async def confirm_withdraw(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data["user_id"]
    to_address = data["to_address"]
    token_name = data["token"]
    token_transfer_amount = data["amount"]

    await TonWallet.send_token(user_id, to_address, token_name, token_transfer_amount)
    await callback.message.delete()
    await callback.message.answer(f"✅ Withdraw of {token_transfer_amount} ${token_name} to `{to_address}` confirmed!")
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "cancel_withdrawal")
async def cancel_withdraw(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()

    await callback.message.answer("❌ Withdraw canceled.")
    await state.clear()
    await callback.answer()


# -- WALLET -- END --



# -- BUY -- START --

@dp.message(lambda message: message.text == "Buy 📈")
async def buy_handler(message: types.Message):
    user_id = message.from_user.id
    user_list_tokens = await TonWallet.get_all_user_tokens(user_id)

    buttons = []
    for x in user_list_tokens:
        if x != "TON":
            text_button = user_list_tokens[x][1] + f" (${x})"
            button = InlineKeyboardButton(text=text_button, callback_data=(x+"_buy"))
            buttons.append(button)

    keyboard_buttons = [
        list(filter(None, pair)) for pair in zip_longest(*[iter(buttons)] * 2)
    ]

    keyboardj = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    image_path = f"{IMAGE_FOLDER}/buy.png"
    photo = FSInputFile(image_path)
    await message.answer_photo(photo=photo, caption="", reply_markup=keyboardj)

class BuyTokenState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_confirmation = State()

@router.callback_query(F.data.endswith("_buy"))
async def buy_callback_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    token = callback.data.replace("_buy", "")
    user_list_tokens = await TonWallet.get_all_user_tokens(user_id)

    user_balance = user_list_tokens["TON"][0]

    if user_balance > 0:
        await state.update_data(token=token)
        await callback.message.answer(f"Enter the quantity of ${token} you wish to buy:")
        await state.set_state(BuyTokenState.waiting_for_amount)
    else:
        await callback.message.answer("You do not have enough $TON")
    
    await callback.answer()

@router.message(BuyTokenState.waiting_for_amount)
async def process_token_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0:
            await message.answer("Количество должно быть больше нуля. Введите снова:")
            return
        
        await state.update_data(amount=amount)
        
        buttons = [
            InlineKeyboardButton(text="✅ Yes", callback_data="confirm_buy"),
            InlineKeyboardButton(text="❌ No", callback_data="cancel_buy")
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
        
        await message.answer(
            f"Do you really want to buy {amount} {await state.get_data()['token']}$?",
            reply_markup=keyboard
        )
        await state.set_state(BuyTokenState.waiting_for_confirmation)
    
    except ValueError:
        await message.answer("Pls, enter corrent number.")

@router.callback_query(F.data == "confirm_buy")
async def confirm_buy(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    token = data["token"]
    amount = data["amount"]

    await callback.message.answer(f"✅ Purchase of {amount} ${token} confirmed, await token delivery!")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_buy")
async def cancel_buy(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("❌ Purchase canceled.")
    await state.clear()
    await callback.answer()

async def get_user_token_balance(user_id: int, token: str) -> float:
    return 10.0

# -- BUY -- END --

# -- SELL -- START --

@dp.message(lambda message: message.text == "Sell 📉")
async def buy_handler(message: types.Message):
    user_id = message.from_user.id
    user_list_tokens = await TonWallet.get_all_user_tokens(user_id)

    buttons = []
    for x in user_list_tokens:
        if x != "TON":
            text_button = user_list_tokens[x][1] + f" (${x})"
            button = InlineKeyboardButton(text=text_button, callback_data=(x+"_sell"))
            buttons.append(button)

    keyboard_buttons = [
        list(filter(None, pair)) for pair in zip_longest(*[iter(buttons)] * 2)
    ]

    keyboardj = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    image_path = f"{IMAGE_FOLDER}/sell.png"
    photo = FSInputFile(image_path)
    await message.answer_photo(photo=photo, caption="", reply_markup=keyboardj)

# -- SELL -- END --

@dp.message(lambda message: message.text == "Token Info ℹ️")
async def token_info_wrapper(message: types.Message):
    await token_info_handler(message, config, IMAGE_FOLDER)

@dp.message(lambda message: message.text == "TP/SL Orders 🎯")
async def tp_sl_orders_handler(message: types.Message):
    image_path = f"{IMAGE_FOLDER}/tp_sl.png"
    photo = FSInputFile(image_path)
    text = config["tp_sl_message"]
    await message.answer_photo(photo=photo, caption=text, reply_markup=get_return_menu())

@dp.message(lambda message: message.text == "Limit Orders 📊")
async def limit_orders_handler(message: types.Message):
    image_path = f"{IMAGE_FOLDER}/limit_orders.png"
    photo = FSInputFile(image_path)
    text = config["limit_orders_message"]
    await message.answer_photo(photo=photo, caption=text, reply_markup=get_return_menu())

@dp.message(lambda message: message.text == "Copy Trade 🔄")
async def copy_trade_handler(message: types.Message):
    image_path = f"{IMAGE_FOLDER}/copy_trade.png"
    photo = FSInputFile(image_path)
    text = config["copy_trade_message"]
    await message.answer_photo(photo=photo, caption=text, reply_markup=get_return_menu())

@dp.message(lambda message: message.text == "Return to Menu 🔙")
async def return_to_menu_handler(message: types.Message):
    await message.delete()
    
    image_path = f"{IMAGE_FOLDER}/start.png"
    photo = FSInputFile(image_path)
    text = config["start_message"]
    await message.answer_photo(photo=photo, caption=text, reply_markup=get_main_menu())

@dp.callback_query(lambda c: c.data == 'search_by_contract')
async def search_contract_wrapper(query: types.CallbackQuery):
    await search_by_contract_callback(query)
    
@dp.callback_query(lambda c: c.data == 'search_by_token_name')
async def search_contract_wrapper2(query: types.CallbackQuery):
    await search_by_token_name_callback(query)
    
@dp.message(lambda message: message.text and message.text.startswith('EQ'))
async def get_token_info_wrapper(message: types.Message):
    await get_token_info_by_contract_address(message, get_return_menu)

@dp.message(lambda message: message.text)
async def get_token_info_wrapper2(message: types.Message):
    await get_token_info_by_name_handler(message, get_return_menu)

@dp.callback_query(lambda c: c.data == "return_to_menu")
async def return_to_menu_callback(callback_query: types.CallbackQuery):
    image_path = f"{IMAGE_FOLDER}/start.png"
    photo = FSInputFile(image_path)
    text = config["start_message"]
    await callback_query.message.answer_photo(photo=photo, caption=text, reply_markup=get_main_menu())
    await callback_query.answer()

async def main():
    print("Bot started...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
