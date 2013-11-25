import time
from sqlite3 import dbapi2 as sqlite3
from hashlib import md5
from datetime import datetime
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash, _app_ctx_stack
from werkzeug import check_password_hash, generate_password_hash


# config
DATABASE = '/tmp/manifest.db'
DEBUG = True
SECRET_KEY = 'development key'

# create app
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('MANIFEST_SETTINGS', silent=True)

## DB stuff
def get_db():
	top = _app_ctx_stack.top
	if not hasattr(top, 'sqlite_db'):
		top.sqlite_db = sqlite3.connect(app.config['DATABASE'])
		top.sqlite_db.row_factory = sqlite3.Row
	return top.sqlite_db


def init_db():
	with app.app_context():
		db = get_db()
		with app.open_resource('schema.sql', mode='r') as f:
			db.cursor().executescript(f.read())
		db.commit()
		db_test_fill()

def db_test_fill():
	db = get_db()
	db.execute('insert into users (first_name,last_name,email,pw_hash) values (?,?,?,?)',
	                 ['Espen', 
									 'Gundersen',
									 'espen11@gmail.com',
									 'pbkdf2:sha1:1000$HN75Jqn2$4c93b9a4d9e45c1514e588af65d0225a5db5924d'])
	db.execute('insert into users (first_name,last_name,email,pw_hash) values (?,?,?,?)',
	                 ['Tommy', 
									 'Jensen',
									 'tommybjensen@gmail.com',
									 'pbkdf2:sha1:1000$HN75Jqn2$4c93b9a4d9e45c1514e588af65d0225a5db5924d'])
	db.execute('insert into planes (name,model) values (?,?)',['LN-VYN','C206'])
	db.execute('insert into planes (name,model) values (?,?)',['LN-PER','C207'])
	db.execute('insert into loads (plane_id) values (?)',['1'])
	db.execute('insert into loads (plane_id) values (?)',['2'])
	db.execute('insert into loads (plane_id) values (?)',['1'])
	db.execute('insert into slot (user_id,load_id) values (?,?)',['1','1'])

	db.commit()

def query_db(query, args=(), one=False):
	cur = get_db().execute(query, args)
	rv = cur.fetchall()
	return (rv[0] if rv else None) if one else rv
## /DB stuff


def get_user_id(email):
	rv = query_db('select user_id from users where email = ?',
	              [email], one=True)
	return rv[0] if rv else None


@app.teardown_appcontext
def close_database(exception):
	top = _app_ctx_stack.top
	if hasattr(top, 'sqlite_db'):
		top.sqlite_db.close()


@app.before_request
def before_request():
	g.user = None
	if 'user_id' in session:
		g.user = query_db('select * from users where user_id = ?',
	                      [session['user_id']], one=True)


@app.route('/')
def index():
	userlist = query_db('select * from users')
	return render_template('all_users.html', users=userlist)


@app.route('/new_load', methods=['GET', 'POST'])
def new_load():
	planes = query_db('select * from planes')
	return render_template('new_load.html', planes=planes)
	if request.method == 'POST':
		flash(request.form['plane'])
	
#	userlist = query_db('select * from users')
#	return render_template('new_load.html', users=userlist)


@app.route('/load/<load_id>')
def show_load(load_id):
	load = query_db('select * from loads where load_id = ?',[load_id])
	plane_id = load[0][1]
	plane = query_db('select * from planes where plane_id = ?',[plane_id])
	plane_name = plane[0][1]
	return render_template('load.html', loads=load, plane=plane_name)


@app.route('/all_loads')
def all_loads():
	loadlist = query_db('select * from loads')
	return render_template('all_loads.html', loads=loadlist)


@app.route('/all_users')
def all_users():
	userlist = query_db('select * from users')
	return render_template('all_users.html', users=userlist)


@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
	if request.method == 'POST':
		db = get_db()
		db.execute('insert into users (first_name, last_name) values (?, ?)',
		                 [request.form['first_name'], request.form['last_name']])
		db.commit()
		flash('User added')
	return render_template('add_user.html')


@app.route('/delete_user', methods=['GET', 'POST'])
def delete_user():
	if request.method == 'POST':
		db = get_db()
		db.execute('delete from users where first_name=? and last_name=?',
		                 [request.form['first_name'], request.form['last_name']])
		db.commit()
		flash('User deleted')
	return render_template('delete_user.html')


@app.route('/<user_id>')
def user_home(user_id):
	profile_user = query_db('select * from users where user_id = ?',
	                        [user_id], one=True)
	if profile_user is None:
		abort(404)


@app.route('/login', methods=['GET', 'POST'])
def login():
	if g.user:
		return redirect(url_for('all_users'))
	error = None
	if request.method == 'POST':
		user = query_db('''select * from users where
			email = ?''', [request.form['email']], one=True)
		if user is None:
			error = 'Invalid email'
		elif not check_password_hash(user['pw_hash'],
		                             request.form['password']):
			error = 'Invalid password'
		else:
			flash('You were logged in')
			session['user_id'] = user['user_id']
			return redirect(url_for('all_users'))
	return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
	if g.user:
		return redirect(url_for('all_users'))
	error = None
	if request.method == 'POST':
		if not request.form['first_name']:
			error = 'You have to enter a first name'
		elif not request.form['last_name']:
			error = 'You have to enter a last name'
		elif not request.form['email'] or \
		         '@' not in request.form['email']:
			error = 'You have to enter a valid email address'
		elif not request.form['password']:
			error = 'You have to enter a password'
		elif request.form['password'] != request.form['password2']:
			error = 'The two passwords do not match'
		elif get_user_id(request.form['email']) is not None:
			error = 'The email is already used'
		else:
			db = get_db()
			db.execute('''insert into users (first_name, last_name, email, pw_hash) values (?, ?, ?, ?)''', [request.form['first_name'], request.form['last_name'], request.form['email'], generate_password_hash(request.form['password'])])
			db.commit()
			flash('You were successfully registered and can login')
			return redirect(url_for('login'))
	return render_template('register.html', error=error)


@app.route('/logout')
def logout():
	flash('You were logged out')
	session.pop('user_id', None)
	return redirect(url_for('all_users'))


if __name__ == '__main__':
	init_db()
	app.run()
