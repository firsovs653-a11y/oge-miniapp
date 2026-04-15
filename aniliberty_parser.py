import requests

class AniLibertyParser:
    def __init__(self):
        # Актуальный базовый URL нового API [citation:10]
        self.base_url = "https://anilibria.top/api/v1"
    
    def search(self, query):
        """
        Ищет аниме по запросу и возвращает список с информацией о сериях
        """
        try:
            # 1. Поиск тайтла по названию
            search_response = requests.get(
                f"{self.base_url}/app/search/titles",
                params={"search": query},
                timeout=10
            )
            search_response.raise_for_status()
            titles = search_response.json()
            
            if not titles:
                return []
            
            videos = []
            for title in titles[:10]:  # Берем первые 10 результатов
                title_id = title.get('id')
                title_name = title.get('names', {}).get('ru', 'Без названия')
                poster_url = title.get('posters', {}).get('original', {}).get('url', '')
                
                # 2. Получаем информацию о сериях для этого тайтла
                series_response = requests.get(
                    f"{self.base_url}/app/series",
                    params={"title_id": title_id},
                    timeout=10
                )
                series_response.raise_for_status()
                series_data = series_response.json()
                
                # Обычно первая серия — первая в списке
                if series_data:
                    first_episode = series_data[0]
                    episode_id = first_episode.get('id')
                    
                    # 3. Получаем прямую ссылку на видео
                    video_url = self._get_video_url(episode_id)
                    
                    if video_url:
                        videos.append({
                            'title': f"{title_name} (Серия {first_episode.get('number', '1')})",
                            'video_url': video_url,
                            'duration': first_episode.get('duration', 0),
                            'thumbnail': poster_url
                        })
            
            return videos

        except Exception as e:
            print(f"AniLiberty search error: {e}")
            return []

    def _get_video_url(self, episode_id):
        """Получает прямую ссылку на MP4-файл серии"""
        try:
            response = requests.get(
                f"{self.base_url}/app/video",
                params={"id": episode_id},
                timeout=10
            )
            response.raise_for_status()
            video_data = response.json()
            
            # Берем ссылку на качество 720p (или максимальное доступное)
            qualities = video_data.get('qualities', [])
            if qualities:
                # Сортируем по качеству (чем выше, тем лучше)
                qualities.sort(key=lambda x: x.get('height', 0), reverse=True)
                return qualities[0].get('src')
            
            return None
            
        except Exception:
            return None
