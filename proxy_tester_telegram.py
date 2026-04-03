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

sys.path.insert(0, str(Path(__file__).parent))

from locales import i18n
from config.settings import config

class TelegramProxyTester:
    def __init__(self, input_file=None, output_file=None, timeout=None, 
                 max_concurrent=None, bot_token=None, lang=None):
        self.input_file = input_file or config.get_default_input_file('telegram')
        self.output_file = output_file or config.get_default_output_file('telegram')
        self.timeout = timeout or config.get('timeout', 10)
        self.max_concurrent = max_concurrent or config.get('max_concurrent', 50)
        
        self.lang = lang or config.get('language', 'en')
        i18n.set_language(self.lang)
        
        self.working_proxies = []
        self.working_by_type = defaultdict(list)
        self.bot_token = bot_token
        
        self.telegram_endpoints = config.get('telegram_endpoints', [
            "https://api.telegram.org/bot",
            "https://api.telegram.org/bot/getMe",
            "https://api.telegram.org/bot/getUpdates",
        ])
        
        self.telegram_urls = config.get('telegram_urls', [
            "https://api.telegram.org",
            "https://web.telegram.org",
            "https://t.me",
        ])
        
    def _t(self, key, **kwargs):
        return i18n.get(key, **kwargs)
    
    def read_proxies(self):
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
        proxy_str = proxy_str.strip()
        
        if proxy_str.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
            return proxy_str
        
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
        if proxy_url.startswith('socks5://'):
            return 'socks5'
        elif proxy_url.startswith('socks4://'):
            return 'socks4'
        elif proxy_url.startswith('https://'):
            return 'https'
        elif proxy_url.startswith('http://'):
            return 'http'
        return 'http'
    
    async def test_telegram_connection(self, proxy_url, session):
        proxy_type = self.get_proxy_type(proxy_url)
        
        for telegram_url in self.telegram_urls:
            try:
                async with session.get(
                    telegram_url,
                    proxy=proxy_url if proxy_type in ['http', 'https'] else None,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status in [200, 301, 302, 403]:
                        return True, "telegram_api"
            except:
                continue
        
        return False, None
    
    async def test_bot_api(self, proxy_url, session):
        proxy_type = self.get_proxy_type(proxy_url)
        
        if self.bot_token:
            bot_url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            try:
                async with session.get(
                    bot_url,
                    proxy=proxy_url if proxy_type in ['http', 'https'] else None,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            return True, f"bot_{data['result']['username']}"
            except:
                pass
            return False, None
        
        for endpoint in self.telegram_endpoints[:1]:
            try:
                async with session.get(
                    endpoint,
                    proxy=proxy_url if proxy_type in ['http', 'https'] else None,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status in [200, 401, 404]:
                        return True, "api_available"
            except:
                continue
        
        return False, None
    
    async def test_single_proxy(self, proxy_url):
        proxy_type = self.get_proxy_type(proxy_url)
        
        try:
            if proxy_type in ['socks4', 'socks5']:
                connector = ProxyConnector.from_url(proxy_url)
            else:
                connector = aiohttp.TCPConnector()
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                telegram_ok, telegram_type = await self.test_telegram_connection(proxy_url, session)
                
                if not telegram_ok:
                    return False, proxy_url, self._t('telegram_connection_failed')
                
                bot_ok, bot_info = await self.test_bot_api(proxy_url, session)
                
                if bot_ok:
                    if self.bot_token:
                        return True, proxy_url, self._t('telegram_bot_working', 
                                                       type=proxy_type.upper(), 
                                                       info=bot_info)
                    else:
                        return True, proxy_url, self._t('telegram_api_available', 
                                                       type=proxy_type.upper())
                else:
                    return False, proxy_url, self._t('telegram_api_not_responding', 
                                                    type=proxy_type.upper())
                
        except aiohttp_socks.ProxyConnectionError as e:
            return False, proxy_url, self._t('proxy_connection_error', error=str(e))
        except asyncio.TimeoutError:
            return False, proxy_url, self._t('timeout_error', timeout=self.timeout)
        except aiohttp.ClientError as e:
            return False, proxy_url, self._t('client_error', error=str(e))
        except Exception as e:
            return False, proxy_url, self._t('unknown_error', error=str(e))
    
    async def test_proxies_batch(self, proxies, detailed=False):
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def test_with_semaphore(proxy):
            async with semaphore:
                if detailed:
                    return await self.test_single_proxy_detailed(proxy)
                else:
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
                
                if is_working:
                    pbar.write(f"  {message}")
        
        return results
    
    async def test_single_proxy_detailed(self, proxy_url):
        proxy_type = self.get_proxy_type(proxy_url)
        results = {}
        
        try:
            if proxy_type in ['socks4', 'socks5']:
                connector = ProxyConnector.from_url(proxy_url)
            else:
                connector = aiohttp.TCPConnector()
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                try:
                    async with session.get(
                        "https://api.telegram.org",
                        proxy=proxy_url if proxy_type in ['http', 'https'] else None,
                        timeout=5
                    ) as response:
                        results['telegram_api'] = response.status in [200, 301, 302, 403]
                except:
                    results['telegram_api'] = False
                
                if results['telegram_api']:
                    start_time = asyncio.get_event_loop().time()
                    try:
                        async with session.get(
                            "https://api.telegram.org",
                            proxy=proxy_url if proxy_type in ['http', 'https'] else None,
                            timeout=5
                        ) as response:
                            latency = (asyncio.get_event_loop().time() - start_time) * 1000
                            results['latency'] = f"{latency:.0f}ms"
                    except:
                        results['latency'] = "Unknown"
                
                if self.bot_token and results['telegram_api']:
                    bot_url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
                    try:
                        async with session.get(
                            bot_url,
                            proxy=proxy_url if proxy_type in ['http', 'https'] else None,
                            timeout=5
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                if data.get('ok'):
                                    results['bot'] = self._t('bot_working', username=data['result']['username'])
                                else:
                                    results['bot'] = self._t('bot_not_responding')
                            else:
                                results['bot'] = self._t('bot_error', status=response.status)
                    except:
                        results['bot'] = self._t('bot_check_failed')
                
                if results.get('telegram_api'):
                    msg = self._t('telegram_available_via', type=proxy_type.upper())
                    if 'latency' in results:
                        msg += f" ({self._t('latency', latency=results['latency'])})"
                    if 'bot' in results:
                        msg += f" - {results['bot']}"
                    return True, proxy_url, msg
                else:
                    return False, proxy_url, self._t('telegram_unavailable_via', type=proxy_type.upper())
                
        except Exception as e:
            return False, proxy_url, self._t('error_via', type=proxy_type.upper(), error=str(e)[:50])
    
    def save_working_proxies(self):
        if not self.working_proxies:
            print(self._t('no_working_proxies'))
            return
        
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(f"# {self._t('telegram_title')} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# {self._t('total_checked', count=len(self.working_proxies))}\n")
                f.write(f"# {self._t('sorting')}\n")
                f.write(f"# {self._t('telegram_note')}\n")
                f.write("#" + "=" * 58 + "\n\n")
                
                f.write(f"# {self._t('working_by_type')}\n")
                for proxy_type in ['socks5', 'socks4', 'https', 'http']:
                    count = len(self.working_by_type.get(proxy_type, []))
                    if count > 0:
                        f.write(f"#   {proxy_type.upper()}: {count}\n")
                f.write("\n")
                
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
        print("=" * 60)
        print(f"🚀 {self._t('telegram_title')}")
        print("=" * 60)
        
        proxies = self.read_proxies()
        if not proxies:
            print(self._t('no_proxies'))
            return
        
        print(self._t('telegram_checking', count=len(proxies)))
        print(self._t('timeout_setting', timeout=self.timeout))
        print(self._t('concurrent_setting', concurrent=self.max_concurrent))
        
        if self.bot_token:
            token_preview = self.bot_token[:10] + "..."
            print(self._t('telegram_with_token', token=token_preview))
        else:
            print(self._t('telegram_without_token'))
        print("-" * 60)
        
        await self.test_proxies_batch(proxies, detailed=bool(self.bot_token))
        
        working = len(self.working_proxies)
        
        print("\n" + "-" * 60)
        print(f"📊 {self._t('statistics')}:")
        print(f"   {self._t('total_checked', count=len(proxies))}")
        print(f"   {self._t('telegram_working', count=working)}")
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
            for proxy in self.working_proxies[:10]:
                print(f"   {proxy}")
            if len(self.working_proxies) > 10:
                print(self._t('examples_more', count=len(self.working_proxies) - 10))
            
            print(f"\n{self._t('telegram_usage_title')}")
            print(self._t('telegram_usage_1'))
            print(self._t('telegram_usage_2'))
            print(self._t('telegram_usage_3'))
        else:
            print(f"\n{self._t('no_working_found')}")
        
        print(f"\n{self._t('testing_complete')}")

def main():
    parser = argparse.ArgumentParser(description='Telegram proxy tester with multi-language support')
    parser.add_argument('-i', '--input', help='Input file with proxies')
    parser.add_argument('-o', '--output', help='Output file for working proxies')
    parser.add_argument('-t', '--timeout', type=int, help='Timeout in seconds')
    parser.add_argument('-c', '--concurrent', type=int, help='Max concurrent checks')
    parser.add_argument('-b', '--bot-token', help='Telegram bot token for detailed check')
    parser.add_argument('-l', '--lang', choices=['en', 'ru'], help='Language (en/ru)')
    
    args = parser.parse_args()
    
    lang = args.lang
    if not lang and config.get('auto_detect_language', True):
        lang = config.detect_language()
    elif not lang:
        lang = config.get('language', 'en')
    
    tester = TelegramProxyTester(
        input_file=args.input,
        output_file=args.output,
        timeout=args.timeout,
        max_concurrent=args.concurrent,
        bot_token=args.bot_token,
        lang=lang
    )
    
    asyncio.run(tester.run())

if __name__ == "__main__":
    main()
