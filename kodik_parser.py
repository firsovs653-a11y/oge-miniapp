from anime_parsers_ru import KodikParser

class KodikVideoParser:
    def __init__(self):
        self.parser = KodikParser()
    
    def search(self, query):
        """
        Ищет видео по запросу и возвращает список результатов
        """
        try:
            results = self.parser.search(query)
            videos = []
            
            for item in results[:10]:  # Берём первые 10 результатов
                videos.append({
                    'title': item.title,
                    'video_url': item.url,  # Прямая ссылка на MP4
                    'duration': getattr(item, 'duration', 0),
                    'thumbnail': getattr(item, 'poster', ''),
                    'quality': getattr(item, 'quality', 'HD')
                })
            
            return videos
        except Exception as e:
            print(f"Kodik search error: {e}")
            return []
