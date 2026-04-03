# locales/__init__.py
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

class I18n:
    """Класс для интернационализации приложения"""
    
    _instance = None
    _translations: Dict[str, Dict[str, str]] = {}
    _current_lang: str = 'en'
    _verbose: bool = False  # Добавляем флаг для вывода сообщений
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_translations()
        return cls._instance
    
    def set_verbose(self, verbose: bool) -> None:
        """Включает/выключает вывод сообщений о загрузке"""
        self._verbose = verbose
    
    def _load_translations(self) -> None:
        """Загружает все файлы переводов из папки locales"""
        locales_dir = Path(__file__).parent
        
        for lang_file in locales_dir.glob('*.json'):
            lang_code = lang_file.stem
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self._translations[lang_code] = json.load(f)
                if self._verbose:
                    print(f"✅ Loaded language: {lang_code}")
            except Exception as e:
                if self._verbose:
                    print(f"❌ Error loading {lang_file}: {e}")
        
        # Если не загружено ни одного перевода, создаем пустой
        if not self._translations:
            self._translations['en'] = {}
            if self._verbose:
                print("⚠️ No translations found, using empty defaults")
    
    def set_language(self, lang_code: str) -> bool:
        """Устанавливает текущий язык"""
        if lang_code in self._translations:
            self._current_lang = lang_code
            return True
        return False
    
    def get(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """
        Получает перевод по ключу с подстановкой параметров
        
        Args:
            key: Ключ перевода (можно использовать точечную нотацию, например 'menu.title')
            default: Значение по умолчанию, если ключ не найден
            **kwargs: Параметры для форматирования строки
        
        Returns:
            Переведенная строка
        """
        translation = self._translations.get(self._current_lang, {})
        
        # Поддержка точечной нотации (например, 'menu.title')
        keys = key.split('.')
        value = translation
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = None
                break
        
        if value is None:
            value = default or key
        
        # Подставляем параметры
        if kwargs and isinstance(value, str):
            try:
                value = value.format(**kwargs)
            except (KeyError, ValueError):
                # Если параметр не найден, оставляем как есть
                pass
        
        return value
    
    def get_available_languages(self) -> list:
        """Возвращает список доступных языков"""
        return list(self._translations.keys())
    
    def get_current_language(self) -> str:
        """Возвращает текущий язык"""
        return self._current_lang

# Создаем глобальный экземпляр
i18n = I18n()