import base64
import json
import os
import random
import sys
import time
from urllib.parse import parse_qs, unquote
import requests
from datetime import datetime, timedelta
from colorama import Fore, Style, init
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import math
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize colorama
init()

BASE_URL = "https://api.miniapp.dropstab.com/api"
print_lock = Lock()

def print_(word):
    now = datetime.now().isoformat(" ").split(".")[0]
    with print_lock:
        print(f"[{now}] | {word}")

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')
    
def load_query():
    try:
        with open('ether_query.txt', 'r') as f:
            queries = [line.strip() for line in f.readlines()]
        return queries
    except FileNotFoundError:
        print_("File ether_query.txt not found.")
        return []
    except Exception as e:
        print_("Failed get Query:", str(e))
        return []

def load_proxies():
    try:
        with open('proxies.txt', 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print_("proxies.txt file not found. Running without proxies.")
        return []

def format_proxy(proxy):
    """Format proxy string correctly"""
    if not proxy:
        return None
    
    # Remove any whitespace
    proxy = proxy.strip()
    
    # Check if proxy already has protocol
    if proxy.startswith(('http://', 'https://')):
        return {'http': proxy, 'https': proxy}
    
    # Add protocol if not present
    return {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }

def parse_query(query: str):
    try:
        parsed_query = parse_qs(query)
        parsed_query = {k: v[0] for k, v in parsed_query.items()}
        user_data = json.loads(unquote(parsed_query['user']))
        parsed_query['user'] = user_data
        return parsed_query
    except Exception as e:
        print_(f"Error parsing query: {str(e)}")
        return None

def get_ip_info(proxy_dict=None):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(
            'https://api.country.is/', 
            headers=headers,
            proxies=proxy_dict, 
            timeout=30,
            verify=False
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('query', 'Unknown'), data.get('country', 'Unknown')
        return 'Unknown', 'Unknown'
    except Exception as e:
        print_(f"Error getting IP info: {e}")
        return 'Unknown', 'Unknown'

def make_request(method, url, headers, json=None, data=None, proxy_dict=None):
    retry_count = 0
    max_retries = 4
    while retry_count <= max_retries:
        try:
            time.sleep(2)  # Rate limiting
            kwargs = {
                'headers': headers,
                'proxies': proxy_dict,
                'timeout': 60,
                'verify': False
            }
            
            if json is not None:
                kwargs['json'] = json
            if data is not None:
                kwargs['data'] = data
                
            response = requests.request(method.upper(), url, **kwargs)
            
            if response.status_code >= 500:
                if retry_count >= max_retries:
                    print_(f"Server error (status {response.status_code}): {response.text}")
                    return None
                retry_count += 1
                continue
                
            if response.status_code >= 400:
                print_(f"Client error (status {response.status_code}): {response.text}")
                return None
                
            return response
            
        except requests.exceptions.RequestException as e:
            print_(f"Request failed: {e}")
            if retry_count >= max_retries:
                return None
            retry_count += 1
            continue
        except Exception as e:
            print_(f"Unexpected error: {e}")
            if retry_count >= max_retries:
                return None
            retry_count += 1
            continue

def print_delay(delay):
    try:
        print()
        while delay > 0:
            now = datetime.now().isoformat(" ").split(".")[0]
            hours, remainder = divmod(delay, 3600)
            minutes, seconds = divmod(remainder, 60)
            with print_lock:
                sys.stdout.write(f"\r[{now}] | Waiting Time: {round(hours)} hours, {round(minutes)} minutes, and {round(seconds)} seconds")
                sys.stdout.flush()
            time.sleep(1)
            delay -= 1
        print_("\nWaiting Done, Starting....\n")
    except Exception as e:
        print_(f"Error in delay timer: {str(e)}")

class Ether:
    def __init__(self):
        self.header = {
            "accept": "application/json",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "origin": "https://miniapp.dropstab.com",
            "priority": "u=1, i",
            "referer": "https://miniapp.dropstab.com/",
            "sec-ch-ua": '"Chromium";v="130", "Microsoft Edge";v="130", "Not?A_Brand";v="99", "Microsoft Edge WebView2";v="130"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"
        }
        self.token = None
        self.proxy_dict = None
        self.token = None
        self.proxy_dict = None

    def get_token(self, query):
        url = f"{BASE_URL}/auth/login"
        headers = self.header
        payload = {"webAppData": query}
        print_("Generate Token....")
        try:
            response = make_request('post', url, headers=headers, json=payload, proxy_dict=self.proxy_dict)
            if response is not None:
                data = response.json()
                self.token = data.get("jwt", {}).get("access", {}).get("token")
                if self.token:
                    return self.token
                print_("Token not found in response")
            return None
        except Exception as e:
            print_(f"Error getting token: {str(e)}")
            return None

    def _make_authenticated_request(self, method, endpoint, **kwargs):
        if not self.token:
            print_("No authentication token available")
            return None
            
        url = f"{BASE_URL}{endpoint}"
        headers = {**self.header, 'authorization': f"Bearer {self.token}"}
        
        try:
            response = make_request(method, url, headers=headers, proxy_dict=self.proxy_dict, **kwargs)
            if response is None:
                return None
            return response.json()
        except Exception as e:
            print_(f"Error in authenticated request to {endpoint}: {str(e)}")
            return None

    def get_user_info(self):
        return self._make_authenticated_request("GET", "/user/current")

    def daily_bonus(self, auto_tasks):
            
        response = self._make_authenticated_request("POST", "/bonus/dailyBonus")
        if response is not None:
            result = response.get('result', False)
            if result:
                print_(f"Daily login Done. Streaks: {response.get('streaks', 0)}")
            else:
                print_("Daily Bonus Claimed")

    def check_tasks(self, auto_tasks):
        if not auto_tasks:
            print_("Tasks check skipped - auto tasks disabled")
            return
            
        tasks = self._make_authenticated_request("GET", "/quest")
        if tasks is None:
            return

        for task_group in tasks:
            group_name = task_group.get('name', '')
            quests = task_group.get('quests', [])
            
            active_quests = [quest for quest in quests if quest.get('status') == 'NEW']
            
            if not active_quests:
                continue
            
            print_(f"== Title Task: {group_name} ==")
            
            for quest in active_quests:
                name = quest.get('name', '')
                reward = quest.get('reward', 0)
                claim_allowed = quest.get('claimAllowed', False)
                
                print_(f"Processing task: {name} | Reward: {reward}")
                
                if claim_allowed:
                    self.claim_task(quest["id"], name)
                else:
                    self.verify_task(quest["id"], name)

    def verify_task(self, task_id, name):
        response = self._make_authenticated_request('PUT', f'/quest/{task_id}/verify')
        if response is not None:
            print_(f"Verification Task {name}: {response.get('status', '')}")

    def claim_task(self, task_id, name):
        response = self._make_authenticated_request('PUT', f'/quest/{task_id}/claim')
        if response is not None:
            print_(f"Claim Task {name}: {response.get('status', '')}")

    def claim_ref(self, auto_tasks):
        if not auto_tasks:
            print_('Referral claim skipped - auto tasks disabled')
            return
            
        print_('Claim Reff Reward')
        response = self._make_authenticated_request('POST', '/refLink/claim')
        if response is not None:
            totalReward = response.get('totalReward', 0)
            print_(f"Reff claim Done, Reward: {totalReward}")

    def get_order(self):
        return self._make_authenticated_request('GET', '/order')
    
    def get_coins(self, randoms):
        return self._make_authenticated_request('GET', '/order/coins')
    
    def get_detail_coin(self, id):
        return self._make_authenticated_request('GET', f'/order/coinStats/{id}')
    
    def post_order(self, payload):
        response = self._make_authenticated_request('POST', '/order', json=payload)
        if response is not None:
            list_periods = response.get('periods', [])
            for data in list_periods:
                period = data.get('period', {})
                hours = period.get('hours')
                order = data.get('order', {})
                if order:
                    shorts = "Long"
                    if order.get('short'):
                        shorts = "Short"
                    coin = order.get('coin', {})
                    print_(f"Open {shorts} in {coin.get('symbol')} at Price {coin.get('price')} time {hours} Hours")
                    break
        return response

    def claim_order(self, order_id):
        return self._make_authenticated_request('PUT', f'/order/{order_id}/claim')

    def mark_checked(self, order_id):
        return self._make_authenticated_request('PUT', f'/order/{order_id}/markUserChecked')

    def process_order(self, order, detail_coin, input_coin, input_order, period_id):
        if not order:
            return None
            
        status = order.get('status')
        order_id = order.get('id')
        coin = order.get('coin', {})
        
        if not all([status, order_id, coin]):
            return None

        try:
            if status == "CLAIM_AVAILABLE":
                print_(f"Claiming successful prediction for {coin.get('symbol', 'Unknown')} | Reward: {order.get('reward', 0)}")
                claim_response = self.claim_order(order_id)
                if claim_response:
                    return self.open_new_position(detail_coin, input_coin, input_order, period_id)
            elif status == "NOT_WIN":
                print_(f"Processing failed prediction for {coin.get('symbol', 'Unknown')}")
                mark_response = self.mark_checked(order_id)
                if mark_response:
                    return self.open_new_position(detail_coin, input_coin, input_order, period_id)
        except Exception as e:
            print_(f"Error processing order: {str(e)}")
        
        return None

    def open_new_position(self, detail_coin, input_coin, input_order, period_id):
        if not detail_coin:
            return None
            
        try:
            if input_coin == 'y':
                coins = random.choice(detail_coin)
            else:
                coins = detail_coin[0]  # Default to first coin (BTC)

            coin_stats = self.get_detail_coin(coins['id'])
            if not coin_stats:
                return None

            short_percentage = coin_stats.get('short', 0)
            long_percentage = coin_stats.get('long', 0)
            
            print_(f"Sentiment Analysis for {coins['symbol']}:")
            print_(f"Long: {long_percentage}% | Short: {short_percentage}%")
            
            status_order = self._determine_position(input_order, long_percentage, short_percentage)
            
            payload = {
                'coinId': coins['id'],
                'short': status_order,
                'periodId': period_id
            }
            
            return self.post_order(payload)
            
        except Exception as e:
            print_(f"Error opening new position: {str(e)}")
            return None

    def _determine_position(self, input_order, long_percentage, short_percentage):
        if input_order == 'l':
            return False  # Long
        elif input_order == 's':
            return True   # Short
        elif input_order == 'm':
            return short_percentage > long_percentage
        elif input_order == 'c':
            return long_percentage > short_percentage
        else:
            return random.choice([True, False])

def process_account(account_data):
    try:
        query, index, total_accounts, input_coin, input_order, auto_claim, auto_tasks, proxies = account_data
        
        print_(f"========= Account {index}/{total_accounts} =========")
        
        if not query:
            print_("Invalid query data")
            return
            
        ether = Ether()
        
        # Setup proxy if available
        if proxies:
            proxy = random.choice(proxies)
            ether.proxy_dict = format_proxy(proxy)
            print_(f"Selected proxy: {proxy}")
            
            # Verify proxy
            ip, country = get_ip_info(ether.proxy_dict)
            print_(f"Current IP: {ip} | Country: {country}")
        
        # Initialize session
        token = ether.get_token(query)
        if not token:
            print_("Failed to get authentication token")
            return
            
        # Get user info
        user_info = ether.get_user_info()
        if user_info:
            print_(f"TGID: {user_info.get('tgId','')} | Username: {user_info.get('tgUsername','None')} | Balance: {user_info.get('balance',0)}")
        
        # Process daily tasks if enabled
        ether.daily_bonus(auto_tasks)
        ether.claim_ref(auto_tasks)
        
        # Get and process orders
        data_order = ether.get_order()
        if not data_order:
            print_("Failed to get order data")
            return
            
        process_orders(ether, data_order, input_coin, input_order, auto_claim)
        
        # Check remaining tasks if enabled
        ether.check_tasks(auto_tasks)
        
    except Exception as e:
        print_(f"Error processing account: {str(e)}")

def process_orders(ether, data_order, input_coin, input_order, auto_claim):
    try:
        results = data_order.get('results', {})
        print_(f"Game Results: {results.get('orders',0)} Orders | {results.get('wins',0)} Wins | {results.get('loses',0)} Loses | {results.get('winRate',0.0)}% Winrate")
        
        total_score = data_order.get('totalScore', 0)
        periods = data_order.get('periods', [])
        detail_coin = ether.get_coins(input_order)
        
        if not detail_coin:
            print_("Failed to get coin details")
            return
            
        for period_data in periods:
            period = period_data.get('period', {})
            if not period:
                continue
                
            unlock_threshold = period.get('unlockThreshold', 0)
            current_order = period_data.get('order', {})
            period_id = period.get('id')
            
            if total_score >= unlock_threshold:
                if auto_claim and current_order:
                    ether.process_order(current_order, detail_coin, input_coin, input_order, period_id)
                elif not current_order:
                    ether.open_new_position(detail_coin, input_coin, input_order, period_id)
                    
    except Exception as e:
        print_(f"Error processing orders: {str(e)}")

def test_proxy(proxy_dict):
    if not proxy_dict:
        return False
        
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(
            'http://ip-api.com/json', 
            headers=headers,
            proxies=proxy_dict, 
            timeout=30,
            verify=False
        )
        if response.status_code == 200:
            data = response.json()
            print_(f"Proxy working. IP: {data.get('query')} Country: {data.get('country')}")
            return True
        return False
    except Exception as e:
        print_(f"Proxy test failed: {str(e)}")
        return False

def main():
    try:
        input_coin = input("Random choice coin y/n (BTC default): ").strip().lower()
        input_order = input("Open order l(long), s(short), r(random), m(majority), c(counter-majority): ").strip().lower()
        auto_claim = input("Enable auto-claim and reopen (y/n): ").strip().lower() == 'y'
        auto_tasks = input("Enable auto-complete tasks (y/n): ").strip().lower() == 'y'
        
        while True:
            try:
                num_threads = int(input("Enter number of threads (1-10): ").strip())
                if 1 <= num_threads <= 10:
                    break
                print_("Please enter a number between 1 and 10")
            except ValueError:
                print_("Please enter a valid number")
        
        while True:
            start_time = time.time()
            clear_terminal()
            
            queries = load_query()
            if not queries:
                print_("No queries loaded. Please check ether_query.txt")
                return
                
            proxies = load_proxies()
            total_accounts = len(queries)
            
            actual_threads = min(num_threads, total_accounts)
            if actual_threads < num_threads:
                print_(f"Adjusting to {actual_threads} threads as there are only {total_accounts} accounts")
            
            account_data = [
                (query, idx + 1, total_accounts, input_coin, input_order, auto_claim, auto_tasks, proxies)
                for idx, query in enumerate(queries)
            ]
            
            with ThreadPoolExecutor(max_workers=actual_threads) as executor:
                list(executor.map(process_account, account_data))
            
            end_time = time.time()
            delay = 7200 - (end_time - start_time)
            
            if delay > 0:
                print_delay(delay)
            else:
                print_("Processing took longer than expected. Starting next cycle immediately.")
                
    except KeyboardInterrupt:
        print_("\nScript terminated by user")
        sys.exit(0)
    except Exception as e:
        print_(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
