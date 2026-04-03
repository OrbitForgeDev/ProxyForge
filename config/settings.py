import os
import json
import platform
from pathlib import Path
from typing import Dict, Any, Optional
import locale

class Config:
    
    _instance = None
    _config: Dict[str, Any] = {}
    _config_file = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _get_config_path(self) -> Path:
        if platform.system() == 'Windows':
            config_dir = Path(os.environ.get('APPDATA', Path.home() / 'AppData/Roaming'))
        else:
            config_dir = Path.home() / '.config'
        
        config_dir = config_dir / 'proxy-tester'
        config_dir.mkdir(parents=True, exist_ok=True)
        
        self._config_file = config_dir / 'config.json'
        return self._config_file
    
    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'language': 'en',
            'timeout': 10,
            'max_concurrent': 50,
            'input_file': 'proxies.txt',
            'output_file': 'working_proxies.txt',
            'telegram_output_file': 'telegram_proxies.txt',
            'telegram_input_file': 'proxies.txt',
            'test_urls': [
                'http://httpbin.org/ip',
                'https://api.ipify.org?format=json',
                'http://ifconfig.me/ip'
            ],
            'telegram_urls': [
                'https://api.telegram.org',
                'https://web.telegram.org',
                'https://t.me'
            ],
            'telegram_endpoints': [
                "https://api.telegram.org/bot",
                "https://api.telegram.org/bot/getMe",
                "https://api.telegram.org/bot/getUpdates",
            ],
            'socks_ports': [1080, 1081, 9050, 9150, 5805],
            'auto_detect_language': True
        }
    
    def _load_config(self) -> None:
        config_file = self._get_config_path()
        default_config = self._get_default_config()
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self._config = {**default_config, **loaded_config}
                    
                    if 'telegram_input_file' not in self._config or not self._config.get('telegram_input_file'):
                        self._config['telegram_input_file'] = 'proxies.txt'
                    if not self._config.get('input_file'):
                        self._config['input_file'] = 'proxies.txt'
                    if not self._config.get('telegram_output_file'):
                        self._config['telegram_output_file'] = 'telegram_proxies.txt'
                    if not self._config.get('output_file'):
                        self._config['output_file'] = 'working_proxies.txt'
                        
                print(f"✅ Loaded config from {config_file}")
            except Exception as e:
                print(f"⚠️ Error loading config: {e}")
                self._config = default_config
                self._save_config()
        else:
            self._config = default_config
            self._save_config()
            print(f"✅ Created default config at {config_file}")
    
    def _save_config(self) -> None:
        if not self._config_file:
            self._get_config_path()
        
        try:
            config_to_save = {
                'language': self._config.get('language'),
                'timeout': self._config.get('timeout'),
                'max_concurrent': self._config.get('max_concurrent'),
                'input_file': self._config.get('input_file'),
                'output_file': self._config.get('output_file'),
                'telegram_output_file': self._config.get('telegram_output_file'),
                'telegram_input_file': self._config.get('telegram_input_file'),
                'auto_detect_language': self._config.get('auto_detect_language')
            }
            
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any, save: bool = True) -> None:
        self._config[key] = value
        if save:
            self._save_config()
    
    def detect_language(self) -> str:
        if not self.get('auto_detect_language'):
            return self.get('language', 'en')
        
        try:
            system_lang = locale.getdefaultlocale()[0]
            if system_lang and system_lang.startswith('ru'):
                return 'ru'
        except:
            pass
        
        return 'en'
    
    def get_default_input_file(self, mode: str = 'standard') -> str:
        if mode == 'telegram':
            filename = self.get('telegram_input_file', self.get('input_file', 'proxies.txt'))
        else:
            filename = self.get('input_file', 'proxies.txt')
        
        if not filename or filename == 'None':
            filename = 'proxies.txt'
            if mode == 'telegram':
                self.set('telegram_input_file', filename, save=False)
            else:
                self.set('input_file', filename, save=False)
            self._save_config()
        
        return filename
    
    def get_default_output_file(self, mode: str = 'standard') -> str:
        if mode == 'telegram':
            filename = self.get('telegram_output_file', 'telegram_proxies.txt')
        else:
            filename = self.get('output_file', 'working_proxies.txt')
        
        if not filename or filename == 'None':
            filename = 'telegram_proxies.txt' if mode == 'telegram' else 'working_proxies.txt'
            if mode == 'telegram':
                self.set('telegram_output_file', filename, save=False)
            else:
                self.set('output_file', filename, save=False)
            self._save_config()
        
        return filename
    
    def update_proxy_files(self, input_file: str, output_file: Optional[str] = None, mode: str = 'standard') -> None:
        if not input_file or input_file == 'None':
            input_file = 'proxies.txt'
        
        if mode == 'telegram':
            self.set('telegram_input_file', input_file, save=False)
            if output_file:
                self.set('telegram_output_file', output_file, save=False)
        else:
            self.set('input_file', input_file, save=False)
            if output_file:
                self.set('output_file', output_file, save=False)
        self._save_config()
    
    def reset_config(self) -> None:
        default_config = self._get_default_config()
        self._config = default_config.copy()
        self._save_config()
        from locales import i18n
        i18n.set_language(self._config.get('language', 'en'))
        print("✅ Configuration reset to defaults")

config = Config()
