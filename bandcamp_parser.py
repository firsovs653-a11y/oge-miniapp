import requests
from bs4 import BeautifulSoup

class BandcampParser:
    def __init__(self):
        self.search_url = "https://bandcamp.com/api/fansignup/v1/search"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def search(self, query, limit=10):
        """Ищет треки на Bandcamp"""
        print(f"🔍 Поиск Bandcamp: '{query}'")
        
        try:
            params = {"q": query, "type": "track"}
            resp = requests.get(self.search_url, params=params, headers=self.headers, timeout=10)
            data = resp.json()
            
            results = []
            for item in data.get('auto', {}).get('results', [])[:limit]:
                if item.get('type') == 't':
                    track_url = item.get('url')
                    if track_url:
                        audio_url = self._get_audio_url(track_url)
                        if audio_url:
                            results.append({
                                'title': item.get('name', 'Без названия'),
                                'artist': item.get('band_name', 'Неизвестен'),
                                'audio_url': audio_url,
                                'duration': 0,
                                'thumbnail': item.get('img', '')
                            })
            
            print(f"✅ Найдено треков: {len(results)}")
            return results if results else self._fallback_tracks()
            
        except Exception as e:
            print(f"❌ Ошибка поиска: {e}")
            return self._fallback_tracks()

    def _get_audio_url(self, track_url):
        """Извлекает прямую MP3-ссылку со страницы трека"""
        try:
            resp = requests.get(track_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            meta_tag = soup.find('meta', property='og:audio')
            if meta_tag:
                return meta_tag.get('content')
        except Exception as e:
            print(f"Ошибка получения аудио: {e}")
        return None

    def _fallback_tracks(self):
        return [
            {
                'title': '🎵 Lofi Hip Hop (Тестовый)',
                'artist': 'Bandcamp',
                'audio_url': 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3',
                'duration': 368,
                'thumbnail': ''
            }
        ]
