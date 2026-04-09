#!/bin/bash

echo "📦 Устанавливаю RepTube..."

apt-get update && apt-get install -y curl lua5.4 git make

if [ ! -d "/tmp/reptube" ]; then
    git clone https://gitflic.ru/project/blogdron/reptube.git /tmp/reptube
fi
cd /tmp/reptube && make install && cd /

echo "✅ RepTube установлен"

cd /app && python app.py
