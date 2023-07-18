from concurrent.futures import ThreadPoolExecutor
from random import choice

from requests import RequestException, Session

from colors import Colors


class ProxyChecker:
    CHECK_URL = 'https://www.bing.com/'
    PROXY_MENU = {
        1: ('http', 'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt'),
        2: ('socks4', 'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt'),
        3: ('socks5', 'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt')
    }

    def __init__(self, info: bool):
        self.info = info
        self.session = Session()
        self.valid_proxies = set()

    def select_proxy(self):
        proxy_choice = choice(list(self.PROXY_MENU.keys()))
        scheme, proxy_url = self.PROXY_MENU.get(proxy_choice)
        return scheme, proxy_url

    def get_proxy(
        self, scheme: str, proxy_url: str
        ):

        response = self.session.get(proxy_url)
        proxy_list = [f'{scheme}://{proxy.strip()}' for proxy in response.text.splitlines()]
        return proxy_list

    def limit_proxy(
        self, proxy_list: list, proxy_limiter: str
        ):

        return proxy_list[:int(proxy_limiter)]

    def __check_proxy(
        self, proxy: str
        ):

        try:
            proxies = {'http': proxy, 'https': proxy}
            response = self.session.get(self.CHECK_URL, proxies=proxies, timeout=10)
            if response.status_code == 200:
                self.valid_proxies.add(proxy)
                if self.info:
                    print(f'{Colors.WHITE}[{Colors.BGREEN}LIVE{Colors.WHITE}]{Colors.END} {proxy}')
                else:
                    print(f'Got ({Colors.BGREEN}{len(self.valid_proxies)}{Colors.END}) live proxy!', end='\r')

        except RequestException:
            if self.info:
                print(f'{Colors.WHITE}[{Colors.RED}DEAD{Colors.WHITE}]{Colors.END} {proxy}')
            else:
                pass

    def start_checking(
        self, proxy_limit: list, worker=50
        ):

        with ThreadPoolExecutor(max_workers=worker) as executor:
            executor.map(self.__check_proxy, proxy_limit)
