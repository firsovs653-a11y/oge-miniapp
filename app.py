import re
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, join_room, leave_room, emit
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, FriendRequest, Room, RoomMember, RoomInvite
import random
import string
import os
import subprocess
import json
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///kinobase.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
@app.route('/api/search_rutube', methods=['POST'])
@login_required


@app.route('/api/search_vk', methods=['POST'])
@login_required
def search_vk():
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'Empty query'}), 400
    
    try:
        # Поиск видео через VK API (публичный, без токена)
        url = "https://api.vk.com/method/video.search"
        params = {
            'q': query,
            'count': 10,
            'sort': 2,  # по релевантности
            'hd': 1,
            'adult': 1,
            'v': '5.131'
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'error' in data:
            return jsonify({'error': data['error']['error_msg']}), 500
        
        videos = []
        for item in data.get('response', {}).get('items', []):
            owner_id = item['owner_id']
            video_id = item['id']
            embed_url = f"https://vk.com/video_ext.php?oid={owner_id}&id={video_id}&hd=1"
            
            videos.append({
                'title': item['title'],
                'embed_url': embed_url,
                'duration': item.get('duration', 0),
                'views': item.get('views', 0)
            })
        
        return jsonify({'results': videos})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
def search_rutube():
    data = request.get_json()
    query = data.get('query', '').strip().lower()
    
    # База тестовых видео
    videos_db = [
        {'title': 'Матрица (1999) — трейлер', 'embed_url': 'https://rutube.ru/play/embed/7716bd3e665725c3c008ae7ab4ff02e2', 'channel': 'Кинопоиск'},
        {'title': 'Матрица: Перезагрузка (2003)', 'embed_url': 'https://rutube.ru/play/embed/7716bd3e665725c3c008ae7ab4ff02e3', 'channel': 'Кинопоиск'},
        {'title': 'Матрица: Революция (2003)', 'embed_url': 'https://rutube.ru/play/embed/7716bd3e665725c3c008ae7ab4ff02e4', 'channel': 'Кинопоиск'},
        {'title': 'Терминатор 2 (1991)', 'embed_url': 'https://rutube.ru/play/embed/123', 'channel': 'Кино'}
    ]
    
    # Фильтруем по запросу
    results = [v for v in videos_db if query in v['title'].lower()]
    
    return jsonify({'results': results})

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

socketio = SocketIO(app, cors_allowed_origins="*")

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

with app.app_context():
    db.create_all()

# ==================== ОСНОВНЫЕ МАРШРУТЫ ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Логин занят')
            return redirect(url_for('register'))
        user = User(username=username, email=email, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash('Регистрация успешна! Войдите')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Неверный логин или пароль')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/friends')
@login_required
def friends():
    incoming = FriendRequest.query.filter_by(to_user_id=current_user.id, status='pending').all()
    return render_template('friends.html', incoming_requests=incoming)

@app.route('/search')
@login_required
def search():
    q = request.args.get('q', '')
    users = User.query.filter(User.username.contains(q), User.id != current_user.id).all()
    return render_template('search.html', users=users, query=q)

@app.route('/profile/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    is_friend = user in current_user.friends
    pending = FriendRequest.query.filter_by(from_user_id=current_user.id, to_user_id=user.id, status='pending').first()
    return render_template('profile.html', profile_user=user, is_friend=is_friend, pending_request=pending)

@app.route('/send_request/<int:user_id>')
@login_required
def send_request(user_id):
    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash('Нельзя добавить себя')
        return redirect(url_for('search'))
    if not FriendRequest.query.filter_by(from_user_id=current_user.id, to_user_id=user_id, status='pending').first():
        db.session.add(FriendRequest(from_user_id=current_user.id, to_user_id=user_id))
        db.session.commit()
        flash(f'Заявка отправлена {user.username}')
    return redirect(url_for('profile', username=user.username))

@app.route('/accept_request/<int:request_id>')
@login_required
def accept_request(request_id):
    req = FriendRequest.query.get_or_404(request_id)
    if req.to_user_id == current_user.id:
        req.status = 'accepted'
        current_user.friends.append(req.from_user)
        req.from_user.friends.append(current_user)
        db.session.commit()
        flash(f'Вы добавили {req.from_user.username}')
    return redirect(url_for('friends'))

@app.route('/reject_request/<int:request_id>')
@login_required
def reject_request(request_id):
    req = FriendRequest.query.get_or_404(request_id)
    if req.to_user_id == current_user.id:
        req.status = 'rejected'
        db.session.commit()
        flash('Заявка отклонена')
    return redirect(url_for('friends'))

# ==================== КОМНАТЫ ====================

@app.route('/rooms')
@login_required
def rooms():
    my_rooms = Room.query.filter(
        (Room.created_by == current_user.id) |
        (Room.id.in_(db.session.query(RoomMember.room_id).filter(RoomMember.user_id == current_user.id)))
    ).all()
    invites = RoomInvite.query.filter_by(to_user_id=current_user.id, status='pending').all()
    return render_template('rooms.html', rooms=my_rooms, invites=invites)

@app.route('/room/create', methods=['GET', 'POST'])
@login_required
def create_room():
    if request.method == 'POST':
        name = request.form['name']
        desc = request.form.get('description', '')
        is_private = 'is_private' in request.form
        code = generate_room_code()
        while Room.query.filter_by(code=code).first():
            code = generate_room_code()
        room = Room(name=name, description=desc, code=code, is_private=is_private, created_by=current_user.id)
        db.session.add(room)
        db.session.commit()
        db.session.add(RoomMember(room_id=room.id, user_id=current_user.id))
        db.session.commit()
        flash(f'Комната "{name}" создана! Код: {code}')
        return redirect(url_for('room', room_id=room.id))
    return render_template('create_room.html')

@app.route('/room/<int:room_id>')
@login_required
def room(room_id):
    room = Room.query.get_or_404(room_id)
    if room.is_private and not room.is_member(current_user.id) and room.created_by != current_user.id:
        flash('Нет доступа')
        return redirect(url_for('rooms'))
    members = RoomMember.query.filter_by(room_id=room.id).all()
    return render_template('room.html', room=room, members=members)

@app.route('/room/join', methods=['POST'])
@login_required
def join_room_code():
    code = request.form['code']
    room = Room.query.filter_by(code=code).first()
    if not room:
        flash('Комната не найдена')
        return redirect(url_for('rooms'))
    if room.is_member(current_user.id):
        flash('Вы уже в комнате')
        return redirect(url_for('room', room_id=room.id))
    db.session.add(RoomMember(room_id=room.id, user_id=current_user.id))
    db.session.commit()
    flash(f'Вы присоединились к "{room.name}"')
    return redirect(url_for('room', room_id=room.id))

@app.route('/room/invite/<int:room_id>', methods=['GET', 'POST'])
@login_required
def invite_to_room(room_id):
    room = Room.query.get_or_404(room_id)
    if room.created_by != current_user.id:
        flash('Только создатель может приглашать')
        return redirect(url_for('room', room_id=room.id))
    if request.method == 'POST':
        friend_id = request.form['friend_id']
        friend = User.query.get_or_404(friend_id)
        if not RoomInvite.query.filter_by(room_id=room.id, to_user_id=friend_id, status='pending').first():
            db.session.add(RoomInvite(room_id=room.id, from_user_id=current_user.id, to_user_id=friend_id))
            db.session.commit()
            flash(f'Приглашение отправлено {friend.username}')
        return redirect(url_for('room', room_id=room.id))
    friends = current_user.friends.all()
    return render_template('invite_to_room.html', room=room, friends=friends)

@app.route('/room/accept_invite/<int:invite_id>')
@login_required
def accept_room_invite(invite_id):
    invite = RoomInvite.query.get_or_404(invite_id)
    if invite.to_user_id == current_user.id:
        invite.status = 'accepted'
        db.session.add(RoomMember(room_id=invite.room_id, user_id=current_user.id))
        db.session.commit()
        flash(f'Вы присоединились к "{invite.room.name}"')
        return redirect(url_for('room', room_id=invite.room_id))
    return redirect(url_for('rooms'))

@app.route('/room/reject_invite/<int:invite_id>')
@login_required
def reject_room_invite(invite_id):
    invite = RoomInvite.query.get_or_404(invite_id)
    if invite.to_user_id == current_user.id:
        invite.status = 'rejected'
        db.session.commit()
        flash('Приглашение отклонено')
    return redirect(url_for('rooms'))

@app.route('/room/leave/<int:room_id>')
@login_required
def leave_room_route(room_id):
    member = RoomMember.query.filter_by(room_id=room_id, user_id=current_user.id).first()
    if member:
        db.session.delete(member)
        db.session.commit()
        flash('Вы покинули комнату')
    return redirect(url_for('rooms'))

# ==================== WEBSOCKET ====================

@socketio.on('join')
def on_join(data):
    room = str(data['room_id'])
    join_room(room)
    print(f'Client joined room {room}')

@socketio.on('play')
def on_play(data):
    room = str(data['room_id'])
    time = data['current_time']
    print(f'Play in room {room} at {time}')
    socketio.emit('play_sync', {'current_time': time}, room=room, include_self=False)

@socketio.on('pause')
def on_pause(data):
    room = str(data['room_id'])
    time = data['current_time']
    print(f'Pause in room {room} at {time}')
    socketio.emit('pause_sync', {'current_time': time}, room=room, include_self=False)

@socketio.on('seek')
def on_seek(data):
    room = str(data['room_id'])
    time = data['current_time']
    print(f'Seek in room {room} to {time}')
    socketio.emit('seek_sync', {'current_time': time}, room=room, include_self=False)

@socketio.on('change_video')
def on_change_video(data):
    room = str(data['room_id'])
    url = data['video_url']
    print(f'Change video in room {room} to {url}')
    socketio.emit('video_change_sync', {'video_url': url}, room=room, include_self=False)

# ==================== ЗАПУСК ====================

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
