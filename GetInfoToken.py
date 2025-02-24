import re
import requests
import aiohttp
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile

# Global variables to track input state
waiting_for_contract = {}
waiting_for_token_name = {}

API_KEY = '' # https://coinmarketcap.com/api/



def format_number(number):
    number = float(number)
    if number >= 1_000_000_000_000:
        return f"{number / 1_000_000_000_000:.2f}T"
    elif number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}B"
    elif number >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"
    elif number >= 1_000:
        return f"{number / 1_000:.2f}K"
    else:
        return str(number)


async def get_token_info_by_address(contract_address):
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/info'
    params = {'address': contract_address}
    headers = {
        'X-CMC_PRO_API_KEY': API_KEY,
        'Accept': 'application/json',
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as response:
            return await response.json()

async def get_token_info_by_name(token_name):
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/info'
    params = {'symbol': token_name.upper()}
    headers = {
        'X-CMC_PRO_API_KEY': API_KEY,
        'Accept': 'application/json',
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as response:
            return await response.json()
    
def extract_price_info(description):
    price_pattern = r'is ([\d\.,]+) USD'
    change_pattern = r'(-?[\d\.,]+) over the last 24 hours'
    volume_pattern = r'trading on .*? market\(s\) with \$([\d\.,]+) traded over the last 24 hours'

    price_match = re.search(price_pattern, description)
    change_match = re.search(change_pattern, description)
    volume_match = re.search(volume_pattern, description)

    price = price_match.group(1) if price_match else 'N/A'
    change = change_match.group(1) if change_match else 'N/A'
    volume = volume_match.group(1) if volume_match else 'N/A'

    price = price.replace(',', '') if price != 'N/A' else price
    volume = volume.replace(',', '') if volume != 'N/A' else volume

    return price, change, volume

def get_inline_buttons():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Search by contract address", callback_data="search_by_contract")],
            [InlineKeyboardButton(text="Search by token name", callback_data="search_by_token_name")]
        ]
    )
    return keyboard

async def token_info_handler(message: types.Message, config, IMAGE_FOLDER):
    image_path = f"{IMAGE_FOLDER}/token_info.png"
    photo = FSInputFile(image_path)
    text = config["token_info_message"]
    await message.answer_photo(parse_mode="Markdown", photo=photo, caption=text, reply_markup=get_inline_buttons())

async def search_by_contract_callback(query: types.CallbackQuery):
    waiting_for_contract[query.from_user.id] = True
    await query.message.answer("Enter the contract address of the token you are interested in:")

async def get_token_info_by_contract_address(message: types.Message, get_return_menu):
    if not waiting_for_contract.get(message.from_user.id, False):
        return

    contract_address = message.text.strip()
    token_data = await get_token_info_by_address(contract_address)

    # Reset the waiting state
    waiting_for_contract[message.from_user.id] = False

    if token_data.get('status', {}).get('error_code') == 0:
        token_info = token_data.get('data', {})
        if token_info:
            token = list(token_info.values())[0]

            name = token.get('name', 'Unknown Token')
            symbol = token.get('symbol', 'Unknown Symbol')
            description = token.get('description', 'No description available.')
            logo = token.get('logo', '')
            market_cap = token.get('self_reported_market_cap', 'N/A')
            supply = token.get('self_reported_circulating_supply', 'N/A')

            price, change, volume = extract_price_info(description)
            market_cap = round(float(market_cap), 0) if market_cap not in [None, 'N/A'] else 'N/A'

            token_details = (
                f"🚀 Token Name: {name} ({symbol})\n\n"
                f"💰 Price: {price} USD\n"
                f"📉 Price Change (24h): {change}%\n\n"
                f"💸 Market Cap: {market_cap} USD\n"
                f"🪙 Circulating Supply: {supply}\n"
                f"📊 Volume: {volume} USD\n\n"
                f"🌐 Official Chat: {token.get('urls', {}).get('chat', ['No link available.'])[0]}\n\n"
            )

            return_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Return to Menu 🔙", callback_data="return_to_menu")]]
            )

            if logo:
                await message.answer_photo(logo, caption=token_details, reply_markup=return_keyboard)
            else:
                await message.answer(token_details, reply_markup=return_keyboard)
        else:
            await message.answer("Sorry, I couldn't find any information for this contract address.", 
                               reply_markup=get_return_menu())
    else:
        await message.answer("There was an error fetching the data. Please try again later.", 
                           reply_markup=get_return_menu())

def extract_price_info(description):
    price_pattern = r'is ([\d\.,]+) USD'
    change_pattern = r'(-?[\d\.,]+) over the last 24 hours'
    volume_pattern = r'trading on .*? market\(s\) with \$([\d\.,]+) traded over the last 24 hours'

    price_match = re.search(price_pattern, description)
    change_match = re.search(change_pattern, description)
    volume_match = re.search(volume_pattern, description)

    price = price_match.group(1) if price_match else 'N/A'
    change = change_match.group(1) if change_match else 'N/A'
    volume = volume_match.group(1) if volume_match else 'N/A'

    price = price.replace(',', '') if price != 'N/A' else price
    volume = volume.replace(',', '') if volume != 'N/A' else volume

    return price, change, volume

def get_inline_buttons():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Search by contract address", callback_data="search_by_contract")],
            [InlineKeyboardButton(text="Search by token name", callback_data="search_by_token_name")]
        ]
    )
    return keyboard

async def search_by_token_name_callback(query: types.CallbackQuery):
    waiting_for_token_name[query.from_user.id] = True
    await query.message.answer("Enter the short name of the token you are interested in:\n(for example: NOT, TON, DOGS)")

async def get_token_info_by_name_handler(message: types.Message, get_return_menu):
    if not waiting_for_token_name.get(message.from_user.id, False):
        return

    token_name = message.text.strip()
    token_data = await get_token_info_by_name(token_name.lstrip('$'))

    waiting_for_token_name[message.from_user.id] = False
    if token_data:
        token_info = token_data.get('data', {})
        token = list(token_info.values())[0]

        name = token.get('name', 'Unknown Token')
        symbol = token.get('symbol', 'Unknown Symbol')
        description = token.get('description', 'No description available.')
        logo = token.get('logo', '')
        market_cap = token.get('self_reported_market_cap', 'N/A')
        supply = token.get('self_reported_circulating_supply', 'N/A')
        
        price, change, volume = extract_price_info(description)
        market_cap = round(float(market_cap), 0) if market_cap not in [None, 'N/A'] else 'N/A'
        
        token_details = (
            f"🚀 Token Name: {name} ({symbol})\n\n"
            f"💰 Price: {price}$\n"
            f"📉 Price Change (24h): {change}%\n\n"
            f"💸 Market Cap: {format_number(market_cap) if market_cap not in ['N/A', None] else market_cap}$\n"
            f"🪙 Circulating Supply: {format_number(supply) if supply not in ['N/A', None] else supply}\n"
            f"📊 Volume: {format_number(volume) if volume not in ['N/A', None] else volume}$\n\n"
            f"🌐 Official Chat: {token.get('urls', {}).get('chat', ['No link available.'])[0]}\n\n"
        )


        return_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Return to Menu 🔙", callback_data="return_to_menu")]]
        )

        if logo:
            await message.answer_photo(logo, caption=token_details, reply_markup=return_keyboard)
        else:
            await message.answer(token_details, reply_markup=return_keyboard)
    else:
        await message.answer("Sorry, I couldn't find any information for this token name.", 
                           reply_markup=get_return_menu())

