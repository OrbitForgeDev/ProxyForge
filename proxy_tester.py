# proxy_tester.py
import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector
import aiohttp_socks
from urllib.parse import urlparse
import sys
from datetime import datetime
from tqdm import tqdm
from collections import defaultdict
import argparse
import os
from pathlib import Path

# Добавляем пути для импорта
sys.path.insert(0, str(Path(__file__).parent))

from locales import i18n
from config.settings import config

class ProxyTester:
    def __init__(self, input_file=None, output_file=None, timeout=None, 
                 max_concurrent=None, lang=None):
        # Загружаем настройки из конфига
        self.input_file = input_file or config.get_default_input_file('standard')
        self.output_file = output_file or config.get_default_output_file('standard')
        self.timeout = timeout or config.get('timeout', 10)
        self.max_concurrent = max_concurrent or config.get('max_concurrent', 50)
        
        # Устанавливаем язык
        self.lang = lang or config.get('language', 'en')
        i18n.set_language(self.lang)
        
        self.working_proxies = []
        self.working_by_type = defaultdict(list)
        self.test_urls = config.get('test_urls', [
            'http://httpbin.org/ip',
            'https://api.ipify.org?format=json',
            'http://ifconfig.me/ip'
        ])
        
    def _t(self, key, **kwargs):
        """Helper метод для получения перевода"""
        return i18n.get(key, **kwargs)
    
    def read_proxies(self):
        """Читает прокси из файла"""
        proxies = []
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        proxy = self.normalize_proxy(line)
                        if proxy:
                            proxies.append(proxy)
            
            print(self._t('loading_proxies', 
                         count=len(proxies), 
                         file=self.input_file))
            return proxies
        except FileNotFoundError:
            print(self._t('file_not_found', file=self.input_file))
            return []
    
    def normalize_proxy(self, proxy_str):
        """Приводит прокси к единому формату"""
        proxy_str = proxy_str.strip()
        
        # Если уже есть схема
        if proxy_str.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
            return proxy_str
        
        # Если есть только IP:PORT
        if ':' in proxy_str:
            parts = proxy_str.split(':')
            if len(parts) >= 2:
                port = parts[-1]
                port = int(port) if port.isdigit() else 0
                
                socks_ports = config.get('socks_ports', [1080, 1081, 9050, 9150, 5805])
                if port in socks_ports:
                    return f"socks5://{proxy_str}"
                else:
                    return f"http://{proxy_str}"
        
        return None
    
    def get_proxy_type(self, proxy_url):
        """Определяет тип прокси"""
        if proxy_url.startswith('socks5://'):
            return 'socks5'
        elif proxy_url.startswith('socks4://'):
            return 'socks4'
        elif proxy_url.startswith('https://'):
            return 'https'
        elif proxy_url.startswith('http://'):
            return 'http'
        return 'http'
    
    async def test_single_proxy(self, proxy_url):
        """Тестирует один прокси"""
        proxy_type = self.get_proxy_type(proxy_url)
        
        for test_url in self.test_urls:
            try:
                if proxy_type in ['socks4', 'socks5']:
                    connector = ProxyConnector.from_url(proxy_url)
                else:
                    connector = aiohttp.TCPConnector()
                
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    proxy_auth = None
                    if proxy_type in ['http', 'https']:
                        proxy_auth = proxy_url
                    
                    async with session.get(
                        test_url, 
                        proxy=proxy_auth if proxy_type in ['http', 'https'] else None,
                        timeout=timeout
                    ) as response:
                        if response.status == 200:
                            text = await response.text()
                            if 'ip' in text.lower() or len(text) > 5:
                                return True, proxy_url, self._t('working_proxy', 
                                                              type=proxy_type.upper(), 
                                                              info=text[:100])
                
            except aiohttp_socks.ProxyConnectionError as e:
                return False, proxy_url, self._t('proxy_connection_error', error=str(e))
            except asyncio.TimeoutError:
                return False, proxy_url, self._t('timeout_error', timeout=self.timeout)
            except aiohttp.ClientError as e:
                return False, proxy_url, self._t('client_error', error=str(e))
            except Exception as e:
                return False, proxy_url, self._t('unknown_error', error=str(e))
        
        return False, proxy_url, self._t('test_failed')
    
    async def test_proxies_batch(self, proxies):
        """Тестирует прокси батчами с прогресс-баром"""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def test_with_semaphore(proxy):
            async with semaphore:
                return await self.test_single_proxy(proxy)
        
        tasks = [test_with_semaphore(proxy) for proxy in proxies]
        
        results = []
        working_count = 0
        
        with tqdm(total=len(proxies), desc=self._t('testing'), unit="шт",
                  bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] {postfix}") as pbar:
            for coro in asyncio.as_completed(tasks):
                is_working, proxy, message = await coro
                results.append((is_working, proxy, message))
                
                if is_working:
                    working_count += 1
                    self.working_proxies.append(proxy)
                    proxy_type = self.get_proxy_type(proxy)
                    self.working_by_type[proxy_type].append(proxy)
                
                pbar.update(1)
                pbar.set_postfix({
                    self._t('progress.working_label'): working_count,
                    self._t('progress.last_label'): proxy.split('://')[-1][:30] if proxy else '...'
                })
        
        return results
    
    def save_working_proxies(self):
        """Сохраняет рабочие прокси в файл с сортировкой по типам"""
        if not self.working_proxies:
            print(self._t('no_working_proxies'))
            return
        
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                # Заголовок
                f.write(f"# {self._t('app_title')} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# {self._t('total_checked', count=len(self.working_proxies))}\n")
                f.write(f"# {self._t('sorting')}\n")
                f.write("#" + "=" * 58 + "\n\n")
                
                # Статистика по типам
                f.write(f"# {self._t('working_by_type')}\n")
                for proxy_type in ['socks5', 'socks4', 'https', 'http']:
                    count = len(self.working_by_type.get(proxy_type, []))
                    if count > 0:
                        f.write(f"#   {proxy_type.upper()}: {count}\n")
                f.write("\n")
                
                # Сортируем по приоритету
                type_order = ['socks5', 'socks4', 'https', 'http']
                
                for proxy_type in type_order:
                    proxies_list = self.working_by_type.get(proxy_type, [])
                    if proxies_list:
                        f.write(f"\n# ========== {proxy_type.upper()} ({len(proxies_list)} pcs) ==========\n")
                        for proxy in sorted(proxies_list):
                            f.write(f"{proxy}\n")
            
            print(self._t('saved_proxies', count=len(self.working_proxies), file=self.output_file))
            print(self._t('saved_sorted'))
            
        except Exception as e:
            print(self._t('unknown_error', error=str(e)))
    
    async def run(self):
        """Запускает тестирование"""
        print("=" * 60)
        print(f"🚀 {self._t('app_title')} v2.0")
        print("=" * 60)
        
        proxies = self.read_proxies()
        if not proxies:
            print(self._t('no_proxies'))
            return
        
        print(self._t('testing_start', count=len(proxies)))
        print(self._t('timeout_setting', timeout=self.timeout))
        print(self._t('concurrent_setting', concurrent=self.max_concurrent))
        print("-" * 60)
        
        await self.test_proxies_batch(proxies)
        
        working = len(self.working_proxies)
        
        print("\n" + "-" * 60)
        print(f"📊 {self._t('statistics')}:")
        print(f"   {self._t('total_checked', count=len(proxies))}")
        print(f"   {self._t('working', count=working)}")
        print(f"   {self._t('not_working', count=len(proxies) - working)}")
        
        if len(proxies) > 0:
            print(f"   {self._t('success_rate', rate=working/len(proxies)*100)}")
        
        if working > 0:
            print(f"\n{self._t('working_by_type')}")
            for proxy_type in ['socks5', 'socks4', 'https', 'http']:
                count = len(self.working_by_type.get(proxy_type, []))
                if count > 0:
                    print(f"   {self._t(proxy_type, count=count)}")
        
        print("-" * 60)
        
        if self.working_proxies:
            self.save_working_proxies()
            
            print(f"\n{self._t('examples_title')}")
            for proxy in self.working_proxies[:5]:
                print(f"   {proxy}")
            if len(self.working_proxies) > 5:
                print(self._t('examples_more', count=len(self.working_proxies) - 5))
        else:
            print(f"\n{self._t('no_working_found')}")
        
        print(f"\n{self._t('testing_complete')}")

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description='Proxy tester with multi-language support')
    parser.add_argument('-i', '--input', help='Input file with proxies')
    parser.add_argument('-o', '--output', help='Output file for working proxies')
    parser.add_argument('-t', '--timeout', type=int, help='Timeout in seconds')
    parser.add_argument('-c', '--concurrent', type=int, help='Max concurrent checks')
    parser.add_argument('-l', '--lang', choices=['en', 'ru'], help='Language (en/ru)')
    
    args = parser.parse_args()
    
    # Определяем язык
    lang = args.lang
    if not lang and config.get('auto_detect_language', True):
        lang = config.detect_language()
    elif not lang:
        lang = config.get('language', 'en')
    
    tester = ProxyTester(
        input_file=args.input,
        output_file=args.output,
        timeout=args.timeout,
        max_concurrent=args.concurrent,
        lang=lang
    )
    
    asyncio.run(tester.run())

if __name__ == "__main__":
    main()