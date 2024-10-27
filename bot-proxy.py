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
        print("File ether_query.txt not found.")
        return []
    except Exception as e:
        print("Failed get Query :", str(e))
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
    parsed_query = parse_qs(query)
    parsed_query = {k: v[0] for k, v in parsed_query.items()}
    user_data = json.loads(unquote(parsed_query['user']))
    parsed_query['user'] = user_data
    return parsed_query

def get_ip_info(proxy_dict=None):
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
            return data.get('query', 'Unknown'), data.get('country', 'Unknown')
        return 'Unknown', 'Unknown'
    except Exception as e:
        print_(f"Error getting IP info: {e}")
        return 'Unknown', 'Unknown'

def make_request(method, url, headers, json=None, data=None, proxy_dict=None):
    retry_count = 0
    while True:
        time.sleep(2)
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, json=json, proxies=proxy_dict, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=json, data=data, proxies=proxy_dict, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=json, data=data, proxies=proxy_dict, timeout=30)
            else:
                raise ValueError("Invalid method.")
            
            if response.status_code >= 500:
                if retry_count >= 4:
                    print_(f"Status Code: {response.status_code} | {response.text}")
                    return None
                retry_count += 1
                continue
            elif response.status_code >= 400:
                print_(f"Status Code: {response.status_code} | {response.text}")
                return None
            elif response.status_code >= 200:
                return response
        except requests.exceptions.RequestException as e:
            print_(f"Request failed: {e}")
            if retry_count >= 4:
                return None
            retry_count += 1
            continue

def print_delay(delay):
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

class Ether:
    def __init__(self):
        self.header = {
            "accept": "application/json",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "priority": "u=1, i",
            "sec-ch-ua": '"Microsoft Edge;v=129, Not=A?Brand;v=8, Chromium;v=129, Microsoft Edge WebView2;v=129"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "Referer": "https://mdkefjwsfepf.dropstab.com/",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
        self.token = None
        self.proxy_dict = None

    def _make_authenticated_request(self, method, endpoint, **kwargs):
        url = f"{BASE_URL}{endpoint}"
        headers = {**self.header, 'authorization': f"Bearer {self.token}"}
        response = make_request(method, url, headers=headers, proxy_dict=self.proxy_dict, **kwargs)
        return response.json() if response else None

    def get_token(self, query):
        url = f"{BASE_URL}/auth/login"
        headers = self.header
        payload = {"webAppData": query}
        print_("Generate Token....")
        try:
            response = make_request('post', url, headers=headers, json=payload, proxy_dict=self.proxy_dict)
            if response is not None:
                data = response.json()
                self.token = data["jwt"]["access"]["token"]
                return self.token
        except Exception as e:
            print_(f"Error Detail : {e}")

    def get_user_info(self):
        return self._make_authenticated_request("GET", "/user/current")

    def daily_bonus(self):
        response = self._make_authenticated_request("POST", "/bonus/dailyBonus")
        if response is not None:
            result = response.get('result', False)
            if result:
                print_(f"Daily login Done. Streaks: {response['streaks']}")
            else:
                print_("Daily Bonus Claimed")

    def check_tasks(self):
        tasks = self._make_authenticated_request("GET", "/quest")
        if tasks is None:
            return

        for task_group in tasks:
            group_name = task_group.get('name', '')
            quests = task_group.get('quests', [])
            
            active_quests = [quest for quest in quests if quest.get('status') == 'NEW']
            
            if not active_quests:
                continue
            
            print_(f"== Title Task : {group_name} ==")
            
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
            print_(f"Verification Task {name} : {response.get('status','')}")

    def claim_task(self, task_id, name):
        response = self._make_authenticated_request('PUT', f'/quest/{task_id}/claim')
        if response is not None:
            print_(f"Claim Task {name} : {response.get('status','')}")

    def claim_ref(self):
        print_('Claim Reff Reward')
        response = self._make_authenticated_request('POST', '/refLink/claim')
        if response is not None:
            totalReward = response.get('totalReward',0)
            print_(f"Reff claim Done, Reward : {totalReward}")

    def get_order(self):
        return self._make_authenticated_request('GET', '/order')
    
    def get_coins(self, randoms):
        return self._make_authenticated_request('GET', '/order/coins')
    
    def get_detail_coin(self, id):
        return self._make_authenticated_request('GET', f'/order/coinStats/{id}')
    
    def post_order(self, payload):
        response = self._make_authenticated_request('POST', '/order', json=payload)
        if response is not None:
            list_periods = response.get('periods',[])
            for data in list_periods:
                period = data.get('period',[])
                hours = period.get('hours')
                order = data.get('order',{})
                if len(order) > 0:
                    shorts = "Long"
                    if order.get('short'):
                        shorts = "Short"
                    coin = order.get('coin')
                    print_(f"Open {shorts} in {coin.get('symbol')} at Price {coin.get('price')} time {hours} Hours")
                    break

    def claim_order(self, order_id):
        response = self._make_authenticated_request('PUT', f'/order/{order_id}/claim')
        if response is not None:
            print_(f"Successfully claimed order {order_id}")
            return response
        return None

    def mark_checked(self, order_id):
        response = self._make_authenticated_request('PUT', f'/order/{order_id}/markUserChecked')
        if response is not None:
            print_(f"Marked order {order_id} as checked")
            return response
        return None

    def process_order(self, order, detail_coin, input_coin, input_order, period_id):
        status = order.get('status')
        order_id = order.get('id')
        coin = order.get('coin', {})
        
        if status == "CLAIM_AVAILABLE":
            print_(f"Claiming successful prediction for {coin.get('symbol')} | Reward: {order.get('reward')}")
            self.claim_order(order_id)
            return self.open_new_position(detail_coin, input_coin, input_order, period_id)
        elif status == "NOT_WIN":
            print_(f"Processing failed prediction for {coin.get('symbol')}")
            self.mark_checked(order_id)
            return self.open_new_position(detail_coin, input_coin, input_order, period_id)
        return None

    def open_new_position(self, detail_coin, input_coin, input_order, period_id):
        status_options = [True, False]  # True for Short, False for Long
        
        if input_coin == 'y':
            coins = random.choice(detail_coin)
        else:
            coins = detail_coin[0]  # Default to first coin (BTC)

        # Get sentiment data for the selected coin
        coin_stats = self.get_detail_coin(coins['id'])
        if coin_stats:
            short_percentage = coin_stats.get('short', 0)
            long_percentage = coin_stats.get('long', 0)
            print_(f"Sentiment Analysis for {coins['symbol']}:")
            print_(f"Long: {long_percentage}% | Short: {short_percentage}%")
            
            if input_order == 'l':
                status_order = status_options[1]  # Long
            elif input_order == 's':
                status_order = status_options[0]  # Short
            elif input_order == 'm':  # New option for majority-based decision
                if long_percentage > short_percentage:
                    status_order = status_options[1]  # Long
                    print_(f"Choosing Long position based on majority sentiment ({long_percentage}% > {short_percentage}%)")
                else:
                    status_order = status_options[0]  # Short
                    print_(f"Choosing Short position based on majority sentiment ({short_percentage}% > {long_percentage}%)")
            elif input_order == 'c':  # New option for counter-majority decision
                if long_percentage > short_percentage:
                    status_order = status_options[0]  # Short
                    print_(f"Choosing Short position against majority sentiment ({long_percentage}% > {short_percentage}%)")
                else:
                    status_order = status_options[1]  # Long
                    print_(f"Choosing Long position against majority sentiment ({short_percentage}% > {long_percentage}%)")
            else:
                status_order = random.choice(status_options)  # Random
        else:
            print_("Failed to get sentiment data, using random choice")
            status_order = random.choice(status_options)

        coin_id = coins.get('id')
        payload = {'coinId': coin_id, 'short': status_order, 'periodId': period_id}
        return self.post_order(payload)
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


def process_account(account_data):
    query, index, total_accounts, input_coin, input_order, auto_claim, proxies = account_data
    
    print_(f"SxG========= Account {index}/{total_accounts} =========SxG")
    
    # Setup proxy
    if proxies:
        proxy = random.choice(proxies)
        proxy_dict = format_proxy(proxy)
        print_(f"Selected proxy: {proxy}")
    else:
        proxy_dict = None
    
    # Create Ether instance with proxy
    ether = Ether()
    ether.proxy_dict = proxy_dict
    
    # Check IP using proxy
    ip, country = get_ip_info(proxy_dict)
    print_(f"Current IP: {ip} | Country: {country}")
    
    token = ether.get_token(query)
    if token is not None:
        user_info = ether.get_user_info()
        print_(f"TGID : {user_info.get('tgId','')} | Username : {user_info.get('tgUsername','None')} | Balance : {user_info.get('balance',0)}")
        ether.daily_bonus()
        ether.claim_ref()
        data_order = ether.get_order()

        if data_order is not None:
            totalScore = data_order.get('totalScore', 0)
            results = data_order.get('results', {})
            print_(f"Result Game : {results.get('orders',0)} Order | {results.get('wins',0)} Wins | {results.get('loses',0)} Loses | {results.get('winRate',0.0)} Winrate")
            
            list_periods = data_order.get('periods', [])
            detail_coin = ether.get_coins(input_order)

            for period_data in list_periods:
                period = period_data.get('period', {})
                unlock_threshold = period.get('unlockThreshold', 0)
                current_order = period_data.get('order', {})
                period_id = period.get('id', 1)

                if totalScore >= unlock_threshold:
                    if auto_claim and current_order:
                        ether.process_order(current_order, detail_coin, input_coin, input_order, period_id)
                    elif not current_order:
                        ether.open_new_position(detail_coin, input_coin, input_order, period_id)
        
        ether.check_tasks()

def main():
    input_coin = input("random choice coin y/n (BTC default)  : ").strip().lower()
    input_order = input("open order l(long), s(short), r(random), m(majority), c(counter-majority)  : ").strip().lower()
    auto_claim = input("Enable auto-claim and reopen (y/n): ").strip().lower() == 'y'
    
    # New prompt for number of threads
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
        proxies = load_proxies()
        total_accounts = len(queries)
        
        # Adjust number of threads if more than accounts
        actual_threads = min(num_threads, total_accounts)
        if actual_threads < num_threads:
            print_(f"Adjusting to {actual_threads} threads as there are only {total_accounts} accounts")
        
        # Prepare account data for threading
        account_data = [
            (query, idx + 1, total_accounts, input_coin, input_order, auto_claim, proxies)
            for idx, query in enumerate(queries)
        ]
        
        # Process accounts in parallel
        with ThreadPoolExecutor(max_workers=actual_threads) as executor:
            list(executor.map(process_account, account_data))
        
        end_time = time.time()
        processing_time = end_time - start_time
        delay = 24 * 3600 - processing_time
        
        if delay > 0:
            print_delay(delay)
        else:
            print_("Processing took longer than 24 hours. Starting next cycle immediately.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_("\nScript terminated by user")
        sys.exit(0)
    except Exception as e:
        print_(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)
