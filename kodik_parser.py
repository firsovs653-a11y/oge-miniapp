import requests
from bs4 import BeautifulSoup
import re

class KodikVideoParser:
    def __init__(self):
        self.base_url = "https://lordfilm.movie"
        self.search_url = f"{self.base_url}/index.php?do=search"
    
    def search(self, query):
        """
        Ищет фильмы на Lordfilm
        """
        try:
            # Отправляем поисковый запрос
            data = {
                "do": "search",
                "subaction": "search",
                "story": query
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.post(self.base_url + "/index.php", data=data, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            # Ищем карточки фильмов
            items = soup.find_all('div', class_='th-item')
            
            for item in items[:10]:
                title_elem = item.find('a', class_='th-title')
                if not title_elem:
                    continue
                
                title = title_elem.text.strip()
                link = title_elem.get('href')
                
                # Получаем постер
                img = item.find('img')
                poster = img.get('src') if img else ''
                
                # Получаем длительность
                duration_elem = item.find('div', class_='th-duration')
                duration = self._parse_duration(duration_elem.text.strip()) if duration_elem else 0
                
                if link:
                    # Получаем прямую ссылку на видео
                    video_url = self._get_video_url(link)
                    if video_url:
                        results.append({
                            'title': title,
                            'video_url': video_url,
                            'duration': duration,
                            'thumbnail': poster
                        })
            
            return results
            
        except Exception as e:
            print(f"Lordfilm search error: {e}")
            return []
    
    def _get_video_url(self, movie_url):
        """
        Извлекает прямую ссылку на видео со страницы фильма
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": self.base_url
            }
            
            response = requests.get(movie_url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем iframe с плеером
            iframe = soup.find('iframe', {'id': 'film_main'})
            if iframe and iframe.get('src'):
                player_url = iframe.get('src')
                
                # Загружаем страницу плеера
                player_response = requests.get(player_url, headers=headers, timeout=15)
                
                # Ищем прямую ссылку на MP4 или m3u8
                mp4_match = re.search(r'file:"([^"]+\.mp4)"', player_response.text)
                if mp4_match:
                    return mp4_match.group(1)
                
                m3u8_match = re.search(r'file:"([^"]+\.m3u8)"', player_response.text)
                if m3u8_match:
                    return m3u8_match.group(1)
                
                # Если не нашли — возвращаем ссылку на плеер
                return player_url
            
        except Exception as e:
            print(f"Error getting video URL: {e}")
        
        return None
    
    def _parse_duration(self, duration_str):
        """
        Переводит "1 ч 30 мин" или "120 мин" в секунды
        """
        try:
            hours = 0
            minutes = 0
            
            hour_match = re.search(r'(\d+)\s*ч', duration_str)
            if hour_match:
                hours = int(hour_match.group(1))
            
            min_match = re.search(r'(\d+)\s*мин', duration_str)
            if min_match:
                minutes = int(min_match.group(1))
            elif not hour_match:
                # Если только минуты (без "мин")
                num_match = re.search(r'(\d+)', duration_str)
                if num_match:
                    minutes = int(num_match.group(1))
            
            return hours * 3600 + minutes * 60
            
        except:
            return 0
