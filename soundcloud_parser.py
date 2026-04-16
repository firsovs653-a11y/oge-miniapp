import requests

class SoundCloudParser:
    def __init__(self):
        # Публичный client_id SoundCloud (используется их собственным плеером)
        self.client_id = "a3e059563d7f33715b3b5e7e7d7c1e8c"
        self.base_url = "https://api-v2.soundcloud.com"
    
    def search(self, query, limit=10):
        """
        Ищет треки на SoundCloud
        """
        try:
            url = f"{self.base_url}/search/tracks"
            params = {
                "q": query,
                "client_id": self.client_id,
                "limit": limit,
                "app_version": "1740473827"  # Текущая версия приложения
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            data = response.json()
            
            results = []
            for track in data.get("collection", []):
                # Проверяем, есть ли потоковая ссылка
                stream_url = track.get("stream_url")
                if stream_url:
                    results.append({
                        'id': track.get('id'),
                        'title': track.get('title', 'Без названия'),
                        'artist': track.get('user', {}).get('username', 'Неизвестен'),
                        'audio_url': f"{stream_url}?client_id={self.client_id}",
                        'duration': track.get('duration', 0) // 1000,  # в секундах
                        'thumbnail': self._get_thumbnail(track),
                        'permalink': track.get('permalink_url', '')
                    })
            
            return results
            
        except Exception as e:
            print(f"SoundCloud search error: {e}")
            return []
    
    def _get_thumbnail(self, track):
        """Извлекает URL обложки"""
        # Пробуем разные варианты
        if track.get('artwork_url'):
            return track['artwork_url'].replace('large', 't500x500')
        if track.get('user', {}).get('avatar_url'):
            return track['user']['avatar_url'].replace('large', 't500x500')
        return ''
    
    def get_track_info(self, track_id):
        """Получает информацию о конкретном треке"""
        try:
            url = f"{self.base_url}/tracks/{track_id}"
            params = {"client_id": self.client_id}
            
            response = requests.get(url, params=params, timeout=10)
            track = response.json()
            
            stream_url = track.get("stream_url")
            if stream_url:
                return {
                    'id': track_id,
                    'title': track.get('title', 'Без названия'),
                    'artist': track.get('user', {}).get('username', 'Неизвестен'),
                    'audio_url': f"{stream_url}?client_id={self.client_id}",
                    'duration': track.get('duration', 0) // 1000,
                    'thumbnail': self._get_thumbnail(track)
                }
            
        except Exception as e:
            print(f"Error getting track info: {e}")
        
        return None
