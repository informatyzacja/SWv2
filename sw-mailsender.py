#!/usr/bin/env python3
import os
import uuid
import sqlite3
import json
import psycopg2
import config

db = psycopg2.connect(host=config.DATABASE_HOST, database=config.DATABASE_DB, user=config.DATABASE_USER, password=config.DATABASE_PW)

# use dicts and lists as json in postgres
import psycopg2.extras
psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)
psycopg2.extensions.register_adapter(list, psycopg2.extras.Json)

def query_db(query, args=()):                                                                                                              
    with db, db.cursor() as cursor:                                                                                                    
        cursor.execute(query, args)                                                                                                        
        return cursor.fetchall()                                                                                                           
def query_db_one(query, args=()):                                                                                                          
    with db, db.cursor() as cursor:                                                                                                    
        cursor.execute(query, args)                                                                                                        
        return cursor.fetchone()
def db_execute(query, args=()):
    with db, db.cursor() as cursor:
        cursor.execute(query, args)

def list_without(l1, l2):
    s = set(l2)
    return [el for el in l1 if el not in s]

def make_token(poll_id):
    token = str(uuid.uuid4())
    os.symlink("/opt/sw/poll/" + str(poll_id), "/opt/sw/v/" + token)
    return token

def make_link(poll_id):
    token = make_token(poll_id)
    return f"{config.BASE_URL}/v/{token}/"

def make_a_href(poll_id):
    link = make_link(poll_id)
    return f"<a href=\"{link}\">{link}</a>"

def add_to_sent_to(poll_id, email):
    # query sent_to again in case sending the email takes a long time somehow
    # yes it'll result in a double-send in case of something really weird happening
    # but it's better than resulting in not sending one email in case of a crash
    # in send_one_email()
    sent_to = query_db_one('select sent_to from polls where id=%s', [poll_id])[0]
    sent_to += [email]
    db_execute('update polls set sent_to=%s where id=%s', [sent_to, poll_id])

def send_email(address, subject, content):
    print(f"Email to {address} with subject \"{subject}\":\n{content}")

def send_one_email(poll_id, email_address, name, mail_template, closes_on_date):
    # todo: check if it's already sent in postfix (if that's possible)
    link = make_a_href(poll_id)
    mail = mail_template
    mail = mail.replace('{name}', name)
    mail = mail.replace('{date_to}', closes_on_date)
    mail = mail.replace('{link}', link)
    send_email(email_address, "System Wyborczy Samorządu Studenckiego Politechniki Wrocławskiej", mail)

def send_one_email_in_poll(poll):
    poll_id, name, sending_out_to, sent_to, mail_template, closes_on_date = poll
    left_to_send = list_without(sending_out_to, sent_to)
    if len(left_to_send) == 0:
        return

    sending_to = left_to_send[-1]
    send_one_email(poll_id, sending_to, name, mail_template, closes_on_date)
    add_to_sent_to(poll_id, sending_to)

def main():
    polls = query_db('select id, name, sending_out_to, sent_to, mail_template, closes_on_date \
                      from polls \
                      where mailing_active and sending_out_to::json::text != sent_to::json::text')

    for poll in polls:
        send_one_email_in_poll(poll)

if __name__ == '__main__':
    main()
