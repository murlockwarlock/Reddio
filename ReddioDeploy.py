import time
import random
import requests
import json
from web3 import Web3
from colorama import Fore, Style, init
from solcx import install_solc, set_solc_version, compile_source

# Установка и настройка Solidity компилятора
install_solc('0.8.0')
set_solc_version('0.8.0')

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

# Загрузка ABI для redETH (нужно для статистики)
abi_data = load_from_file('abi.json')
print(f"{Fore.CYAN}Полное содержимое abi.json: {abi_data}{Style.RESET_ALL}")
try:
    parsed_abi = json.loads(abi_data)
    print(f"{Fore.GREEN}ABI успешно разобрано: {list(parsed_abi.keys())}{Style.RESET_ALL}")
except json.JSONDecodeError as e:
    print(f"{Fore.RED}Ошибка разбора ABI: {e}{Style.RESET_ALL}")
    exit()

# Константа адреса redETH
RED_ETH_ADDRESS = w3_reddio.to_checksum_address("0x4f4FDcECa7d48822E39097970b6cDBa179C28d9b")
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


# Генерация креативного названия токена
def generate_creative_token():
    adjectives = [
        "Quantum", "Stellar", "Lunar", "Solar", "Crypto", "Nebula", "Galaxy", "Ether", "Cosmic", "Radiant",
        "Celestial", "Ethereal", "Digital", "Futuristic", "Ancient", "Nova", "Atomic", "Eclipse", "Infinite", "Vortex",
        "Decentralized", "Immutable", "Transparent", "Trustless", "Encrypted", "Dynamic", "Lightning", "Hybrid",
        "Pioneering", "NextGen", "Scalable", "Adaptive", "Synthetic", "Metaverse", "Defi", "Programmable",
        "Autonomous", "Layered", "Hyper", "Spectral", "Interstellar"
    ]

    nouns = [
        "Chain", "Element", "Coin", "Token", "Crystal", "Verse", "Galaxy", "Universe", "Sphere", "Orbit",
        "Network", "Link", "Foundation", "Block", "Core", "Matrix", "Circuit", "Realm", "Force", "Core", "System",
        "Protocol", "Ledger", "Node", "Wallet", "Stake", "Mining", "Contract", "Layer", "Liquidity", "Consensus",
        "Governance", "Bridge", "Oracle", "Ecosystem", "Hash", "Nonce", "Validator", "Beacon", "Cluster",
        "Sharding", "Dapp", "SmartContract", "Gateway"
    ]

    adjective = random.choice(adjectives)
    noun = random.choice(nouns)

    name = f"{adjective} {noun}"
    contract_name = name.replace(" ", "_")
    symbol = generate_symbol(name)

    return contract_name, name, symbol


# Генерация символа токена
def generate_symbol(name):
    words = name.split()
    symbol = ''.join([word[0] for word in words]).upper()
    for word in words:
        symbol += random.choice(word[1:3]).upper()
    return symbol


# Генерация начального объема эмиссии
def generate_initial_supply():
    return random.randint(1000000, 1000000000)


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


# Развертывание контракта с повторной отправкой
def deploy_contract(private_key, max_attempts=3):
    account = w3_reddio.eth.account.from_key(private_key)
    address = account.address

    native_balance = w3_reddio.eth.get_balance(address)
    gas_price = w3_reddio.eth.gas_price
    gas_cost = gas_price * 2000000  # Примерный лимит газа для деплоя
    print(f"{Fore.CYAN}Баланс RED: {w3_reddio.from_wei(native_balance, 'ether')} RED{Style.RESET_ALL}")
    if native_balance < gas_cost:
        print(f"{Fore.RED}✗ Недостаточно RED для оплаты газа.{Style.RESET_ALL}")
        return None

    for attempt in range(max_attempts):
        try:
            contract_name, token_name, symbol = generate_creative_token()
            initial_supply = generate_initial_supply()

            updated_contract_code = f'''
            pragma solidity ^0.8.0;

            interface IERC20 {{
                function totalSupply() external view returns (uint256);
                function balanceOf(address account) external view returns (uint256);
                function transfer(address recipient, uint256 amount) external returns (bool);
                function allowance(address owner, address spender) external view returns (uint256);
                function approve(address spender, uint256 amount) external returns (bool);
                function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);

                event Transfer(address indexed from, address indexed to, uint256 value);
                event Approval(address indexed owner, address indexed spender, uint256 value);
            }}

            contract {contract_name} is IERC20 {{
                string public name = "{token_name}";
                string public symbol = "{symbol}";
                uint8 public decimals = 18;
                uint256 private _totalSupply;
                mapping(address => uint256) private _balances;
                mapping(address => mapping(address => uint256)) private _allowances;

                constructor(uint256 initialSupply) {{
                    _totalSupply = initialSupply * (10 ** uint256(decimals)); 
                    _balances[msg.sender] = _totalSupply;
                    emit Transfer(address(0), msg.sender, _totalSupply);
                }}

                function totalSupply() public view override returns (uint256) {{
                    return _totalSupply;
                }}

                function balanceOf(address account) public view override returns (uint256) {{
                    return _balances[account];
                }}

                function transfer(address recipient, uint256 amount) public override returns (bool) {{
                    require(recipient != address(0), "ERC20: transfer to the zero address");
                    require(_balances[msg.sender] >= amount, "ERC20: transfer amount exceeds balance");

                    _balances[msg.sender] -= amount;
                    _balances[recipient] += amount;

                    emit Transfer(msg.sender, recipient, amount);
                    return true;
                }}

                function allowance(address owner, address spender) public view override returns (uint256) {{
                    return _allowances[owner][spender];
                }}

                function approve(address spender, uint256 amount) public override returns (bool) {{
                    _allowances[msg.sender][spender] = amount;
                    emit Approval(msg.sender, spender, amount);
                    return true;
                }}

                function transferFrom(address sender, address recipient, uint256 amount) public override returns (bool) {{
                    require(sender != address(0), "ERC20: transfer from the zero address");
                    require(recipient != address(0), "ERC20: transfer to the zero address");
                    require(_balances[sender] >= amount, "ERC20: transfer amount exceeds balance");
                    require(_allowances[sender][msg.sender] >= amount, "ERC20: transfer amount exceeds allowance");

                    _balances[sender] -= amount;
                    _balances[recipient] += amount;
                    _allowances[sender][msg.sender] -= amount;

                    emit Transfer(sender, recipient, amount);
                    return true;
                }}
            }}
            '''

            compiled_sol = compile_source(updated_contract_code)
            contract_interface = compiled_sol[f'<stdin>:{contract_name}']
            abi = contract_interface['abi']
            bytecode = contract_interface['bin']

            TokenContract = w3_reddio.eth.contract(abi=abi, bytecode=bytecode)

            gas_estimate = TokenContract.constructor(initial_supply).estimate_gas({'from': address})
            print(f"{Fore.CYAN}Оценка газа для развертывания {token_name} ({symbol}): {gas_estimate}{Style.RESET_ALL}")

            transaction = TokenContract.constructor(initial_supply).build_transaction({
                'from': address,
                'nonce': w3_reddio.eth.get_transaction_count(address, 'pending'),
                'gas': gas_estimate + 10000,
                'gasPrice': gas_price,
            })

            signed_tx = w3_reddio.eth.account.sign_transaction(transaction, private_key)
            tx_hash = w3_reddio.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash_link = f"https://reddio-devnet.l2scan.co/tx/{w3_reddio.to_hex(tx_hash)}"
            print(
                f"{Fore.CYAN}✅ Транзакция развертывания {token_name} отправлена. Хэш: {tx_hash_link}{Style.RESET_ALL}")

            # Проверяем статус транзакции
            if check_transaction_status(tx_hash):
                receipt = w3_reddio.eth.get_transaction_receipt(tx_hash)
                print(
                    f"{Fore.GREEN}✓ Контракт {token_name} успешно развернут по адресу: {receipt.contractAddress}{Style.RESET_ALL}")
                return receipt.contractAddress
            else:
                print(
                    f"{Fore.YELLOW}Попытка {attempt + 1}/{max_attempts}: Транзакция не прошла, повторяем...{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка при отправке (попытка {attempt + 1}/{max_attempts}): {e}{Style.RESET_ALL}")
            if attempt < max_attempts - 1:
                print(f"{Fore.YELLOW}Повторяем через 10 секунд...{Style.RESET_ALL}")
                time.sleep(10)
    print(f"{Fore.RED}✗ Не удалось развернуть контракт после {max_attempts} попыток.{Style.RESET_ALL}")
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

    print(f"{Fore.CYAN}Запуск развертывания контракта для {address}{Style.RESET_ALL}")
    contract_address = deploy_contract(private_key)
    if not contract_address:
        continue

    time.sleep(random.randint(10, 30))

# Вывод статистики после обработки всех аккаунтов
print_wallet_stats(accounts)