from flask import Flask, request, jsonify, g, render_template, redirect
import sqlite3
import json
import dateutil.parser
import uuid
import os
app = Flask(__name__)



# setup g.db as sqlite ./database.db
DATABASE = 'database.db'
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
def query_db(query, args=()):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return rv
def query_db_one(query, args=()):
    cur = get_db().execute(query, args)
    rv = cur.fetchone()
    cur.close()
    return rv


def send_out_mail(voting_id, voting_name, voting_type, voting_choices, email):
    token = str(uuid.uuid4())
    get_db().execute('insert into tokens(token, voting_id) values(?, ?)', [token, voting_id])
    print("Mail about '{}' to '{}' - token '{}'".format(voting_name, email, token))

    with open('static/voting?token='+token, 'w') as cached_response:
        json.dump({
            'name': voting_name,
            'type': voting_type,
            'choices': voting_choices,
        }, cached_response)


# handled by nginx static/ cache
@app.route('/voting', methods=['GET'])
def voting_get():
    voting_id = query_db_one('select voting_id from tokens where token = ?', [request.args.get('token')])
    if not voting_id:
        return "Incorrect voting_id", 400
    voting_id = voting_id[0]

    res = query_db_one('select name, choice_type, options from votings where id=?', [voting_id])

    return jsonify({
            'name': res[0],
            'type': res[1],
            'choices': json.loads(res[2]),
        })

@app.route('/vote', methods=['POST'])
def vote_post():
    token = request.json['token']

    voting_id = query_db_one('select voting_id from tokens where token = ?', [token])
    if not voting_id:
        return "Incorrect voting_id", 400
    voting_id = voting_id[0]

    print(request.json)

    get_db().execute('delete from tokens where token=?', [token])
    get_db().commit()

    #os.unlink('static/voting?token=' + token)

    return ""


# management apis (those needing auth):

@app.route('/votings', methods=['GET'])
def votings_get():
    return jsonify(list({
            'id': voting[0],
            'name': voting[1],
            'choices': json.loads(voting[2]),
            'choiceType': voting[3],
            'visibility': voting[4],
            'closesOnDate': voting[5]
        } for voting in query_db('select id, name, options, choice_type, visibility, closes_on_date from votings')))


@app.route('/voting', methods=['PUT'])
def voting_put():
    # TODO: this is a PUT request - PUTs are idempotent so they are allowed to be repeated
    j = request.json
    cur = get_db().cursor()
    cur.execute('insert into votings(name, options, choice_type, visibility, possible_recipients, closes_on_date, sent_to) \
                    values(?,?,?,?,?,?,"[]");',
        [
            j['name'],
            json.dumps(j['options']),
            j['choiceType'],
            j['visibility'],
            json.dumps(j['recipients']),
            j['closesOnDate']
        ])
    rowid = cur.lastrowid
    get_db().commit()

    return jsonify({
        "votingId": rowid
    })

@app.route('/voting', methods=['DELETE'])
def voting_delete():
    voting_id = request.args.get('voting_id')
    get_db().execute('delete from votings where id=?', [voting_id])
    get_db().commit()
    return ""

@app.route('/schedule', methods=['GET'])
def schedule_get():
    voting_id = request.args.get('voting_id')
    return jsonify(list({
            'possibleRecipients': json.loads(row[0]),
            'sendingTo': [], # TODO: fetch from postfix
            'sentTo': json.loads(row[1])
        } for row in query_db('select possible_recipients, sent_to from votings where id=?', [voting_id])))


@app.route('/schedule', methods=['POST'])
def schedule_post():
    voting_id = request.json['votingId']
    to_send_out = request.json['scheduleToSendOut']

    row = query_db_one('select name, possible_recipients, sent_to, options, choice_type from votings where id = ?', [voting_id])
    if not row:
        return "Nonexistant voting", 400
    name, possible_recipients, sent_to, voting_choices, voting_type = row 

    possible_recipients = json.loads(possible_recipients)
    sent_to = json.loads(sent_to)

    for mail in to_send_out:
        if mail in sent_to:
            print("Not double sending to", mail)
            continue
        send_out_mail(voting_id, name, voting_type, voting_choices, mail)
        sent_to.append(mail)

    possible_recipients = [mail for mail in possible_recipients if mail not in to_send_out]

    get_db().execute('update votings set possible_recipients = ?, sent_to = ? where id = ?', [
        json.dumps(possible_recipients),
        json.dumps(sent_to),
        voting_id
    ])
    get_db().commit()

    return ""

@app.route('/scheduleAllNotScheduled', methods=['POST'])
def schedule_all_post():
    voting_id = request.json['votingId']

    row = query_db_one('select name, possible_recipients, sent_to, options, choice_type  from votings where id = ?', [voting_id])
    if not row:
        return "Nonexistant voting", 400
    name, possible_recipients, sent_to, voting_choices, voting_type = row 

    possible_recipients = json.loads(possible_recipients)
    sent_to = json.loads(sent_to)

    for mail in possible_recipients:
        if mail in sent_to:
            print("Not double sending to", mail)
            continue
        send_out_mail(voting_id, name, voting_type, voting_choices, mail)
        sent_to.append(mail)

    get_db().execute('update votings set possible_recipients = "[]", sent_to = ? where id = ?', [
        json.dumps(sent_to),
        voting_id
    ])
    get_db().commit()

    return ""

@app.route('/admin/polls', methods=['GET'])
def admin_polls():
    # TODO: access control
    polls = list({
            'id': voting[0],
            'name': voting[1],
            'choices': json.loads(voting[2]),
            'choiceType': voting[3],
            'visibility': voting[4],
            'closesOnDate': voting[5]
        } for voting in query_db('select id, name, options, choice_type, visibility, closes_on_date from votings'))
    return render_template('polls.html', polls=polls)

@app.route('/admin/addpoll', methods=['GET'])
def admin_addpoll():
    return render_template('addpoll.html')

@app.route('/admin/addpoll', methods=['POST'])
def admin_addpoll_post():
    cur = get_db().cursor()
    cur.execute('insert into votings(name, options, choice_type, visibility, possible_recipients, closes_on_date, sent_to) \
                    values(?,?,?,?,?,?,"[]");',
        [
            request.form['name'],
            json.dumps(request.form['options']),
            request.form['choiceType'],
            request.form['visibility'],
            json.dumps(request.form['recipients']),
            request.form['closesOnDate']
        ])
    #rowid = cur.lastrowid
    get_db().commit()

    return redirect('/admin/polls', code=303)
