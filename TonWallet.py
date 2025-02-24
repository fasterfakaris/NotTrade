from tonutils.client import TonapiClient
from tonutils.jetton import JettonMaster, JettonWallet
from tonutils.wallet import WalletV4R2
from tonutils.utils import to_amount
from mnemonic import Mnemonic
import aiohttp
import json
import asyncio
import os
import re

TON_CONSOLE_API_KEY = '' # https://tonconsole.com
IS_TESTNET = False # Testnet TON Network flag
DEBUG_MODE = True # Debug mode flag
DATABASE = 'database.json'
TOKEN_FILE = 'tokens.txt'

# TON WALLET FUNCTIONAL -- START

async def create_new_wallet(user_id) -> None:
    client = TonapiClient(api_key=TON_CONSOLE_API_KEY, is_testnet=IS_TESTNET)
    wallet, public_key, private_key, mnemonic = WalletV4R2.create(client)
    data = {user_id: [wallet.address.to_str(), mnemonic]}
    print(mnemonic)
    
    if DEBUG_MODE:
        print("Wallet has been successfully created!")
        print(f"Address: {wallet.address.to_str()}")
    
    with open(DATABASE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)



async def get_wallet(user_id):
    with open(DATABASE, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data[str(user_id)][0]



async def get_all_user_tokens(user_id):
    with open(DATABASE, "r", encoding="utf-8") as file:
        data = json.load(file)
    mnemonic = data[str(user_id)][1]
    client = TonapiClient(api_key=TON_CONSOLE_API_KEY, is_testnet=IS_TESTNET)
    wallet, public_key, private_key, mnemonic = WalletV4R2.from_mnemonic(client, mnemonic)
    list_tokens = {}
    try:
        balance = await wallet.balance()
        list_tokens["TON"] = [to_amount(balance), "Toncoin", None]

        with open(TOKEN_FILE, "r") as file:
            for line in file:
                pattern = r'([^|]+) \(\$([^\)]+)\) \| ([^\s]+)'
                match = re.match(pattern, line.strip())
                
                if match:
                    name = match.group(1)
                    symbol = match.group(2)
                    address = match.group(3)
                jetton_wallet_address = await JettonMaster.get_wallet_address(
                    client=client,
                    owner_address=wallet.address.to_str(),
                    jetton_master_address=address,
                )

                jetton_wallet_data = await JettonWallet.get_wallet_data(
                    client=client,
                    jetton_wallet_address=jetton_wallet_address,
                )

                list_tokens[symbol] = [to_amount(jetton_wallet_data.balance, 9), str(name), str(address)]
        
        
    except aiohttp.ClientResponseError as e:
            print(e)
            if e.status == 404:
                list_tokens["TON"] = [0, "Toncoin", None]
                with open(TOKEN_FILE, "r") as file:
                    for line in file:
                        pattern = r'([^|]+) \(\$([^\)]+)\) \| ([^\s]+)'
                        match = re.match(pattern, line.strip())
                        
                        if match:
                            name = match.group(1)
                            symbol = match.group(2)
                            address = match.group(3)
                        list_tokens[symbol] = [0, str(name), str(address)]
    except Exception as e:
        pass
    return list_tokens



# Buy token functional
async def buy_token(user_id, token_name, ton_count):
    token_list = get_all_user_tokens(user_id)
    buy_token_adrress = token_list[token_name][2]

    with open(DATABASE, "r", encoding="utf-8") as file:
        data = json.load(file)
    mnemonic = data[str(user_id)][1]
    
    client = TonapiClient(api_key=TON_CONSOLE_API_KEY)
    wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic)

    tx_hash = await wallet.dedust_swap_ton_to_jetton(
        jetton_master_address=buy_token_adrress,
        ton_amount=ton_count,
    )
    if DEBUG_MODE:
        print("Successfully swapped TON to Jetton!")
        print(f"Transaction hash: {tx_hash}")


        
# Sell token functional
async def sell_token(user_id, token_name, token_count):
    token_list = get_all_user_tokens(user_id)
    buy_token_adrress = token_list[token_name][2]

    with open(DATABASE, "r", encoding="utf-8") as file:
        data = json.load(file)
    mnemonic = data[str(user_id)][1]
    
    client = TonapiClient(api_key=TON_CONSOLE_API_KEY)
    wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic)

    tx_hash = await wallet.dedust_swap_jetton_to_ton(
        jetton_master_address=buy_token_adrress,
        jetton_amount=token_count,
        jetton_decimals=9,
    )
    if DEBUG_MODE:
        print("Successfully swapped Jetton to TON!")
        print(f"Transaction hash: {tx_hash}")



# Withdrawal token functional
async def send_token(user_id, to_adress, token_name, token_transfer_amount):
    with open(DATABASE, "r", encoding="utf-8") as file:
        data = json.load(file)
    token_list = await get_all_user_tokens(user_id)
    buy_token_adrress = token_list[token_name][2]
    
    mnemonic = data[str(user_id)][1]
    client = TonapiClient(api_key=TON_CONSOLE_API_KEY, is_testnet=IS_TESTNET)
    wallet, public_key, private_key, mnemonic = WalletV4R2.from_mnemonic(client, mnemonic)
    if token_name == "TON":
        tx_hash = await wallet.transfer(
            destination=to_adress,
            amount=token_transfer_amount,
            body="From NotTrade",
        )
    else:
        tx_hash = await wallet.transfer_jetton(
        destination=to_adress,
        jetton_master_address=buy_token_adrress,
        jetton_amount=token_transfer_amount,
        jetton_decimals=9,
        forward_payload="From NotTrade",
    )
    if DEBUG_MODE:
        print(f"Successfully transferred {token_transfer_amount} TON!")

# TON WALLET FUNCTIONAL -- END      
