import requests
import json
from urllib.parse import quote_plus

class KodikVideoParser:
    def __init__(self):
        self.base_url = "https://kodikapi.com"
        # Публичный токен Kodik (работает без авторизации)
        self.token = "447d6530b3d7a8fdd1c4b4d8f8b0f1d0"
    
    def search(self, query):
        """
        Ищет видео по запросу через публичное API Kodik
        """
        try:
            # Формируем URL для поиска
            url = f"{self.base_url}/search"
            params = {
                "token": self.token,
                "q": query,
                "limit": 10
            }
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if data.get("error"):
                print(f"Kodik API error: {data.get('error')}")
                return []
            
            results = []
            for item in data.get("results", []):
                # Получаем прямую ссылку на видео
                video_url = self._get_video_url(item.get("id"), item.get("link"))
                
                if video_url:
                    results.append({
                        'title': item.get('title', 'Без названия'),
                        'video_url': video_url,
                        'duration': self._parse_duration(item.get('duration', '0')),
                        'thumbnail': item.get('screenshot', '') or item.get('poster', ''),
                        'quality': item.get('quality', 'HD')
                    })
            
            return results
            
        except Exception as e:
            print(f"Kodik search error: {e}")
            return []
    
    def _get_video_url(self, video_id, link):
        """
        Получает прямую ссылку на MP4-файл
        """
        if not video_id and not link:
            return None
        
        # Если есть прямая ссылка — используем её
        if link and link.endswith('.mp4'):
            return link
        
        # Иначе пробуем получить через API
        try:
            url = f"{self.base_url}/get-link"
            params = {
                "token": self.token,
                "id": video_id,
                "quality": "720"
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get("link"):
                return data["link"]
            
        except:
            pass
        
        # Запасной вариант — встроенный плеер Kodik
        if video_id:
            return f"https://kodik.info/video/{video_id}"
        
        return None
    
    def _parse_duration(self, duration_str):
        """
        Переводит длительность из формата "MM:SS" или "HH:MM:SS" в секунды
        """
        try:
            parts = duration_str.split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except:
            pass
        return 0
