import requests
from bs4 import BeautifulSoup
import re

class BandcampParser:
    def __init__(self):
        self.base_url = "https://bandcamp.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def search(self, query, limit=10):
        """Ищет треки на Bandcamp через HTML парсинг"""
        print(f"🔍 Поиск Bandcamp: '{query}'")
        
        try:
            # Используем публичную страницу поиска
            search_url = f"{self.base_url}/search"
            params = {"q": query, "item_type": "t"}
            
            resp = requests.get(search_url, params=params, headers=self.headers, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            results = []
            
            # Ищем треки в результатах поиска
            for item in soup.find_all('li', class_='searchresult')[:limit]:
                # Заголовок и ссылка
                title_elem = item.find('div', class_='heading')
                if not title_elem:
                    continue
                
                link = title_elem.find('a')
                if not link:
                    continue
                
                title = link.text.strip()
                track_url = self.base_url + link.get('href')
                
                # Исполнитель
                artist_elem = item.find('div', class_='subhead')
                artist = artist_elem.text.strip() if artist_elem else 'Неизвестен'
                
                # Обложка
                img = item.find('img')
                thumbnail = img.get('src') if img else ''
                
                # Получаем прямую ссылку на аудио
                audio_url = self._get_audio_url(track_url)
                
                if audio_url:
                    results.append({
                        'title': title[:100],
                        'artist': artist[:50],
                        'audio_url': audio_url,
                        'duration': 0,
                        'thumbnail': thumbnail
                    })
            
            print(f"✅ Найдено треков: {len(results)}")
            
            if not results:
                return self._fallback_tracks()
            
            return results
            
        except Exception as e:
            print(f"❌ Ошибка поиска: {e}")
            return self._fallback_tracks()

    def _get_audio_url(self, track_url):
        """Извлекает прямую MP3-ссылку со страницы трека"""
        try:
            resp = requests.get(track_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Способ 1: meta-тег og:audio
            meta_tag = soup.find('meta', property='og:audio')
            if meta_tag and meta_tag.get('content'):
                return meta_tag.get('content')
            
            # Способ 2: ищем в data-атрибутах
            play_button = soup.find('a', {'data-trackinfo': True})
            if play_button:
                trackinfo = play_button.get('data-trackinfo', '')
                match = re.search(r'"mp3-128":"([^"]+)"', trackinfo)
                if match:
                    return match.group(1).replace('\\u002F', '/')
            
            # Способ 3: ищем в JavaScript
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    match = re.search(r'"mp3-128":"([^"]+)"', script.string)
                    if match:
                        return match.group(1).replace('\\u002F', '/')
            
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
            },
            {
                'title': '🎧 Chill Synthwave (Тестовый)',
                'artist': 'Bandcamp',
                'audio_url': 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3',
                'duration': 292,
                'thumbnail': ''
            }
        ]
