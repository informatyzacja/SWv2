#!/usr/bin/env python3

import sys
import bcrypt
import psycopg2
import config

def get_hashed_password(plain_text_password):
    # Hash a password for the first time
    #   (Using bcrypt, the salt is saved into the hash itself)
    return bcrypt.hashpw(plain_text_password.encode('utf8'), bcrypt.gensalt()).decode('utf8')

def change(user, pw):
    db = psycopg2.connect(host=config.DATABASE_HOST, database=config.DATABASE_DB, user=config.DATABASE_USER, password=config.DATABASE_PW)
    with db, db.cursor() as cursor:
        hashed = get_hashed_password(pw)
        cursor.execute('update users set password_hash = %s where username = %s', (hashed, user))

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} [username] [password]")
        sys.exit(1)
    change(sys.argv[1], sys.argv[2])
