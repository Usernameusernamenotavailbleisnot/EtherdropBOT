import random
import requests
import json
import time
from datetime import datetime, timedelta
import os
import sys
from urllib.parse import parse_qs, unquote
from colorama import Fore, Style, init

# Initialize colorama
init()

BASE_URL = "https://api.miniapp.dropstab.com/api"

def print_(word):
    now = datetime.now().isoformat(" ").split(".")[0]
    print(f"[{now}] | {word}")

def load_proxies():
    try:
        with open('proxies.txt', 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print_("proxies.txt file not found. Running without proxies.")
        return []

proxies = load_proxies()

def get_ip_info():
    try:
        response = requests.get('https://api.country.is', timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('ip', 'Unknown'), data.get('country', 'Unknown')
        else:
            print_(f"Failed to get IP info. Status code: {response.status_code}")
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
                response = requests.get(url, headers=headers, json=json, proxies=proxy_dict, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=json, data=data, proxies=proxy_dict, timeout=10)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=json, data=data, proxies=proxy_dict, timeout=10)
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

    def active_task_list(self):
        try:
            return self._make_authenticated_request("GET", "/quest")
        except requests.RequestException:
            print(f"{Fore.RED+Style.BRIGHT}[ Task ]: Failed to get active task list{Style.RESET_ALL}")
            return None

    def check_tasks(self):
        tasks = self.active_task_list()
        if tasks is None:
            return

        for task_group in tasks:
            group_name = task_group.get('name', '')
            quests = task_group.get('quests', [])
            
            active_quests = [
                quest for quest in quests 
                if quest.get('status') == 'NEW'
            ]
            
            if not active_quests:
                continue  # Lewati grup tugas ini jika tidak ada tugas aktif
            
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

def parse_query(query: str):
    parsed_query = parse_qs(query)
    parsed_query = {k: v[0] for k, v in parsed_query.items()}
    user_data = json.loads(unquote(parsed_query['user']))
    parsed_query['user'] = user_data
    return parsed_query

def print_delay(delay):
    print()
    while delay > 0:
        now = datetime.now().isoformat(" ").split(".")[0]
        hours, remainder = divmod(delay, 3600)
        minutes, seconds = divmod(remainder, 60)
        sys.stdout.write(f"\r[{now}] | Waiting Time: {round(hours)} hours, {round(minutes)} minutes, and {round(seconds)} seconds")
        sys.stdout.flush()
        time.sleep(1)
        delay -= 1
    print_("\nWaiting Done, Starting....\n")
       
def main():
    input_coin = input("random choice coin y/n (BTC default)  : ").strip().lower()
    input_order = input("open order l(long), s(short), r(random)  : ").strip().lower()
    while True:
        start_time = time.time()
        clear_terminal()
        queries = load_query()
        sum = len(queries)
        ether = Ether()
        for index, query in enumerate(queries, start=1):
            print_(f"SxG========= Account {index}/{sum} =========SxG")
            
            # Check IP once per account
            proxy = random.choice(proxies) if proxies else None
            ether.proxy_dict = {'http': proxy, 'https': proxy} if proxy else None
            ip, country = get_ip_info()
            print_(f"Current IP: {ip} | Country: {country}")
            
            token = ether.get_token(query)
            if token is not None:
                user_info = ether.get_user_info()
                print_(f"TGID : {user_info.get('tgId','')} | Username : {user_info.get('tgUsername','None')} | Balance : {user_info.get('balance',0)}")
                ether.daily_bonus()
                ether.claim_ref()
                data_order = ether.get_order()
                if data_order is not None:
                    totalScore = data_order.get('totalScore',0)
                    results = data_order.get('results',{})
                    print_(f"Result Game : {results.get('orders',0)} Order | {results.get('wins',0)} Wins | {results.get('loses',0)} Loses | {results.get('winRate',0.0)} Winrate")
                    list_periods = data_order.get('periods',[])
                    detail_coin = ether.get_coins(input_order)
                    for list in list_periods:
                        period = list.get('period',{})
                        unlockThreshold = period.get('unlockThreshold',0)
                        detail_order = list.get('order',{})
                        id = period.get('id',1)
                        if totalScore >= unlockThreshold:
                            status = [True, False]
                            if input_coin =='y':
                                coins = random.choice(detail_coin)
                            else:
                                coins = detail_coin[0]

                            if input_order == 'l':
                                status_order = status[1]
                            elif input_order == 's':
                                status_order = status[0]
                            else:
                                status_order = random.choice(status)
                            if detail_order is None:
                                coin_id = coins.get('id')
                                payload = {'coinId': coin_id, 'short': status_order, 'periodId': id}
                                ether.post_order(payload)
                        
                ether.check_tasks()                

        end_time = time.time()
        processing_time = end_time - start_time
        delay = 24 * 3600 - processing_time  # 24 hours minus processing time
        if delay > 0:
            print_delay(delay)
        else:
            print_("Processing took longer than 24 hours. Starting next cycle immediately.")

if __name__ == "__main__":
     main()
