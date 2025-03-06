import time
import random
import requests
import json
from web3 import Web3
from colorama import Fore, Style, init

# Инициализация colorama
init(autoreset=True)


# Подключение к Reddio
def connect_to_reddio(max_retries=5):
    for attempt in range(max_retries):
        w3 = Web3(Web3.HTTPProvider('https://reddio-dev.reddio.com'))
        if w3.is_connected():
            print(f"{Fore.GREEN}Успешно подключились к сети Reddio (ChainID: 50341).{Style.RESET_ALL}")
            return w3
        print(f"{Fore.YELLOW}Попытка {attempt + 1}/{max_retries}: Не удалось подключиться к Reddio.{Style.RESET_ALL}")
        time.sleep(5)
    print(f"{Fore.RED}Не удалось подключиться к Reddio после {max_retries} попыток.{Style.RESET_ALL}")
    exit()


# Чтение файлов
def load_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
        if not content:
            raise ValueError(f"Файл {file_path} пуст!")
        return content
    except FileNotFoundError:
        print(f"{Fore.RED}Файл {file_path} не найден!{Style.RESET_ALL}")
        exit()
    except Exception as e:
        print(f"{Fore.RED}Ошибка чтения файла {file_path}: {e}{Style.RESET_ALL}")
        exit()


accounts = load_from_file('accounts.txt').splitlines()
proxies = load_from_file('proxies.txt').splitlines()

# Проверка количества данных
if len(accounts) != len(proxies):
    print(
        f"{Fore.RED}Количество аккаунтов ({len(accounts)}) и прокси ({len(proxies)}) не совпадает!{Style.RESET_ALL}")
    exit()

w3_reddio = connect_to_reddio()

# Загрузка и проверка ABI
abi_data = load_from_file('abi.json')
print(f"{Fore.CYAN}Полное содержимое abi.json: {abi_data}{Style.RESET_ALL}")
try:
    parsed_abi = json.loads(abi_data)
    print(f"{Fore.GREEN}ABI успешно разобрано: {list(parsed_abi.keys())}{Style.RESET_ALL}")
except json.JSONDecodeError as e:
    print(f"{Fore.RED}Ошибка разбора ABI: {e}{Style.RESET_ALL}")
    exit()

# Константы адресов
WITHDRAW_CONTRACT_ADDRESS = w3_reddio.to_checksum_address("0xA3ED8915aE346bF85E56B6BB6b723091716f58b4")
RED_ETH_ADDRESS = w3_reddio.to_checksum_address("0x4f4FDcECa7d48822E39097970b6cDBa179C28d9b")

# Создание контрактов
withdraw_contract = w3_reddio.eth.contract(address=WITHDRAW_CONTRACT_ADDRESS, abi=parsed_abi['withdraw_contract'])
red_eth_contract = w3_reddio.eth.contract(address=RED_ETH_ADDRESS, abi=parsed_abi['token'])


# Проверка прокси
def check_proxy(proxy, max_retries=3):
    for attempt in range(max_retries):
        try:
            session = requests.Session()
            session.proxies = {'http': proxy, 'https': proxy}
            response = session.get('https://httpbin.org/ip', timeout=30)
            if response.status_code == 200:
                print(f"{Fore.GREEN}✓ Прокси {proxy} работает (IP: {response.json().get('origin')}).{Style.RESET_ALL}")
                return True
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка проверки прокси {proxy}: {e}{Style.RESET_ALL}")
        time.sleep(2)
    return False


# Генерация суммы вывода (уменьшен диапазон)
def generate_random_amount():
    return w3_reddio.to_wei(random.uniform(0.0001, 0.0019), 'ether')


# Динамическая цена газа
def get_dynamic_gas_price(w3):
    base_gas_price = w3.eth.gas_price
    variation = random.uniform(0.8, 1.2)
    dynamic_gas_price = int(base_gas_price * variation)
    print(
        f"{Fore.CYAN}Текущая цена газа: {w3.from_wei(base_gas_price, 'gwei')} Gwei, применённая: {w3.from_wei(dynamic_gas_price, 'gwei')} Gwei{Style.RESET_ALL}")
    return dynamic_gas_price


# Проверка статуса транзакции
def check_transaction_status(tx_hash, max_checks=5, wait_time=30):
    for attempt in range(max_checks):
        try:
            receipt = w3_reddio.eth.get_transaction_receipt(tx_hash)
            if receipt:
                if receipt.status == 1:
                    tx_hash_link = f"https://reddio-devnet.l2scan.co/tx/{tx_hash.hex()}"
                    print(f"{Fore.GREEN}✓ Транзакция подтверждена. Хэш: {tx_hash_link}{Style.RESET_ALL}")
                    return True
                else:
                    print(f"{Fore.RED}✗ Транзакция провалилась. Статус: {receipt.status}{Style.RESET_ALL}")
                    return False
            else:
                print(
                    f"{Fore.YELLOW}Проверка {attempt + 1}/{max_checks}: Транзакция ещё не подтверждена, ждем...{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}Проверка {attempt + 1}/{max_checks}: Ошибка проверки: {e}{Style.RESET_ALL}")
        time.sleep(wait_time)
    print(f"{Fore.RED}✗ Транзакция не подтверждена после {max_checks} проверок.{Style.RESET_ALL}")
    return False


# Выполнение withdrawETH в Reddio с повторной отправкой
def send_withdraw_eth_transaction(nonce, private_key, recipient, amount_wei, max_attempts=3):
    account = w3_reddio.eth.account.from_key(private_key)
    address = account.address
    gas_price = get_dynamic_gas_price(w3_reddio)
    gas_cost = gas_price * 120000

    native_balance = w3_reddio.eth.get_balance(address)
    red_eth_balance = red_eth_contract.functions.balanceOf(address).call()
    print(
        f"{Fore.CYAN}Баланс: {w3_reddio.from_wei(native_balance, 'ether')} RED, {w3_reddio.from_wei(red_eth_balance, 'ether')} redETH{Style.RESET_ALL}")

    if native_balance < gas_cost:
        print(f"{Fore.RED}✗ Недостаточно RED для оплаты газа.{Style.RESET_ALL}")
        return None
    if red_eth_balance < amount_wei:
        print(f"{Fore.RED}✗ Недостаточно redETH для вывода.{Style.RESET_ALL}")
        return None

    for attempt in range(max_attempts):
        try:
            tx = withdraw_contract.functions.withdrawETH(recipient, amount_wei).build_transaction({
                'chainId': 50341, 'gas': 120000, 'gasPrice': gas_price, 'nonce': nonce
            })
            signed_tx = w3_reddio.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3_reddio.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash_link = f"https://reddio-devnet.l2scan.co/tx/{tx_hash.hex()}"
            print(f"{Fore.CYAN}✅ Транзакция withdrawETH отправлена. Хэш: {tx_hash_link}{Style.RESET_ALL}")

            # Проверяем статус транзакции
            if check_transaction_status(tx_hash):
                balance_after = red_eth_contract.functions.balanceOf(address).call()
                print(
                    f"{Fore.GREEN}✓ Вывод успешен. Баланс redETH после: {w3_reddio.from_wei(balance_after, 'ether')} redETH{Style.RESET_ALL}")
                return tx_hash
            else:
                print(
                    f"{Fore.YELLOW}Попытка {attempt + 1}/{max_attempts}: Транзакция не прошла, повторяем...{Style.RESET_ALL}")
                nonce = w3_reddio.eth.get_transaction_count(address, 'pending')  # Обновляем nonce
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка при отправке (попытка {attempt + 1}/{max_attempts}): {e}{Style.RESET_ALL}")
            if attempt < max_attempts - 1:
                print(f"{Fore.YELLOW}Повторяем через 10 секунд...{Style.RESET_ALL}")
                time.sleep(10)
                nonce = w3_reddio.eth.get_transaction_count(address, 'pending')  # Обновляем nonce
    print(f"{Fore.RED}✗ Не удалось выполнить withdrawETH после {max_attempts} попыток.{Style.RESET_ALL}")
    return None


# Вывод статистики по кошелькам
def print_wallet_stats(accounts):
    print(f"{Fore.MAGENTA}=== Статистика по кошелькам ==={Style.RESET_ALL}")
    for i, private_key in enumerate(accounts):
        account = w3_reddio.eth.account.from_key(private_key)
        address = account.address
        native_balance = w3_reddio.eth.get_balance(address)
        red_eth_balance = red_eth_contract.functions.balanceOf(address).call()
        print(f"{Fore.CYAN}Кошелек #{i + 1}: {address}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Баланс RED: {w3_reddio.from_wei(native_balance, 'ether')} RED{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Баланс redETH: {w3_reddio.from_wei(red_eth_balance, 'ether')} redETH{Style.RESET_ALL}")
        print(f"{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")


# Основной процесс
print(f"{Fore.MAGENTA}Всего аккаунтов для обработки: {len(accounts)}{Style.RESET_ALL}")
for i in range(len(accounts)):
    private_key = accounts[i]
    proxy = proxies[i]
    account = w3_reddio.eth.account.from_key(private_key)
    address = account.address

    print(f"{Fore.MAGENTA}=== Обработка аккаунта: {address} (#{i + 1}/{len(accounts)}) ==={Style.RESET_ALL}")
    if not check_proxy(proxy):
        continue

    nonce_reddio = w3_reddio.eth.get_transaction_count(address, 'pending')
    amount_wei = generate_random_amount()
    print(f"{Fore.CYAN}Сумма для вывода: {w3_reddio.from_wei(amount_wei, 'ether')} redETH{Style.RESET_ALL}")
    tx_hash_reddio = send_withdraw_eth_transaction(nonce_reddio, private_key, address, amount_wei)
    if not tx_hash_reddio:
        continue

    time.sleep(random.randint(10, 30))

# Вывод статистики после обработки всех аккаунтов
print_wallet_stats(accounts)