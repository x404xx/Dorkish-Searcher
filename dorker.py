from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import cycle
from json import dump
from random import shuffle
from re import findall
from time import time

from requests import RequestException, Response, get
from user_agent import generate_user_agent as ua

from colors import Colors
from proxier import ProxyChecker


class DorkSearch:
    BASE_URL = 'https://www.google.com/search'
    ALL_URLS = set()

    @classmethod
    def __send_request(
        cls,
        dork: str,
        amount: int,
        proxies: dict,
        user_agent: str,
        timeout: int,
        lang: str
        ):

        response = get(
            cls.BASE_URL,
            headers={'User-Agent': user_agent},
            params={
                'q': dork,
                'num': amount + 2,
                'hl': lang,
            },
            proxies=proxies,
            timeout=timeout,
        )
        response.raise_for_status()
        return response

    @classmethod
    def __save_to_file(
        cls, dork: str, file_name: str
        ):

        if cls.ALL_URLS:
            results_dict = {dork: list(cls.ALL_URLS)}
            with open(f'{file_name}.json', 'a') as file:
                dump(results_dict, file, indent=4)
            print(f'\n{Colors.BYELLOW}Output saved successfully.{Colors.END}\n')
        else:
            print(f'\n{Colors.BYELLOW}No output to save.{Colors.END}\n')

    @staticmethod
    def __handle_urls(response: Response):
        return findall(r'f"><a href="(https:.*?)"', response)

    @staticmethod
    def __fetch_proxies(info: bool):
        scraper = ProxyChecker(info)
        scheme, proxy_url = scraper.select_proxy()
        print(f'Auto selected protocol {Colors.CYAN}{scheme.upper()}{Colors.END}')
        proxy_list = scraper.get_proxy(scheme, proxy_url)
        print(f'Found {Colors.GREEN}{len(proxy_list)}{Colors.END} proxies!')
        return scraper, proxy_list

    @classmethod
    def __working_proxies(
        cls, scraper: ProxyChecker, proxy_limit: list, worker: int
        ):

        proxy_started = time()
        scraper.start_checking(proxy_limit, worker)
        print(f'\n\n{Colors.LYELLOW}Checking proxy time taken: {cls.__time_taken(proxy_started)}\n')
        valid_proxies = list(scraper.valid_proxies)
        return valid_proxies

    @staticmethod
    def __proxy_limiter(
        scraper: ProxyChecker, proxy_list: list
        ):

        limiter = input('How many proxies should be check (type \'!skip\' to skip limit): ').lower()
        if limiter == '!skip':
            proxies_list = proxy_list
        else:
            proxies_list = scraper.limit_proxy(proxy_list, limiter)
        shuffle(proxies_list)
        return proxies_list

    @staticmethod
    def __time_taken(started_time):
        elapsed = round((time() - started_time), 2)

        if elapsed < 1:
            format_elapsed = f'{Colors.LBLUE}{round(elapsed * 1000)}{Colors.END} miliseconds!'
        elif elapsed < 60:
            format_elapsed = f'{Colors.LBLUE}{elapsed}{Colors.END} seconds!'
        else:
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            format_elapsed = f'{Colors.LBLUE}{minutes}{Colors.END} minutes {Colors.LBLUE}{seconds}{Colors.END} seconds!'

        return format_elapsed

    @classmethod
    def __search_dorks(
        cls,
        dork: str,
        amount: int,
        worker=50,
        info=False,
        timeout=15,
        lang='en',
        start_from=0,
        ):

        scraper, proxy_list = cls.__fetch_proxies(info)
        proxy_limit = cls.__proxy_limiter(scraper, proxy_list)
        valid_proxies = cls.__working_proxies(scraper, proxy_limit, worker)
        proxy_pool = cycle(valid_proxies)

        while start_from < amount:
            with ThreadPoolExecutor(max_workers=worker) as executor:
                futures = []

                for _ in range(amount):
                    proxy = str(next(proxy_pool))
                    user_agent = str(ua())
                    proxies = {'http': proxy, 'https': proxy}

                    if info:
                        print(f'Proxy: {Colors.BGREEN}{proxy}{Colors.END} | User-Agent: {Colors.LPURPLE}{user_agent}{Colors.END}')

                    future = executor.submit(
                        cls.__send_request,
                        dork,
                        amount - start_from,
                        proxies,
                        user_agent,
                        timeout,
                        lang
                    )
                    futures.append(future)

                for future in as_completed(futures):
                    try:
                        response = future.result()
                        urls = cls.__handle_urls(response.text)

                        for idx, url in enumerate(urls[:amount], start=start_from + 1):
                            print(f'{Colors.WHITE}{idx}. {Colors.GREEN}{url}{Colors.END}')
                            cls.ALL_URLS.add(url)
                            start_from += 1
                        
                        if start_from >= amount:
                            break

                    except RequestException as exc:
                        if len(valid_proxies) == 0:
                            print(f'{Colors.LYELLOW}No more valid proxies available. {Colors.WHITE}Scraping new proxies...{Colors.END}\n')
                            scraper, proxy_list = cls.__fetch_proxies(info)
                            proxy_limit = cls.__proxy_limiter(scraper, proxy_list)
                            valid_proxies = cls.__working_proxies(scraper, proxy_limit, worker)
                            proxy_pool = cycle(valid_proxies)
                        else:
                            if info:
                                print(f'Exception: {Colors.RED}{type(exc).__name__}{Colors.END}')
                            valid_proxies.pop(0)

                        continue

    @classmethod
    def run(
        cls,
        dork=None,
        worker=None,
        amount=None,
        info=False,
        save_output=False,
        file_name=None,
        ):

        if dork is None:
            dork = input('Dork: ')
        if amount is None:
            amount = int(input('How many URLs: '))
        if worker is None:
            worker = int(input('How many worker (Default 50): '))
        if not info:
            option = input('Do want to get info? (y/n): ').lower()
            info = True if option == 'y' else False

        search_started = time()
        cls.__search_dorks(dork, amount, worker, info)
        print(f'\n{Colors.LYELLOW}Searching time taken: {cls.__time_taken(search_started)}')
        
        if file_name is None:
            file_name = input('\nYour filename (Without Extension): ')

        cls.__save_to_file(dork, file_name) if save_output else cls.__save_to_file(dork, file_name)
