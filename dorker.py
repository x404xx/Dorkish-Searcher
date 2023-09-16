import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from user_agent import generate_user_agent

from colors import Colors
from proxier import ProxyChecker


class DorkSearch(ProxyChecker):
    BASE_URL = 'https://www.google.com/search'
    ALL_URLS = set()

    def __init__(self):
        super().__init__()

    def _send_request(
        self,
        dork: str,
        amount: int,
        proxies: dict,
        user_agent: str
        ):

        response = self.session.get(
            self.BASE_URL,
            headers={'User-Agent': user_agent},
            params={'q': dork, 'num': amount + 2, 'hl': 'en'},
            proxies=proxies,
            timeout=15
        )
        response.raise_for_status()
        return response

    def _save_to_file(
        self, dork: str, file_name: str
        ):

        if self.ALL_URLS:
            results_dict = {dork: list(self.ALL_URLS)}

            if os.path.exists(f'{file_name}.json'):
                overwrite = input(f'{Colors.RED}Warning: Output file already exists. Do you want to overwrite it? (y/n): {Colors.END}')
                if overwrite.lower() != 'y':
                    file_name = input('Enter a new filename (Without Extension): ')

            with open(f'{file_name}.json', 'w') as file:
                json.dump(results_dict, file, indent=4)
            print(f'\n{Colors.BYELLOW}Output saved successfully.{Colors.END}\n')

        else:
            print(f'\n{Colors.BYELLOW}No output to save.{Colors.END}\n')

    def _handle_urls(
        self, response: requests.Response
        ):

        soup = BeautifulSoup(response.content, 'html.parser')
        href_list = [link.get('href') for link in soup.select('div.yuRUbf a[href]')]
        return href_list

    def _search_dorks(
        self,
        dork: str,
        amount: int,
        worker: int,
        info: bool,
        start_from=0
        ):

        proxy_limit = self.get_proxy_limit()

        color_template = f'{Colors.GREEN}{{}}{Colors.RED}({Colors.WHITE}{{}}{Colors.RED}){Colors.END}'
        print(f"\nStarted: {color_template.format('Dork', dork)}, {color_template.format('Amount', amount)}, {color_template.format('Worker', worker)}, {color_template.format('Limiter', self.limiter)}, {color_template.format('Info', info)}\n")

        proxy_iterator = self.working_proxy_iterator(proxy_limit, worker)

        while start_from < amount:
            with ThreadPoolExecutor(max_workers=worker) as executor:
                futures = []

                for _ in range(amount):
                    try:
                        proxy = str(next(proxy_iterator))
                    except StopIteration:
                        print(f'\n{Colors.LYELLOW}No more valid proxies available. {Colors.WHITE}Scraping new proxies...{Colors.END}\n')
                        self.live_proxies.clear()
                        self.dead_count = 0
                        proxy_limit = self.get_proxy_limit()
                        proxy_iterator = self.working_proxy_iterator(proxy_limit, worker)
                        proxy = str(next(proxy_iterator))

                    user_agent = str(generate_user_agent())
                    proxies = {'http': proxy, 'https': proxy}

                    if info:
                        print(f'Proxy: {Colors.BGREEN}{proxy}{Colors.END} | User-Agent: {Colors.LPURPLE}{user_agent}{Colors.END}')

                    future = executor.submit(self._send_request, dork, amount - start_from, proxies, user_agent)
                    futures.append(future)

                search_started = time.time()
                for future in as_completed(futures):
                    try:
                        response = future.result()
                        if response:
                            urls = self._handle_urls(response)
                            if urls is not None:
                                for idx, url in enumerate(urls[:amount], start=start_from + 1):
                                    print(f'{Colors.WHITE}{idx}. {Colors.GREEN}{url}{Colors.END}')
                                    self.ALL_URLS.add(url)
                                    start_from += 1

                                if start_from >= amount:
                                    print(f'\n{Colors.LYELLOW}Searching time taken: {self.start_timer(search_started)}\n\n{Colors.WHITE}Finished! Please wait closing remaining thread!{Colors.END}')
                                    break
                            else:
                                print(f'\n{Colors.WHITE}No result found with the given dork{Colors.END} "{Colors.RED}{dork}{Colors.END}"\n')
                                sys.exit(0)

                    except requests.RequestException as exc:
                        if info:
                            print(f'Exception: {Colors.RED}{type(exc).__name__}{Colors.END}')
                        continue

    def run(
        self,
        dork: str=None,
        worker: int=None,
        amount: int=None,
        file_name: str=None,
        info=False,
        ):

        dork = dork or input('Dork: ')
        amount = amount or int(input('How many URLs: '))
        worker = worker or int(input('How many workers (Press ENTER for default 50): ') or 50)
        info = info or input('Do want to get info? (y/n): ').lower() == 'y'

        self._search_dorks(dork, amount, worker, info)

        file_name = file_name or input('\nYour filename (Without Extension): ')
        self._save_to_file(dork, file_name)
