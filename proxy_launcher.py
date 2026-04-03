import os
import sys
import subprocess
import platform
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from locales import i18n
from config.settings import config

class ProxyLauncher:
    def __init__(self):
        self.scripts = {
            '1': {
                'name_key': 'standard',
                'desc_key': 'standard_desc',
                'script': 'proxy_tester.py',
                'default_output': config.get_default_output_file('standard'),
                'mode': 'standard'
            },
            '2': {
                'name_key': 'telegram',
                'desc_key': 'telegram_desc',
                'script': 'proxy_tester_telegram.py',
                'default_output': config.get_default_output_file('telegram'),
                'mode': 'telegram'
            }
        }
        self.current_lang = config.get('language', 'en')
        i18n.set_language(self.current_lang)
    
    def _t(self, key, **kwargs):
        return i18n.get(key, **kwargs)
    
    def clear_screen(self):
        os.system('cls' if platform.system() == 'Windows' else 'clear')
    
    def select_language(self):
        print("\n" + "=" * 60)
        print(self._t('language.title'))
        print("  1. English")
        print("  2. Русский")
        print("=" * 60)
        
        try:
            choice = input(self._t('language.choice')).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            return 'en'
        
        if choice == '2':
            self.current_lang = 'ru'
        else:
            self.current_lang = 'en'
        
        i18n.set_language(self.current_lang)
        config.set('language', self.current_lang)
        return self.current_lang
    
    def print_header(self):
        print("=" * 60)
        print(f"🚀 {self._t('app_title')} v2.0")
        print(f"   {self._t('app_description')}")
        print("=" * 60)
        print()
    
    def print_menu(self):
        print(f"{self._t('menu.title')}:")
        print("-" * 40)
        for key, script_info in self.scripts.items():
            name = self._t(f'menu.{script_info["name_key"]}')
            desc = self._t(f'menu.{script_info["desc_key"]}')
            print(f"  {key}. {name}")
            print(f"     📝 {desc}")
            print(f"     📁 {script_info['script']}")
            print(f"     💾 {script_info['default_output']}")
            print()
        print("  0. " + self._t('menu.exit'))
        print("  r. " + self._t('menu.reset'))
        print("-" * 40)
    
    def reset_configuration(self):
        print("\n" + "=" * 60)
        print("⚠️ " + self._t('reset.title'))
        print("=" * 60)
        print(self._t('reset.warning'))
        print()
        
        try:
            confirm = input(self._t('reset.confirm')).lower()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            return
        
        if confirm == 'y':
            config.reset_config()
            
            self.current_lang = config.get('language', 'en')
            i18n.set_language(self.current_lang)
            
            self.scripts['1']['default_output'] = config.get_default_output_file('standard')
            self.scripts['2']['default_output'] = config.get_default_output_file('telegram')
            
            print("\n✅ " + self._t('reset.success'))
            print(self._t('reset.restart'))
            input("\n" + self._t('press_enter'))
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            print("\n❌ " + self._t('reset.cancelled'))
            input("\n" + self._t('press_enter'))
    
    def check_file_exists(self, filename, create_template=False):
        if not filename or filename == 'None':
            filename = "proxies.txt"
            
        if not os.path.exists(filename):
            print(f"\n⚠️ {self._t('file_not_found', file=filename)}")
            if create_template:
                try:
                    choice = input(self._t('create_template_question')).lower()
                except (EOFError, KeyboardInterrupt):
                    print("\n")
                    return False
                    
                if choice == 'y':
                    self.create_template_file(filename)
                    return True
            return False
        return True
    
    def create_template_file(self, filename):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("# " + self._t('template.header') + "\n")
                f.write("# " + self._t('template.format') + "\n")
                f.write("#\n")
                f.write("# " + self._t('template.examples') + ":\n")
                f.write("# 192.168.1.1:8080\n")
                f.write("# http://192.168.1.1:8080\n")
                f.write("# socks5://192.168.1.1:1080\n")
                f.write("# socks5://username:password@192.168.1.1:1080\n")
                f.write("#\n")
                f.write("# " + self._t('template.working_examples') + ":\n")
                f.write("http://94.43.164.242:8080\n")
                f.write("http://92.51.122.174:8080\n")
                f.write("http://176.32.2.193:8080\n")
            print(f"✅ {self._t('template.created', file=filename)}")
            print(f"📝 {self._t('template.add_proxies')}")
            return True
        except Exception as e:
            print(f"❌ {self._t('template.error', error=e)}")
            return False
    
    def get_input_file(self, mode='standard'):
        print(f"\n{self._t('input_file.title')}:")
        print("-" * 40)
    
        default_file = config.get_default_input_file(mode)
    
        if not default_file or default_file == 'None':
            default_file = "proxies.txt"
    
        print(self._t('input_file.default_question') + f"'{default_file}'? (y/n): ", end="")
        try:
            choice = input().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            return default_file
    
        if choice == 'y':
            filename = default_file
        else:
            try:
                filename = input(self._t('input_file.enter_filename')).strip()
            except (EOFError, KeyboardInterrupt):
                print("\n")
                filename = default_file
    
        if not filename or filename == 'None':
            filename = default_file
            print(self._t('input_file.using_default', file=filename))
    
        config.update_proxy_files(filename, None, mode)
    
        return filename
    
    def get_additional_args(self, script_name, mode):
        args = []
        
        if script_name == 'proxy_tester_telegram.py':
            print(f"\n{self._t('telegram_setup.title')}:")
            print("-" * 40)
            
            try:
                choice = input(self._t('telegram_setup.bot_token_question')).lower()
            except (EOFError, KeyboardInterrupt):
                print("\n")
                return args
            
            if choice == 'y':
                try:
                    bot_token = input(self._t('telegram_setup.enter_token')).strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n")
                    return args
                    
                if bot_token:
                    args.extend(['-b', bot_token])
                    print(self._t('telegram_setup.token_added'))
        
        return args
    
    def get_advanced_settings(self):
        print(f"\n{self._t('advanced_settings.title')}:")
        print("-" * 40)
        print(self._t('advanced_settings.press_enter'))
    
        default_timeout = config.get('timeout', 10)
        print(self._t('advanced_settings.timeout') + f"[{default_timeout}]: ", end="")
        try:
            timeout_input = input().strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            timeout_input = ""
        timeout = timeout_input if timeout_input else str(default_timeout)
    
        default_concurrent = config.get('max_concurrent', 50)
        print(self._t('advanced_settings.concurrent') + f"[{default_concurrent}]: ", end="")
        try:
            concurrent_input = input().strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            concurrent_input = ""
        concurrent = concurrent_input if concurrent_input else str(default_concurrent)
    
        return timeout, concurrent
    
    def run_script(self, script_name, input_file, timeout, concurrent, additional_args, mode):
        if not os.path.exists(script_name):
            print(f"\n{self._t('errors.script_not_found', script=script_name)}")
            print(self._t('errors.check_folder'))
            return False
        
        cmd = [
            sys.executable,
            script_name,
            '-i', input_file,
            '-t', timeout,
            '-c', concurrent,
            '-l', self.current_lang
        ]
        
        output_file = config.get_default_output_file(mode)
        if output_file and output_file != 'None':
            cmd.extend(['-o', output_file])
        
        cmd.extend(additional_args)
        
        print("\n" + "=" * 60)
        print(f"🚀 RUNNING {script_name}")
        print("=" * 60)
        print(f"{self._t('confirmation.input_file', file=input_file)}")
        print(f"{self._t('confirmation.timeout', timeout=timeout)}")
        print(f"{self._t('confirmation.concurrent', concurrent=concurrent)}")
        if additional_args:
            print(f"🔧 Extra params: {' '.join(additional_args)}")
        print("=" * 60)
        print()
        
        try:
            process = subprocess.run(cmd, capture_output=False, text=True)
            
            if process.returncode == 0:
                print(f"\n{self._t('confirmation.success')}")
                return True
            else:
                print(f"\n{self._t('confirmation.error')}")
                return False
                
        except KeyboardInterrupt:
            print(f"\n\n{self._t('confirmation.interrupted')}")
            return False
        except Exception as e:
            print(f"\n{self._t('errors.critical', error=e)}")
            return False
    
    def show_results(self, script_info):
        output_file = script_info['default_output']
        
        if not output_file or output_file == 'None':
            output_file = "working_proxies.txt" if script_info['mode'] == 'standard' else "telegram_proxies.txt"
        
        if os.path.exists(output_file):
            print("\n" + "=" * 60)
            print(f"📊 {self._t('results.title')}")
            print("=" * 60)
            
            with open(output_file, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                working_count = len(lines)
            
            print(self._t('results.working_count', count=working_count))
            print(self._t('results.saved_to', file=output_file))
            
            if working_count > 0:
                print(f"\n{self._t('examples_title')}")
                for proxy in lines[:5]:
                    print(f"   {proxy}")
                if working_count > 5:
                    print(self._t('examples_more', count=working_count - 5))
            
            try:
                choice = input(f"\n{self._t('results.open_file')}").lower()
            except (EOFError, KeyboardInterrupt):
                print("\n")
                return
                
            if choice == 'y':
                if platform.system() == 'Windows':
                    os.startfile(output_file)
                elif platform.system() == 'Darwin':
                    subprocess.run(['open', output_file])
                else:
                    subprocess.run(['xdg-open', output_file])
        else:
            print(f"\n{self._t('results.file_not_found')}")
    
    def run(self):
        self.select_language()
        
        while True:
            self.clear_screen()
            self.print_header()
            self.print_menu()
            
            try:
                choice = input("🔍 " + self._t('menu.prompt')).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n")
                break
            
            if choice == '0':
                print(f"\n👋 {self._t('menu.exit')}!")
                break
            
            if choice == 'r':
                self.reset_configuration()
                continue
            
            if choice not in self.scripts:
                print(f"\n{self._t('errors.invalid_choice')}")
                input("\n" + self._t('press_enter'))
                continue
            
            script_info = self.scripts[choice]
            
            input_file = self.get_input_file(script_info['mode'])
            
            if not self.check_file_exists(input_file, create_template=True):
                print(f"\n{self._t('errors.cannot_continue')}")
                input("\n" + self._t('press_enter'))
                continue
            
            additional_args = self.get_additional_args(script_info['script'], script_info['mode'])
            
            timeout, concurrent = self.get_advanced_settings()
            
            mode_name = self._t(f'menu.{script_info["name_key"]}')
            
            print("\n" + "=" * 60)
            print(f"📋 {self._t('confirmation.title')}:")
            print(f"   {self._t('confirmation.mode', mode=mode_name)}")
            print(f"   {self._t('confirmation.input_file', file=input_file)}")
            print(f"   {self._t('confirmation.timeout', timeout=timeout)}")
            print(f"   {self._t('confirmation.concurrent', concurrent=concurrent)}")
            print("=" * 60)
            
            try:
                confirm = input(f"\n{self._t('confirmation.run_question')}").lower()
            except (EOFError, KeyboardInterrupt):
                print("\n")
                continue
                
            if confirm != 'y':
                print(self._t('confirmation.cancelled'))
                input("\n" + self._t('press_enter'))
                continue
            
            success = self.run_script(
                script_info['script'],
                input_file,
                timeout,
                concurrent,
                additional_args,
                script_info['mode']
            )
            
            if success:
                self.show_results(script_info)
            
            input("\n\n" + self._t('press_enter'))

def main():
    launcher = ProxyLauncher()
    
    try:
        launcher.run()
    except KeyboardInterrupt:
        print("\n\n👋 Program interrupted by user")
    except EOFError:
        print("\n\n👋 Program terminated")
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
