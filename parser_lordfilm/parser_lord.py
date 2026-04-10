


from bs4 import BeautifulSoup   # pip install beautifulsoup4
import requests # pip install requests
# pip install lxml
import random

import sqlite3

#моздаём базу данных
db = sqlite3.connect("films.db")
cur = db.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS lord_films (
    ID INTEGER PRIMARY KEY,
    RESURS TEXT,
    NAME TEXT,
    YEAR TEXT,
    DESCRIPTION TEXT,
    LINK_STR TEXT
)""")
db.commit()

resurs_name = "LordFilms"


user_agent_list = [
    'Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 uacq',
    'Mozilla/5.0 (Windows NT 11.0; Win64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5653.214 Safari/537.36'
]


url_page = "https://jk.lordfilm-s.space/filmi/page/"
url = "https://jk.lordfilm-s.space/filmi/"  # Ссылка на сайт откуда парсим
index_page = 1  # Индекс для страциц https://jk.lordfilm-s.space/filmi/page/index_page/

while True:
    # Каждую новую страницу будем парсить от имени нового Юзер-Агента
    user_agent = random.choice(user_agent_list)
    headers = {'User-Agent': user_agent}
    # ///

    page = BeautifulSoup(requests.get(url, headers=headers).text, "lxml")

    name_list = []
    year_list = []
    link_list = []
    description_list = []

    # названия фильмов
    for name in page.find_all("div", class_="th-title"):
        name_text = name.text
        #print(name_text)
        name_list.append(name_text)


    # Года фильмов
    for year in page.find_all("div", class_="th-year"):
        year_text = year.text
        #print(year_text)
        year_list.append(year_text)


    # Ссылки на страницы фильмов
    for film in page.find_all("div", class_="th-item"):
        link_str = film.find("a", class_="th-in with-mask").get('href')
       # print(link_str)
        link_list.append(link_str)


    # Парсим описание фильмов
    for link in link_list:
        page2 = BeautifulSoup(requests.get(link, headers=headers).text, "lxml")
        description = page2.find("div", class_="fdesc clearfix slice-this").text
        #print(description)
        # убираем артифакты
        b_split_list = description.split("						")
        b1 = b_split_list[-1]
        #print(b1)
        description_list.append(b1)


    i = 0
    while i < len(description_list):
        name1 = name_list[i]
        year1 = year_list[i]
        description1 = description_list[i]
        link2 = link_list[i]

        cur.execute("""INSERT INTO lord_films (RESURS, NAME, YEAR, DESCRIPTION, LINK_STR) VALUES (?, ?, ?, ?, ?);""",
                    (resurs_name, name1, year1, description1, link2))
        # print("Добавлено " + str(i))
        i = i + 1

    db.commit()


    print(f"Страниц записано: {index_page}")
    index_page = index_page + 1
    url = "https://jk.lordfilm-s.space/filmi/page/" + str(index_page) + "/"



    if index_page == 8:
        break


print("end of line")

