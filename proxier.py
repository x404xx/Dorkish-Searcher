import random
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from colors import Colors


class ProxyChecker:
    CHECK_URL = 'https://www.bing.com/'
    PROXY_MENU = {
        'http': 'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
        'socks4': 'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt',
        'socks5': 'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt'
    }

    def __init__(self):
        self.session = requests.Session()
        self.live_proxies = set()
        self.dead_count = 0
        self.limiter = None

    def __del__(self):
        self.session.close()

    def start_timer(
        self, started_time: float
        ):

        elapsed = round((time.time() - started_time), 2)
        return (
            f'{Colors.BGREEN}{round(elapsed * 1000)}{Colors.END} miliseconds!'
            if elapsed < 1
            else f'{Colors.BGREEN}{elapsed}{Colors.END} seconds!'
            if elapsed < 60
            else f'{Colors.BGREEN}{int(elapsed // 60)}{Colors.END} minutes {Colors.BGREEN}{int(elapsed % 60)}{Colors.END} seconds!'
        )

    def _fetch_proxy_list(self):
        protocol = random.choice(list(self.PROXY_MENU.keys()))
        print(f'Auto selected protocol {Colors.CYAN}{protocol.upper()}{Colors.END}')
        response = self.session.get(self.PROXY_MENU.get(protocol))
        proxy_list = [f'{protocol}://{proxy.strip()}' for proxy in response.text.splitlines()]
        print(f'Found {Colors.GREEN}{len(proxy_list)}{Colors.END} proxies!')
        random.shuffle(proxy_list)
        return proxy_list

    def get_proxy_limit(self):
        proxy_list = self._fetch_proxy_list()
        self.limiter = input('How many proxies should be checked (Press ENTER to skip limit): ')
        proxy_limit = proxy_list if not self.limiter.strip() else proxy_list[:int(self.limiter)]
        return proxy_limit

    def working_proxy_iterator(
        self, proxy_limit: list, worker: int
        ):

        proxy_started = time.time()
        self._start_checking(proxy_limit, worker)
        print(f'\n\n{Colors.LYELLOW}Checking proxy time taken: {self.start_timer(proxy_started)}\n')
        return iter(list(self.live_proxies))

    def _check_proxy(
        self, proxy: str
        ):

        try:
            proxies = {'http': proxy, 'https': proxy}
            response = self.session.get(self.CHECK_URL, proxies=proxies, timeout=10)
            if 200 <= response.status_code <= 299:
                self.live_proxies.add(proxy)
            else:
                self.dead_count += 1
        except requests.RequestException:
            self.dead_count += 1
            pass

        print(f'{Colors.WHITE}Live{Colors.END}: ({Colors.BGREEN}{len(self.live_proxies)}{Colors.END}) {Colors.WHITE}Dead{Colors.END}: ({Colors.RED}{self.dead_count}{Colors.END})', end='\r')

    def _start_checking(
        self, proxy_limit: list, worker: int
        ):

        with ThreadPoolExecutor(max_workers=worker) as executor:
            executor.map(self._check_proxy, proxy_limit)
