from flask import Flask, request, jsonify, g, render_template, redirect, flash, make_response
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
import psycopg2
import json
import dateutil.parser
import uuid
import os
import pathlib
import bcrypt
import subprocess
import sys

# import ../config.py
sys.path.append('..')
import config

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'memcached'
app.config['SECRET_KEY'] = config.SESSION_SECRET_KEY
login_manager = LoginManager()
login_manager.init_app(app)

# use dicts and lists as json in postgres
import psycopg2.extras
psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)
psycopg2.extensions.register_adapter(list, psycopg2.extras.Json)

# setup g.db as postgres
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = psycopg2.connect(host=config.DATABASE_HOST, database=config.DATABASE_DB, user=config.DATABASE_USER, password=config.DATABASE_PW)
    return db
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
    conn = get_db()
def query_db(query, args=()):
    conn = get_db()
    with conn, conn.cursor() as cursor:
        cursor.execute(query, args)
        return cursor.fetchall()
def query_db_one(query, args=()):
    conn = get_db()
    with conn, conn.cursor() as cursor:
        cursor.execute(query, args)
        return cursor.fetchone()
def db_execute(query, args=()):
    conn = get_db()
    with conn, conn.cursor() as cursor:
        cursor.execute(query, args)

def check_password(plain_text_password, hashed_password):
    # Check hashed password. Using bcrypt, the salt is saved into the hash itself
    return bcrypt.checkpw(plain_text_password.encode('utf8'), hashed_password.encode('utf8'))

class User:
    def __init__(self, user_id):
        self.user_id = user_id
        # flask-login required values:
        self.is_active = True
        self.is_authenticated = True
        self.is_anonymous = False
    def get_id(self):
        return self.user_id

@login_manager.user_loader
def load_user(user_id):
    print(f"User id: {user_id}")
    return User(user_id)

@login_manager.unauthorized_handler
def unauthorized():
    return redirect('/admin/login', code=303)

# Make redirects use "Location: /admin/login" instead
# of "Location: http://localhost/admin/login" so python
# doesn't have to know the hostname and port.
@app.after_request
def dont_make_location_header_relative(response):
    response.autocorrect_location_header = False
    return response

@app.route('/admin/login', methods=['GET'])
def admin_login():
    if current_user.is_authenticated:
        return redirect('/admin/polls', code=303)
    return render_template('login.html')

@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    login = request.form['login']
    password = request.form['password']
    row = query_db_one('select id, password_hash from users where username=%s', [login])
    if not row:
        flash("Użytkownik nie istnieje lub podano złe hasło")
        return unauthorized()
    user_id, password_hash = row
    if not check_password(password, password_hash):
        flash("Użytkownik nie istnieje lub podano złe hasło")
        return unauthorized()
    login_user(User(user_id))
    return redirect('/admin/polls', code=303)

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return unauthorized()

@app.route('/admin/polls', methods=['GET'])
@login_required
def admin_polls():
    polls = list({
            'id': voting[0],
            'name': voting[1],
            'choices': voting[2],
            'choiceType': voting[3],
            'visibility': voting[4],
            'closesOnDate': voting[5]
        } for voting in query_db('select id, name, options, choice_type, visibility, closes_on_date from polls where closed=false and owner_user=%s order by id',
                                 [int(current_user.get_id())]))
    return render_template('polls.html', polls=polls, closed=False)

@app.route('/admin/closedpolls', methods=['GET'])
@login_required
def admin_closedpolls():
    polls = list({
            'id': voting[0],
            'name': voting[1],
            'choices': voting[2],
            'choiceType': voting[3],
            'visibility': voting[4],
            'closesOnDate': voting[5]
        } for voting in query_db('select id, name, options, choice_type, visibility, closes_on_date from polls where closed=true and owner_user=%s order by id',
                                 [int(current_user.get_id())]))
    return render_template('polls.html', polls=polls, closed=True)

@app.route('/admin/addpoll', methods=['GET'])
@login_required
def admin_addpoll():
    return render_template('addpoll.html')

@app.route('/admin/addpoll', methods=['POST'])
@login_required
def admin_addpoll_post():
    db_execute('insert into polls(name, options, choice_type, visibility, possible_recipients, \
                    closes_on_date, owner_user, sent_to, sending_out_to, mail_template, max_choices, description) \
                    values(%s,%s,%s,%s,%s,%s,%s,\'[]\',\'[]\',%s,%s,%s);',
        [
            request.form['name'],
            json.loads(request.form['options']),
            request.form['choiceType'],
            request.form['visibility'],
            json.loads(request.form['recipients']),
            request.form['closesOnDate'],
            int(current_user.get_id()),
            request.form['mailTemplate'],
            int(request.form['maxChoices']),
            request.form['description']
        ])
    get_db().commit()

    return redirect('/admin/polls', code=303)

@app.route('/admin/copypoll', methods=['GET'])
@login_required
def admin_copypoll():
    poll_id = request.args.get('id')
    row = query_db_one('select name, options, choice_type, possible_recipients, sending_out_to, closes_on_date, mail_template, max_choices, description from polls\
                        where id = %s and owner_user = %s', [poll_id, int(current_user.get_id())])
    if not row:
        return "Głosowanie nie istnieje", 400
    name, options, choice_type, possible_recipients, sending_out_to, closes_on_date, mail_template, max_choices, description = row
    return render_template('copypoll.html', poll_id=poll_id, name=name, options=options, choice_type=choice_type,
                            possible_recipients=possible_recipients, sending_out_to_amount=0,
                            closes_on_date=closes_on_date, mail_template=mail_template, should_disable=False,
                            max_choices=max_choices, description=description)

@app.route('/admin/editpoll', methods=['GET'])
@login_required
def admin_editpoll():
    poll_id = request.args.get('id')
    row = query_db_one('select name, options, choice_type, possible_recipients, sending_out_to, closes_on_date, mail_template, max_choices, description from polls\
                        where id = %s and owner_user = %s', [poll_id, int(current_user.get_id())])
    if not row:
        return "Głosowanie nie istnieje", 400
    name, options, choice_type, possible_recipients, sending_out_to, closes_on_date, mail_template, max_choices, description = row
    sending_out_to_amount = len(sending_out_to)
    should_disable = "disabled" if sending_out_to_amount > 0 else ""
    return render_template('editpoll.html', poll_id=poll_id, name=name, options=options, choice_type=choice_type,
                            possible_recipients=possible_recipients, sending_out_to_amount=sending_out_to_amount,
                            closes_on_date=closes_on_date, mail_template=mail_template, should_disable=should_disable,
                            max_choices=max_choices, description=description)

@app.route('/admin/editpoll', methods=['POST'])
@login_required
def admin_editpoll_post():
    poll_id = int(request.args.get('id'))
    name, sending_out_to, closed = query_db_one('select name, sending_out_to, closed from polls where id=%s and owner_user=%s',
                                        [poll_id, int(current_user.get_id())])

    if len(sending_out_to) == 0:
        db_execute('update polls set name=%s, options=%s, choice_type=%s, visibility=%s, possible_recipients=%s, closes_on_date=%s, mail_template=%s, max_choices=%s, description=%s \
                    where id=%s and owner_user=%s', [
                request.form['name'],
                json.loads(request.form['options']),
                request.form['choiceType'],
                request.form['visibility'],
                json.loads(request.form['recipients']),
                request.form['closesOnDate'],
                request.form['mailTemplate'],
                int(request.form['maxChoices']),
                request.form['description'],
                poll_id,
                int(current_user.get_id())
            ])
        get_db().commit()
    else:
        flash("Nie można zedytować głosowania \"{}\" ponieważ rozsyłanie maili już się rozpoczęło".format(name))
    
    if closed:
        return redirect('/admin/closedpolls', code=303)
    else:
        return redirect('/admin/polls', code=303)

def list_without(l1, l2):
    s = set(l2)
    return [el for el in l1 if el not in s]

@app.route('/admin/sendout', methods=['GET'])
@login_required
def admin_sendout():
    poll_id = int(request.args.get('id'))
    row = query_db_one('set time zone \'Europe/Warsaw\'; select name, possible_recipients, sending_out_to, sent_to, mailing_active, planned_start_sending::timestamp::text, closed from polls where id=%s and owner_user=%s',
                        [poll_id, int(current_user.get_id())])
    if not row:
        return "Głosowanie nie istnieje", 400
    name, possible_recipients, sending_out_to, sent_to, mailing_active, planned_start_sending, closed = row
    mailing_active = mailing_active

    possible_recipients = list_without(list_without(possible_recipients, sending_out_to), sent_to)
    sending_out_to = list_without(sending_out_to, sent_to)

    return render_template('sendout.html',
            id=poll_id,
            name=name,
            possible_recipients=possible_recipients,
            sending_out_to=sending_out_to,
            sent_to=sent_to,
            mailing_active=mailing_active,
            planned_start_sending=planned_start_sending,
            closed=closed)

@app.route('/admin/sendout/unplan', methods=['POST'])
def admin_sendout_unplan_post():
    poll_id = int(request.args.get('id'))

    # This is not useless: make sure the current user has permissions to the poll
    row = query_db_one('select id from polls where id=%s and owner_user=%s',
                        [poll_id, int(current_user.get_id())])
    if not row:
        return "Głosowanie nie istnieje", 400

    db_execute('update polls set planned_start_sending=null where id=%s and owner_user=%s', 
        [poll_id, int(current_user.get_id())])
    get_db().commit()

    return redirect(f'/admin/sendout?id={poll_id}', code=303)

@app.route('/admin/sendout/plan', methods=['POST'])
def admin_sendout_plan_post():
    poll_id = int(request.args.get('id'))

    # This is not useless: make sure the current user has permissions to the poll
    row = query_db_one('select id from polls where id=%s and owner_user=%s',
                        [poll_id, int(current_user.get_id())])
    if not row:
        return "Głosowanie nie istnieje", 400

    timestamp = f'{request.form["planSendoutDate"]} {request.form["planSendoutTime"]}'
    db_execute('set time zone \'Europe/Warsaw\'; update polls set planned_start_sending=%s::timestamptz where id=%s and owner_user=%s', 
        [timestamp, poll_id, int(current_user.get_id())])
    get_db().commit()

    return redirect(f'/admin/sendout?id={poll_id}', code=303)

@app.route('/admin/sendout/queueselected', methods=['POST'])
@login_required
def admin_sendout_queueselected_post():
    poll_id = int(request.args.get('id'))

    row = query_db_one('select sending_out_to from polls where id=%s and owner_user=%s', [poll_id, int(current_user.get_id())])
    if not row:
        return "Głosowanie nie istnieje", 400
    sending_out_to = row[0]
    add_to_sending_out_to = json.loads(request.form['selected'])
    sending_out_to = sending_out_to + add_to_sending_out_to
    db_execute('update polls set sending_out_to=%s where id=%s and owner_user=%s', [sending_out_to, poll_id, int(current_user.get_id())])
    get_db().commit()
    
    return redirect('/admin/sendout?id=' + str(poll_id), code=303)

@app.route('/admin/sendout/queueall', methods=['POST'])
@login_required
def admin_sendout_queueall_post():
    poll_id = int(request.args.get('id'))
    db_execute('update polls \
                set sending_out_to=(select possible_recipients from polls where id=%s and owner_user=%s) \
                where id=%s and owner_user=%s',
                [poll_id, int(current_user.get_id()), poll_id, int(current_user.get_id())])
    get_db().commit()

    return redirect('/admin/sendout?id=' + str(poll_id), code=303)

def setup_static_poll_index_html(poll_id, generated_filename="index.html"):
    name, options, choice_type, closes_on_date, description, max_choices = query_db_one(
            'select name, options, choice_type, closes_on_date, description, max_choices from polls where id=%s',
            [poll_id])

    description = description.strip().split('\n')
    if len(description) == 1 and description[0] == '':
        description = []

    poll_path = "/opt/sw/poll/" + str(poll_id)
    pathlib.Path(poll_path + "/results").mkdir(parents=True, exist_ok=True)
    with open(poll_path + "/" + generated_filename, 'w') as vote_index:
        vote_index.write(render_template('vote.html', name=name, options=options, choice_type=choice_type,
                                         closes_on_date=closes_on_date, description=description, max_choices=max_choices))

def activate_mailing(poll_id):
    setup_static_poll_index_html(poll_id)

    db_execute('update polls set mailing_active=true, planned_start_sending=null where id=%s', [poll_id])
    get_db().commit()

    print(f"sw_admin.py: activated mailing for poll with id {poll_id}")

@app.route('/admin/sendout/activatemailing', methods=['POST'])
@login_required
def admin_sendout_activatemailing_post():
    poll_id = int(request.args.get('id'))

    # This is not useless: make sure the current user has permissions to the poll
    row = query_db_one('select name from polls where id=%s and owner_user=%s', [poll_id, int(current_user.get_id())])
    if not row:
        return "Głosowanie nie istnieje", 400

    activate_mailing(poll_id)

    return redirect('/admin/sendout?id=' + str(poll_id), code=303)
    
@app.route('/admin/sendout/deactivatemailing', methods=['POST'])
@login_required
def admin_sendout_deactivatemailing_post():
    poll_id = int(request.args.get('id'))

    db_execute('update polls set mailing_active=false where id=%s and owner_user=%s', [poll_id, int(current_user.get_id())])
    get_db().commit()

    return redirect('/admin/sendout?id=' + str(poll_id), code=303)

def result_getter(poll_id):
    results_dict = {}
    results = subprocess.Popen(['/opt/sw/countvotes.sh', str(poll_id)], stdout=subprocess.PIPE).stdout.readlines()
    for result in results:
        result = result.decode('utf8').strip()
        option, count = result.split(' ', 2)
        results_dict[option] = int(count)
    return lambda i: 0 if f"option_{i}" not in results_dict else results_dict[f"option_{i}"]

@app.route('/admin/results', methods=['GET'])
@login_required
def admin_results():
    poll_id = int(request.args.get('id'))
    row = query_db_one('select name, options, \
                        json_array_length(possible_recipients), json_array_length(sending_out_to), json_array_length(sent_to) \
                        from polls where id=%s and owner_user=%s', [poll_id, int(current_user.get_id())])
    if not row:
        return "Głosowanie nie istnieje", 400
    name, options, possible_recipients_len, sending_out_to_len, sent_to_len = row

    get_result = result_getter(poll_id)

    voted_len = int(subprocess.Popen(['du', '--inodes', '-sS', f"/opt/sw/poll/{poll_id}/results/"], stdout=subprocess.PIPE).stdout.read().decode('utf8').split('\t')[0]) - 1

    results = []
    for i, option in enumerate(options):
        results.append({ 'score': get_result(i), 'name': option['name'], 'description': option['description'] })

    return render_template('results.html',
            name=name,
            possible_recipients_len=possible_recipients_len,
            sending_out_to_len=sending_out_to_len,
            sent_to_len=sent_to_len,
            voted_len=voted_len,
            results=results)

@app.route('/admin/peek', methods=['GET'])
@login_required
def look_at_poll():
    # This is not useless: make sure the current user has permissions to the poll
    poll_id = int(request.args.get('id'))
    row = query_db_one('select name from polls where id=%s and owner_user=%s', [poll_id, int(current_user.get_id())])
    if not row:
        return "Głosowanie nie istnieje", 400

    # Use the same logic as when activating mailing
    setup_static_poll_index_html(poll_id, 'index-peek.html')

    # TODO: this but better
    with open('/opt/sw/poll/' + str(poll_id) + '/index-peek.html', 'r') as index_peek:
        response = make_response(index_peek.read())
        response.headers['Content-Type'] = 'text/html'
        return response

@app.route('/admin/vote', methods=['GET', 'POST'])
@login_required
def admin_peek_vote():
    return redirect('/admin/polls', code=303)

if __name__ == '__main__':
    app.run()

# TODO: sqlite BEGIN EXCLUSIVE TRANSACTION
# TODO: noatime
