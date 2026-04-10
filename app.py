import re
import random
import string
import os
import secrets
import requests
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, join_room, emit
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, FriendRequest, Room, RoomMember, RoomInvite
from authlib.integrations.flask_client import OAuth
import eventlet

# ВАЖНО: Патч для корректной работы с eventlet
eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///kinobase.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Google OAuth конфигурация
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', '')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', '')

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ВАЖНО: Используем async_mode='eventlet' для Railway
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='eventlet',
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25
)

# Инициализация OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'},
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
)

# ==================== VK API ====================
VK_ACCESS_TOKEN = os.environ.get('VK_ACCESS_TOKEN', '')

# ==================== VK VIDEO SEARCH ====================
@app.route('/api/search_vk', methods=['POST'])
@login_required
def search_vk():
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'Empty query'}), 400
    
    # Заглушка — возвращает тестовые видео
    return jsonify({
        'results': [
            {
                'title': f'Тестовое видео по запросу "{query}"',
                'video_url': 'https://www.w3schools.com/html/mov_bbb.mp4',
                'duration': 600,
                'views': 1000
            },
            {
                'title': 'Big Buck Bunny (тестовое видео)',
                'video_url': 'https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4',
                'duration': 60,
                'views': 5000
            }
        ]
    })

# ==================== ОСНОВНЫЕ МАРШРУТЫ ====================
def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

@app.context_processor
def inject_config():
    return dict(config={
        'GOOGLE_CLIENT_ID': app.config['GOOGLE_CLIENT_ID']
    })

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
        
        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password)
        )
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

@app.route('/google_login')
def google_login():
    if not app.config['GOOGLE_CLIENT_ID']:
        flash('Вход через Google не настроен')
        return redirect(url_for('login'))
    
    redirect_uri = url_for('google_authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/google_authorize')
def google_authorize():
    try:
        token = google.authorize_access_token()
        user_info = google.get('userinfo').json()
        
        # Ищем пользователя по email
        user = User.query.filter_by(email=user_info['email']).first()
        
        if not user:
            # Создаем нового пользователя
            username = user_info['email'].split('@')[0]
            # Проверяем, не занят ли username
            counter = 1
            base_username = username
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                username=username,
                email=user_info['email'],
                password=generate_password_hash(secrets.token_urlsafe(32))
            )
            db.session.add(user)
            db.session.commit()
            flash(f'Аккаунт создан через Google! Ваш логин: {username}')
        
        login_user(user)
        return redirect(url_for('index'))
    
    except Exception as e:
        print(f"Google OAuth error: {e}")
        flash('Ошибка при входе через Google')
        return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/friends')
@login_required
def friends():
    incoming = FriendRequest.query.filter_by(
        to_user_id=current_user.id, 
        status='pending'
    ).all()
    return render_template('friends.html', incoming_requests=incoming)

@app.route('/search')
@login_required
def search():
    q = request.args.get('q', '')
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
    pending = FriendRequest.query.filter_by(
        from_user_id=current_user.id,
        to_user_id=user.id,
        status='pending'
    ).first()
    return render_template(
        'profile.html',
        profile_user=user,
        is_friend=is_friend,
        pending_request=pending
    )

@app.route('/send_request/<int:user_id>')
@login_required
def send_request(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('Пользователь не найден')
        return redirect(url_for('search'))
    
    if user == current_user:
        flash('Нельзя добавить себя')
        return redirect(url_for('search'))
    
    existing = FriendRequest.query.filter_by(
        from_user_id=current_user.id,
        to_user_id=user_id,
        status='pending'
    ).first()
    
    if not existing:
        db.session.add(FriendRequest(
            from_user_id=current_user.id,
            to_user_id=user_id
        ))
        db.session.commit()
        flash(f'Заявка отправлена {user.username}')
    
    return redirect(url_for('profile', username=user.username))

@app.route('/accept_request/<int:request_id>')
@login_required
def accept_request(request_id):
    req = db.session.get(FriendRequest, request_id)
    if not req:
        flash('Заявка не найдена')
        return redirect(url_for('friends'))
    
    if req.to_user_id == current_user.id:
        req.status = 'accepted'
        current_user.friends.append(req.from_user)
        req.from_user.friends.append(current_user)
        db.session.commit()
        flash(f'Вы добавили {req.from_user.username} в друзья')
    
    return redirect(url_for('friends'))

@app.route('/reject_request/<int:request_id>')
@login_required
def reject_request(request_id):
    req = db.session.get(FriendRequest, request_id)
    if not req:
        flash('Заявка не найдена')
        return redirect(url_for('friends'))
    
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
        (Room.id.in_(
            db.session.query(RoomMember.room_id).filter(
                RoomMember.user_id == current_user.id
            )
        ))
    ).all()
    
    invites = RoomInvite.query.filter_by(
        to_user_id=current_user.id,
        status='pending'
    ).all()
    
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
        
        room = Room(
            name=name,
            description=desc,
            code=code,
            is_private=is_private,
            created_by=current_user.id
        )
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
    room = db.session.get(Room, room_id)
    if not room:
        flash('Комната не найдена')
        return redirect(url_for('rooms'))
    
    if room.is_private and not room.is_member(current_user.id) and room.created_by != current_user.id:
        flash('Нет доступа к приватной комнате')
        return redirect(url_for('rooms'))
    
    members = RoomMember.query.filter_by(room_id=room.id).all()
    return render_template('room.html', room=room, members=members)

@app.route('/room/join', methods=['POST'])
@login_required
def join_room_code():
    code = request.form['code']
    room = Room.query.filter_by(code=code).first()
    
    if not room:
        flash('Комната с таким кодом не найдена')
        return redirect(url_for('rooms'))
    
    if room.is_member(current_user.id):
        flash('Вы уже в этой комнате')
        return redirect(url_for('room', room_id=room.id))
    
    db.session.add(RoomMember(room_id=room.id, user_id=current_user.id))
    db.session.commit()
    flash(f'Вы присоединились к комнате "{room.name}"')
    
    return redirect(url_for('room', room_id=room.id))

@app.route('/room/invite/<int:room_id>', methods=['GET', 'POST'])
@login_required
def invite_to_room(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        flash('Комната не найдена')
        return redirect(url_for('rooms'))
    
    if room.created_by != current_user.id:
        flash('Только создатель комнаты может приглашать')
        return redirect(url_for('room', room_id=room.id))
    
    if request.method == 'POST':
        friend_id = request.form['friend_id']
        friend = db.session.get(User, friend_id)
        
        if not friend:
            flash('Пользователь не найден')
            return redirect(url_for('room', room_id=room.id))
        
        existing = RoomInvite.query.filter_by(
            room_id=room.id,
            to_user_id=friend_id,
            status='pending'
        ).first()
        
        if not existing:
            db.session.add(RoomInvite(
                room_id=room.id,
                from_user_id=current_user.id,
                to_user_id=friend_id
            ))
            db.session.commit()
            flash(f'Приглашение отправлено {friend.username}')
        
        return redirect(url_for('room', room_id=room.id))
    
    friends = current_user.friends.all()
    return render_template('invite_to_room.html', room=room, friends=friends)

@app.route('/room/accept_invite/<int:invite_id>')
@login_required
def accept_room_invite(invite_id):
    invite = db.session.get(RoomInvite, invite_id)
    if not invite:
        flash('Приглашение не найдено')
        return redirect(url_for('rooms'))
    
    if invite.to_user_id == current_user.id:
        invite.status = 'accepted'
        db.session.add(RoomMember(room_id=invite.room_id, user_id=current_user.id))
        db.session.commit()
        flash(f'Вы присоединились к комнате "{invite.room.name}"')
        return redirect(url_for('room', room_id=invite.room_id))
    
    return redirect(url_for('rooms'))

@app.route('/room/reject_invite/<int:invite_id>')
@login_required
def reject_room_invite(invite_id):
    invite = db.session.get(RoomInvite, invite_id)
    if not invite:
        flash('Приглашение не найдено')
        return redirect(url_for('rooms'))
    
    if invite.to_user_id == current_user.id:
        invite.status = 'rejected'
        db.session.commit()
        flash('Приглашение отклонено')
    
    return redirect(url_for('rooms'))

@app.route('/room/leave/<int:room_id>')
@login_required
def leave_room_route(room_id):
    member = RoomMember.query.filter_by(
        room_id=room_id,
        user_id=current_user.id
    ).first()
    
    if member:
        db.session.delete(member)
        db.session.commit()
        flash('Вы покинули комнату')
    
    return redirect(url_for('rooms'))

# ==================== WEBSOCKET СИНХРОНИЗАЦИЯ ====================
@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')

@socketio.on('join')
def on_join(data):
    room = str(data['room_id'])
    join_room(room)
    print(f'Client {request.sid} joined room {room}')

@socketio.on('play')
def on_play(data):
    room = str(data['room_id'])
    time = data['current_time']
    print(f'Play in room {room} at {time}')
    emit('play_sync', {'current_time': time}, room=room, include_self=False)

@socketio.on('pause')
def on_pause(data):
    room = str(data['room_id'])
    time = data['current_time']
    print(f'Pause in room {room} at {time}')
    emit('pause_sync', {'current_time': time}, room=room, include_self=False)

@socketio.on('seek')
def on_seek(data):
    room = str(data['room_id'])
    time = data['current_time']
    print(f'Seek in room {room} to {time}')
    emit('seek_sync', {'current_time': time}, room=room, include_self=False)

@socketio.on('change_video')
def on_change_video(data):
    room = str(data['room_id'])
    url = data['video_url']
    print(f'Change video in room {room} to {url}')
    emit('video_change_sync', {'video_url': url}, room=room, include_self=False)

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    # ВАЖНО: Используем socketio.run с eventlet
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
