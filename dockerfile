# Используем официальный образ Python
FROM python:3.13-slim

# Устанавливаем системные зависимости для RepTube
RUN apt-get update && apt-get install -y \
    curl \
    lua5.4 \
    git \
    make \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем RepTube из официального репозитория
RUN git clone https://gitflic.ru/project/blogdron/reptube.git /opt/reptube && \
    cd /opt/reptube && \
    make install

# Устанавливаем зависимости Python
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Запускаем приложение
CMD ["python", "app.py"]
