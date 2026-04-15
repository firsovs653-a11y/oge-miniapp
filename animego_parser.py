from anicli_api.source.animego import Animego
from anicli_api.player.kodik import Kodik

class AnimeGoParser:
    def __init__(self):
        # Используем публичный плеер Kodik (не требует токена)
        self.player = Kodik()
        self.source = Animego()
    
    def search(self, query):
        """
        Ищет аниме по запросу и возвращает список с прямыми ссылками
        """
        try:
            # Поиск на animego.org
            results = self.source.search(query)
            videos = []
            
            for anime in results[:5]:  # Берём первые 5 результатов
                # Получаем список серий
                episodes = anime.get_episodes()
                if not episodes:
                    continue
                
                # Берём первую серию
                episode = episodes[0]
                
                # Получаем источники видео (Kodik)
                sources = episode.get_sources()
                if not sources:
                    continue
                
                # Берём первый источник
                source = sources[0]
                
                # Получаем прямую ссылку через Kodik
                video = source.get_video()
                if video:
                    videos.append({
                        'title': f"{anime.title} (Серия {episode.num})",
                        'video_url': video.url,
                        'duration': 0,  # animego не отдаёт длительность
                        'thumbnail': anime.thumbnail if hasattr(anime, 'thumbnail') else '',
                        'quality': video.quality if hasattr(video, 'quality') else 'HD'
                    })
            
            return videos
            
        except Exception as e:
            print(f"AnimeGo search error: {e}")
            return []
