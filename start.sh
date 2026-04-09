#!/bin/bash

echo "📦 Устанавливаю RepTube..."

# Обновляем пакеты и устанавливаем зависимости
apt-get update && apt-get install -y curl lua5.4 git make

# Клонируем и устанавливаем RepTube
git clone https://gitflic.ru/project/blogdron/reptube.git /tmp/reptube
cd /tmp/reptube && make install && cd /

echo "✅ RepTube установлен"

# Запускаем приложение
python app.py
