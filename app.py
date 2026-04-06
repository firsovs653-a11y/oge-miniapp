from flask_socketio import SocketIO, emit, join_room, leave_room
from models import db, User, FriendRequest, Room, RoomMember, RoomInvite
import random
import string
import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, FriendRequest

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///kinobase.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)
    print(f"✅ Создана папка: {instance_path}")

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
with app.app_context():
    db.create_all()
    print("✅ База данных создана")



@app.route('/')
def index():
    return render_template('index.html', current_user=current_user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Логин занят')
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
    
    return render_template('register.html', current_user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль')
    
    return render_template('login.html', current_user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
@app.route('/profile/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    is_friend = user in current_user.friends
    pending_request = FriendRequest.query.filter_by(
        from_user_id=current_user.id, 
        to_user_id=user.id, 
        status='pending'
    ).first()
    return render_template('profile.html', profile_user=user, is_friend=is_friend, pending_request=pending_request)

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    users = User.query.filter(User.username.contains(query), User.id != current_user.id).all()
    return render_template('search.html', users=users, query=query)

@app.route('/send_request/<int:user_id>')
@login_required
def send_request(user_id):
    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash('Нельзя добавить себя в друзья')
        return redirect(url_for('search'))
    
    existing = FriendRequest.query.filter_by(
        from_user_id=current_user.id, 
        to_user_id=user_id, 
        status='pending'
    ).first()
    
    if existing:
        flash('Заявка уже отправлена')
    else:
        request_obj = FriendRequest(from_user_id=current_user.id, to_user_id=user_id)
        db.session.add(request_obj)
        db.session.commit()
        flash(f'Заявка отправлена пользователю {user.username}')
    
    return redirect(url_for('profile', username=user.username))

@app.route('/accept_request/<int:request_id>')
@login_required
def accept_request(request_id):
    req = FriendRequest.query.get_or_404(request_id)
    if req.to_user_id != current_user.id:
        flash('Доступ запрещён')
        return redirect(url_for('index'))
    
    req.status = 'accepted'
    current_user.friends.append(req.from_user)
    req.from_user.friends.append(current_user)
    db.session.commit()
    flash(f'Вы добавили {req.from_user.username} в друзья')
    return redirect(url_for('friends'))

@app.route('/reject_request/<int:request_id>')
@login_required
def reject_request(request_id):
    req = FriendRequest.query.get_or_404(request_id)
    if req.to_user_id != current_user.id:
        flash('Доступ запрещён')
        return redirect(url_for('index'))
    
    req.status = 'rejected'
    db.session.commit()
    flash('Заявка отклонена')
    return redirect(url_for('friends'))

@app.route('/friends')
@login_required
def friends():
    incoming_requests = FriendRequest.query.filter_by(to_user_id=current_user.id, status='pending').all()
    return render_template('friends.html', FriendRequest=FriendRequest, incoming_requests=incoming_requests)
# ==================== КОМНАТЫ ДЛЯ ПРОСМОТРА ====================

@app.route('/rooms')
@login_required
def rooms():
    # Мои комнаты (где я участник или создатель)
    my_rooms = Room.query.filter(
        (Room.created_by == current_user.id) |
        (Room.id.in_(db.session.query(RoomMember.room_id).filter(RoomMember.user_id == current_user.id)))
    ).all()
    
    # Приглашения в комнаты
    invites = RoomInvite.query.filter_by(to_user_id=current_user.id, status='pending').all()
    
    return render_template('rooms.html', rooms=my_rooms, invites=invites)

@app.route('/room/create', methods=['GET', 'POST'])
@login_required
def create_room():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        is_private = 'is_private' in request.form
        
        code = generate_room_code()
        while Room.query.filter_by(code=code).first():
            code = generate_room_code()
        
        room = Room(
            name=name,
            description=description,
            code=code,
            is_private=is_private,
            created_by=current_user.id
        )
        db.session.add(room)
        db.session.commit()
        
        # Добавляем создателя как участника
        member = RoomMember(room_id=room.id, user_id=current_user.id)
        db.session.add(member)
        db.session.commit()
        
        flash(f'Комната "{name}" создана! Код: {code}')
        return redirect(url_for('room', room_id=room.id))
    
    return render_template('create_room.html')

@app.route('/room/<int:room_id>')
@login_required
def room(room_id):
    room = Room.query.get_or_404(room_id)
    
    # Проверяем, имеет ли пользователь доступ
    if room.is_private and not room.is_member(current_user.id) and room.created_by != current_user.id:
        flash('У вас нет доступа к этой комнате')
        return redirect(url_for('rooms'))
    
    members = RoomMember.query.filter_by(room_id=room.id).all()
    return render_template('room.html', room=room, members=members)

@app.route('/room/join', methods=['POST'])
@login_required
def join_room():
    code = request.form['code']
    room = Room.query.filter_by(code=code).first()
    
    if not room:
        flash('Комната с таким кодом не найдена')
        return redirect(url_for('rooms'))
    
    if room.is_member(current_user.id):
        flash('Вы уже в этой комнате')
        return redirect(url_for('room', room_id=room.id))
    
    member = RoomMember(room_id=room.id, user_id=current_user.id)
    db.session.add(member)
    db.session.commit()
    
    flash(f'Вы присоединились к комнате "{room.name}"')
    return redirect(url_for('room', room_id=room.id))

@app.route('/room/invite/<int:room_id>', methods=['GET', 'POST'])
@login_required
def invite_to_room(room_id):
    room = Room.query.get_or_404(room_id)
    
    if room.created_by != current_user.id:
        flash('Только создатель комнаты может приглашать')
        return redirect(url_for('room', room_id=room.id))
    
    if request.method == 'POST':
        friend_id = request.form['friend_id']
        friend = User.query.get_or_404(friend_id)
        
        # Проверяем, не отправлено ли уже приглашение
        existing = RoomInvite.query.filter_by(
            room_id=room.id,
            to_user_id=friend_id,
            status='pending'
        ).first()
        
        if existing:
            flash('Приглашение уже отправлено')
        else:
            invite = RoomInvite(
                room_id=room.id,
                from_user_id=current_user.id,
                to_user_id=friend_id
            )
            db.session.add(invite)
            db.session.commit()
            flash(f'Приглашение отправлено {friend.username}')
        
        return redirect(url_for('room', room_id=room.id))
    
    # GET — показываем список друзей для приглашения
    friends = current_user.friends.all()
    return render_template('invite_to_room.html', room=room, friends=friends)

@app.route('/room/accept_invite/<int:invite_id>')
@login_required
def accept_invite(invite_id):
    invite = RoomInvite.query.get_or_404(invite_id)
    
    if invite.to_user_id != current_user.id:
        flash('Доступ запрещён')
        return redirect(url_for('rooms'))
    
    invite.status = 'accepted'
    member = RoomMember(room_id=invite.room_id, user_id=current_user.id)
    db.session.add(member)
    db.session.commit()
    
    flash(f'Вы присоединились к комнате "{invite.room.name}"')
    return redirect(url_for('room', room_id=invite.room_id))

@app.route('/room/reject_invite/<int:invite_id>')
@login_required
def reject_invite(invite_id):
    invite = RoomInvite.query.get_or_404(invite_id)
    
    if invite.to_user_id != current_user.id:
        flash('Доступ запрещён')
        return redirect(url_for('rooms'))
    
    invite.status = 'rejected'
    db.session.commit()
    
    flash('Приглашение отклонено')
    return redirect(url_for('rooms'))

@app.route('/room/leave/<int:room_id>')
@login_required
def leave_room(room_id):
    room = Room.query.get_or_404(room_id)
    
    member = RoomMember.query.filter_by(room_id=room.id, user_id=current_user.id).first()
    if member:
        db.session.delete(member)
        db.session.commit()
        flash(f'Вы покинули комнату "{room.name}"')
    
    return redirect(url_for('rooms'))
# ==================== WEBSOCKET ДЛЯ СИНХРОНИЗАЦИИ ВИДЕО ====================

@socketio.on('join_room')
def handle_join_room(data):
    room_id = data['room_id']
    join_room(str(room_id))
    emit('user_joined', {'user': current_user.username}, room=str(room_id))

@socketio.on('leave_room')
def handle_leave_room(data):
    room_id = data['room_id']
    leave_room(str(room_id))
    emit('user_left', {'user': current_user.username}, room=str(room_id))

@socketio.on('play')
def handle_play(data):
    room_id = data['room_id']
    current_time = data['current_time']
    # Обновляем состояние в БД
    with app.app_context():
        room = Room.query.get(room_id)
        if room:
            room.is_playing = True
            room.current_time = current_time
            db.session.commit()
    emit('sync_play', {'current_time': current_time}, room=str(room_id), include_self=False)

@socketio.on('pause')
def handle_pause(data):
    room_id = data['room_id']
    current_time = data['current_time']
    with app.app_context():
        room = Room.query.get(room_id)
        if room:
            room.is_playing = False
            room.current_time = current_time
            db.session.commit()
    emit('sync_pause', {'current_time': current_time}, room=str(room_id), include_self=False)

@socketio.on('seek')
def handle_seek(data):
    room_id = data['room_id']
    current_time = data['current_time']
    with app.app_context():
        room = Room.query.get(room_id)
        if room:
            room.current_time = current_time
            db.session.commit()
    emit('sync_seek', {'current_time': current_time}, room=str(room_id), include_self=False)

@socketio.on('change_video')
def handle_change_video(data):
    room_id = data['room_id']
    video_url = data['video_url']
    with app.app_context():
        room = Room.query.get(room_id)
        if room:
            room.video_url = video_url
            room.current_time = 0
            room.is_playing = False
            db.session.commit()
    emit('sync_change_video', {'video_url': video_url}, room=str(room_id), include_self=False)

@socketio.on('get_state')
def handle_get_state(data):
    room_id = data['room_id']
    with app.app_context():
        room = Room.query.get(room_id)
        if room:
            emit('sync_state', {
                'video_url': room.video_url,
                'current_time': room.current_time,
                'is_playing': room.is_playing
            })
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
