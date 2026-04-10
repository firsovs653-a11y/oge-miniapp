import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'parser_lordfilm'))

from parser_lord import LordFilmParser

class LordFilmWrapper:
    def __init__(self):
        self.parser = LordFilmParser()
    
    def search_movie(self, query):
        try:
            # Вызываем метод поиска твоего парсера
            return self.parser.search_movie(query)
        except Exception as e:
            print(f"Parser error: {e}")
            return None
