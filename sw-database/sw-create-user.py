#!/usr/bin/env python3

import sys
import bcrypt
import psycopg2

sys.path.append('..') # for ../config.py
import config

def get_hashed_password(plain_text_password):
    # Hash a password for the first time
    #   (Using bcrypt, the salt is saved into the hash itself)
    return bcrypt.hashpw(plain_text_password.encode('utf8'), bcrypt.gensalt()).decode('utf8')

def add(user, pw):
    db = psycopg2.connect(host=config.DATABASE_HOST, database=config.DATABASE_DB, user=config.DATABASE_USER, password=config.DATABASE_PW)
    with db, db.cursor() as cursor:
        hashed = get_hashed_password(pw)
        cursor.execute('insert into users(username, password_hash) values(%s, %s)', (user, hashed))

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} [username] [password]")
        sys.exit(1)
    add(sys.argv[1], sys.argv[2])
