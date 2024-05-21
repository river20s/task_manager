from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 할 일과 태그 사이의 다대다 관계를 위한 연결 테이블
task_tags = db.Table('task_tags',
    db.Column('task_id', db.Integer, db.ForeignKey('task.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    tasks = db.relationship('Task', backref='owner', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    deadline = db.Column(db.DateTime, nullable=True)  # 마감기한 필드 추가
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tags = db.relationship('Tag', secondary=task_tags, lazy='subquery',
        backref=db.backref('tasks', lazy=True))

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(7), nullable=False)  # HTML 색상 코드 (#RRGGBB)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def home():
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    tasks = Task.query.filter_by(owner=current_user).all()
    tags = Tag.query.all()
    return render_template('index.html', current_time=current_time, tasks=tasks, tags=tags)

@app.route('/add', methods=['POST'])
@login_required
def add_task():
    task_text = request.form.get('task')
    tag_names = request.form.get('tags').split(',')
    deadline = request.form.get('deadline')
    if task_text:
        new_task = Task(task=task_text, owner=current_user)
        if deadline:
            new_task.deadline = datetime.strptime(deadline, '%Y-%m-%d')
        for tag_name in tag_names:
            tag_name = tag_name.strip()
            if tag_name:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name, color=_generate_random_color())
                    db.session.add(tag)
                new_task.tags.append(tag)
        db.session.add(new_task)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/complete/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    task = Task.query.get(task_id)
    if task and task.owner == current_user:
        task.completed = not task.completed
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/tag/<string:tag_name>')
@login_required
def tasks_by_tag(tag_name):
    tag = Tag.query.filter_by(name=tag_name).first_or_404()
    tasks = Task.query.filter(Task.tags.contains(tag), Task.owner == current_user).all()
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    return render_template('index.html', current_time=current_time, tasks=tasks, tags=Tag.query.all(), selected_tag=tag_name)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def _generate_random_color():
    return '#{0:06x}'.format(random.randint(0, 0xFFFFFF))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
