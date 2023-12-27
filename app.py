from flask import Flask, request, send_file, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image
import io

app = Flask(__name__)
app.secret_key = 'your secret key'  # replace with your actual secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    images = db.relationship('Image', backref='user', lazy=True)

@app.route('/')
def home():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    else:
        return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            return "Username already exists."
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    else:
        return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['username'] = username
            return redirect(url_for('home'))
        else:
            return "Login failed."
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    user = User.query.filter_by(username=session['username']).first()
    Image.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    session.pop('username', None)
    return redirect(url_for('home'))


@app.route('/convert', methods=['POST'])
def convert_image():
    if 'username' not in session:
        return redirect(url_for('login'))
    file = request.files['image']
    try:
        image = Image.open(file.stream)
    except IOError:
        return "Invalid image file.", 400
    image = image.convert('RGB')
    byte_arr = io.BytesIO()
    image.save(byte_arr, format='WEBP')
    byte_arr.seek(0)
    user = User.query.filter_by(username=session['username']).first()
    new_image = Image(user_id=user.id, image_data=byte_arr.getvalue())
    db.session.add(new_image)
    db.session.commit()
    return send_file(byte_arr, mimetype='image/webp')

@app.route('/get_images', methods=['GET'])
def get_images():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['username']).first()
    images = Image.query.filter_by(user_id=user.id).all()
    return jsonify([str(image.image_data) for image in images])

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(port=5000)
