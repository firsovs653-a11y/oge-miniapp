import requests
import re
import json

class AnimeGoParser:
    def __init__(self):
        self.base_url = "https://animego.org"
        self.api_url = "https://animego.org/api/v2"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
    
    def search(self, query):
        """
        Ищет аниме через API AnimeGo
        """
        try:
            # Используем официальный поиск AnimeGo
            search_url = f"{self.api_url}/search"
            params = {
                "q": query,
                "limit": 10
            }
            
            response = requests.get(search_url, params=params, headers=self.headers, timeout=15)
            data = response.json()
            
            results = []
            items = data.get('data', [])
            
            for item in items:
                title = item.get('title_ru') or item.get('title_en', 'Без названия')
                anime_id = item.get('id')
                poster = item.get('poster', '')
                
                if anime_id:
                    # Получаем список серий
                    episodes = self._get_episodes(anime_id)
                    if episodes:
                        first_ep = episodes[0]
                        video_url = self._get_video_url(anime_id, first_ep.get('id'))
                        
                        if video_url:
                            results.append({
                                'title': f"{title} (Серия {first_ep.get('number', '1')})",
                                'video_url': video_url,
                                'duration': first_ep.get('duration', 0),
                                'thumbnail': poster
                            })
            
            return results
            
        except Exception as e:
            print(f"AnimeGo search error: {e}")
            return self._fallback_search(query)
    
    def _get_episodes(self, anime_id):
        """Получает список серий"""
        try:
            url = f"{self.api_url}/anime/{anime_id}/episodes"
            response = requests.get(url, headers=self.headers, timeout=10)
            data = response.json()
            return data.get('data', [])
        except:
            return []
    
    def _get_video_url(self, anime_id, episode_id):
        """Получает прямую ссылку на видео"""
        try:
            # Пробуем получить через API плеера
            player_url = f"{self.base_url}/player/episode/{episode_id}"
            response = requests.get(player_url, headers=self.headers, timeout=10)
            
            # Ищем прямую ссылку в ответе
            match = re.search(r'file:"([^"]+\.m3u8)"', response.text)
            if match:
                return match.group(1)
            
            match = re.search(r'file:"([^"]+\.mp4)"', response.text)
            if match:
                return match.group(1)
            
        except Exception as e:
            print(f"Error getting video URL: {e}")
        
        return None
    
    def _fallback_search(self, query):
        """
        Запасной вариант — парсинг HTML (если API недоступно)
        """
        try:
            search_url = f"{self.base_url}/search/all?q={query}"
            response = requests.get(search_url, headers=self.headers, timeout=15)
            
            # Ищем JSON с данными в HTML
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', response.text)
            if match:
                data = json.loads(match.group(1))
                anime_list = data.get('props', {}).get('pageProps', {}).get('animeList', [])
                
                results = []
                for anime in anime_list[:5]:
                    results.append({
                        'title': anime.get('title_ru', 'Без названия'),
                        'video_url': f"{self.base_url}/anime/{anime.get('id')}",
                        'duration': 0,
                        'thumbnail': anime.get('poster', '')
                    })
                return results
        except:
            pass
        
        return []
