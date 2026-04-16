import re
import random
import string
import os
import secrets
import requests
import json
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, join_room, emit
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, FriendRequest, Room, RoomMember, RoomInvite, ChatMessage
from soundcloud_parser import SoundCloudParser

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///kinobase.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Уберите эти строки:
# import eventlet
# eventlet.monkey_patch()

# Оставьте:
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
# ==================== JSON ЛОГ ПОЛЬЗОВАТЕЛЕЙ ====================
USERS_DATA_FILE = 'users_data.json'

def save_user_data(username, email, password_hash):
    """Сохраняет данные пользователя в JSON-файл"""
    try:
        with open(USERS_DATA_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        users = []
    
    users.append({
        'id': len(users) + 1,
        'username': username,
        'email': email,
        'password_hash': password_hash,
        'registered_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    with open(USERS_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Данные сохранены в {USERS_DATA_FILE}")

# ==================== VK API ====================
VK_ACCESS_TOKEN = os.environ.get('VK_ACCESS_TOKEN', '')

# ==================== VK VIDEO SEARCH ====================


# ==================== VK API ====================
VK_ACCESS_TOKEN = os.environ.get('VK_ACCESS_TOKEN', '')

# ==================== ПОИСК МУЗЫКИ SOUNDCLOUD ====================
@app.route('/api/search_music', methods=['POST'])
@login_required
def search_music():
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'Empty query'}), 400
    
    try:
        parser = SoundCloudParser()
        results = parser.search(query, limit=10)
        
        if not results:
            return jsonify({'results': [], 'message': 'Ничего не найдено'})
        
        return jsonify({'results': results})
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== ОСТАВЛЯЕМ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ ====================
@app.route('/api/search_video', methods=['POST'])
@login_required
def search_video():
    """Перенаправляет на поиск музыки"""
    return search_music()
# ==================== ОСНОВНЫЕ МАРШРУТЫ ====================
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
        
        if User.query.filter_by(email=email).first():
            flash('Email уже используется')
            return redirect(url_for('register'))
        
        password_hash = generate_password_hash(password)
        user = User(username=username, email=email, password=password_hash)
        db.session.add(user)
        db.session.commit()
        
        # Сохраняем в JSON
        save_user_data(username, email, password_hash)
        
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
    q = request.args.get('q', '').strip()
    users = []
    
    if q:
        users = User.query.filter(
            User.username.contains(q), 
            User.id != current_user.id
        ).all()
    
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

@app.route('/room/delete/<int:room_id>')
@login_required
def delete_room(room_id):
    room = Room.query.get_or_404(room_id)
    
    if room.created_by != current_user.id:
        flash('Только создатель может удалить комнату')
        return redirect(url_for('rooms'))
    
    ChatMessage.query.filter_by(room_id=room_id).delete()
    RoomInvite.query.filter_by(room_id=room_id).delete()
    RoomMember.query.filter_by(room_id=room_id).delete()
    db.session.delete(room)
    db.session.commit()
    
    flash(f'Комната "{room.name}" удалена')
    return redirect(url_for('rooms'))

@app.route('/room/leave/<int:room_id>')
@login_required
def leave_room_route(room_id):
    room = Room.query.get_or_404(room_id)
    
    if room.created_by == current_user.id:
        flash('Вы создатель комнаты. Используйте кнопку "Удалить"')
        return redirect(url_for('rooms'))
    
    member = RoomMember.query.filter_by(room_id=room_id, user_id=current_user.id).first()
    if member:
        db.session.delete(member)
        db.session.commit()
        flash(f'Вы покинули комнату "{room.name}"')
    
    return redirect(url_for('rooms'))

# ==================== WEBSOCKET СИНХРОНИЗАЦИЯ ====================
@socketio.on('join')
def on_join(data):
    room = str(data['room_id'])
    join_room(room)
    print(f'Client joined room {room}')

@socketio.on('play')
def on_play(data):
    room = str(data['room_id'])
    time = data['current_time']
    emit('play_sync', {'current_time': time}, room=room, include_self=False)

@socketio.on('pause')
def on_pause(data):
    room = str(data['room_id'])
    time = data['current_time']
    emit('pause_sync', {'current_time': time}, room=room, include_self=False)

@socketio.on('seek')
def on_seek(data):
    room = str(data['room_id'])
    time = data['current_time']
    emit('seek_sync', {'current_time': time}, room=room, include_self=False)

@socketio.on('change_video')
def on_change_video(data):
    room = str(data['room_id'])
    url = data['video_url']
    emit('video_change_sync', {'video_url': url}, room=room, include_self=False)

@socketio.on('send_message')
def on_send_message(data):
    room = str(data['room_id'])
    user_id = current_user.id
    message = data['message'][:500]
    
    msg = ChatMessage(room_id=int(room), user_id=user_id, message=message)
    db.session.add(msg)
    db.session.commit()
    
    emit('new_message', {
        'username': current_user.username,
        'message': message,
        'timestamp': msg.created_at.strftime('%H:%M')
    }, room=room)

@socketio.on('typing')
def on_typing(data):
    room = str(data['room_id'])
    emit('user_typing', {'username': current_user.username}, room=room, include_self=False)

@socketio.on('stop_typing')
def on_stop_typing(data):
    room = str(data['room_id'])
    emit('user_stop_typing', {'username': current_user.username}, room=room, include_self=False)
@app.route('/vk_callback')
def vk_callback():
    code = request.args.get('code')
    if code:
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>VK Auth - Sinchro</title></head>
        <body style="background:#0a0a1a; color:#fff; font-family:sans-serif; padding:40px; text-align:center;">
            <h2>✅ Код авторизации получен!</h2>
            <p>Скопируйте этот код и вставьте в терминал, где запущен скрипт:</p>
            <textarea rows="3" cols="80" readonly style="font-family:monospace; padding:10px; border-radius:8px;">{code}</textarea>
            <p style="margin-top:20px; color:#888;">Можно закрыть эту страницу</p>
        </body>
        </html>
        """
    else:
        return "<h2>❌ Ошибка: код не найден в URL</h2>"
# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
