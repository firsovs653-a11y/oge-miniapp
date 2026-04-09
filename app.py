@app.route('/api/search_vk', methods=['POST'])
@login_required
def search_vk():
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'Empty query'}), 400
    
    try:
        print(f"🔍 Searching VK for: {query}")
        print(f"📡 Response status: {response.status_code}")
        print(f"📄 Response length: {len(response.content)}")
        print(f"🔤 First 200 bytes: {response.content[:200]}")
        search_url = f"https://vk.com/video?q={query}&section=all"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(search_url, headers=headers)
        
        # Пробуем разные кодировки
        html = None
        for encoding in ['utf-8', 'windows-1251', 'cp1251', 'latin1']:
            try:
                html = response.content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if not html:
            return jsonify({'error': 'Failed to decode response'}), 500
        
        soup = BeautifulSoup(html, 'html.parser')
        
        videos = []
        # Ищем видео разными способами
        video_items = soup.select('.video_item') or soup.select('.video-card') or soup.select('[data-video-id]')
        
        for item in video_items:
            # Пробуем найти ссылку
            link = item.get('href', '')
            if not link:
                link_elem = item.select_one('a')
                link = link_elem.get('href', '') if link_elem else ''
            
            if '/video' in link:
                match = re.search(r'video(-?\d+_\d+)', link)
                if match:
                    video_id = match.group(1)
                    oid, vid = video_id.split('_')
                    embed_url = f"https://vk.com/video_ext.php?oid={oid}&id={vid}"
                    
                    title_elem = item.select_one('.video_item_title, .video-card__title, [data-title]')
                    title = title_elem.text.strip() if title_elem else 'Без названия'
                    title = title.encode('utf-8', errors='ignore').decode('utf-8')
                    
                    videos.append({'title': title, 'embed_url': embed_url})
        
        if not videos:
            return jsonify({'error': 'No videos found'}), 404
        
        return jsonify({'results': videos[:5]})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
