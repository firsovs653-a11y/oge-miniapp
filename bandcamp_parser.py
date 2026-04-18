import requests
from bs4 import BeautifulSoup
import re
import time

class BandcampParser:
    def __init__(self):
        self.base_url = "https://bandcamp.com"
        self.session = requests.Session()
        
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        })
        
        self._init_session()

    def _init_session(self):
        """Получает куки, посетив главную страницу"""
        try:
            self.session.get(self.base_url, timeout=10)
            time.sleep(0.5)
        except:
            pass

    def search(self, query, limit=10):
        """Ищет треки на Bandcamp"""
        print(f"🔍 Поиск Bandcamp: '{query}'")
        
        try:
            api_results = self._search_api(query, limit)
            if api_results:
                return api_results
            
            return self._search_html(query, limit)
            
        except Exception as e:
            print(f"❌ Ошибка поиска: {e}")
            return self._fallback_tracks()

    def _search_api(self, query, limit):
        """Поиск через внутреннее API Bandcamp"""
        try:
            api_url = "https://bandcamp.com/api/fansignup/v1/search"
            params = {"q": query, "type": "track"}
            
            resp = self.session.get(api_url, params=params, timeout=10)
            data = resp.json()
            
            results = []
            for item in data.get('auto', {}).get('results', [])[:limit]:
                if item.get('type') == 't':
                    track_url = item.get('url')
                    if track_url:
                        # Исправляем URL если нужно
                        if not track_url.startswith('http'):
                            track_url = self.base_url + track_url
                        audio_url = self._get_audio_url(track_url)
                        if audio_url:
                            results.append({
                                'title': item.get('name', 'Без названия'),
                                'artist': item.get('band_name', 'Неизвестен'),
                                'audio_url': audio_url,
                                'duration': 0,
                                'thumbnail': item.get('img', '')
                            })
            
            if results:
                print(f"✅ API нашёл треков: {len(results)}")
                return results
                
        except Exception as e:
            print(f"API поиск не сработал: {e}")
        
        return None

    def _search_html(self, query, limit):
        """Поиск через HTML парсинг"""
        try:
            search_url = f"{self.base_url}/search"
            params = {"q": query, "item_type": "t"}
            
            resp = self.session.get(search_url, params=params, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            results = []
            
            for item in soup.find_all('li', class_='searchresult')[:limit]:
                link = item.find('a')
                if not link:
                    continue
                
                href = link.get('href')
                
                # Исправляем URL
                if href.startswith('http'):
                    track_url = href
                else:
                    track_url = self.base_url + href
                
                title = link.text.strip()
                
                artist_elem = item.find('div', class_='subhead')
                artist = artist_elem.text.strip() if artist_elem else 'Неизвестен'
                
                img = item.find('img')
                thumbnail = img.get('src') if img else ''
                
                audio_url = self._get_audio_url(track_url)
                if audio_url:
                    results.append({
                        'title': title[:100],
                        'artist': artist[:50],
                        'audio_url': audio_url,
                        'duration': 0,
                        'thumbnail': thumbnail
                    })
            
            print(f"✅ HTML нашёл треков: {len(results)}")
            
            if not results:
                return self._fallback_tracks()
            
            return results
            
        except Exception as e:
            print(f"HTML поиск не сработал: {e}")
            return self._fallback_tracks()

    def _get_audio_url(self, track_url):
        """Извлекает прямую MP3-ссылку"""
        try:
            resp = self.session.get(track_url, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Способ 1: meta-тег
            meta_tag = soup.find('meta', property='og:audio')
            if meta_tag and meta_tag.get('content'):
                return meta_tag.get('content')
            
            # Способ 2: data-trackinfo
            play_button = soup.find('a', {'data-trackinfo': True})
            if play_button:
                trackinfo = play_button.get('data-trackinfo', '')
                match = re.search(r'"mp3-128":"([^"]+)"', trackinfo)
                if match:
                    return match.group(1).replace('\\u002F', '/')
            
            # Способ 3: JavaScript
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
            }
        ]
