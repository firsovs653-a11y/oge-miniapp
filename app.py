from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

app = Flask(__name__)
app.config['SECRET_KEY'] = 'секретный_ключ_поменяй'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kinobase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

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
    return render_template('friends.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
