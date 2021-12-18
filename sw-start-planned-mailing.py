#!/usr/bin/env python3
import config
import sw_admin
import datetime
import time
import psycopg2

import psycopg2.extras
psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)
psycopg2.extensions.register_adapter(list, psycopg2.extras.Json)

def get_db():
    return psycopg2.connect(host=config.DATABASE_HOST, database=config.DATABASE_DB, user=config.DATABASE_USER, password=config.DATABASE_PW)

def query_db(query, args=()):
    conn = get_db()
    with conn, conn.cursor() as cursor:
        cursor.execute(query, args)
        return cursor.fetchall()

def main():
    while True:
        rows = query_db('set time zone \'Europe/Warsaw\'; select id, name from polls where planned_start_sending is not null and now() > planned_start_sending')
        for row in rows:
            poll_id, poll_name = row
            print(f'{datetime.datetime.now()} Activating mailing for poll "{poll_name}" (id={poll_id})')
            with sw_admin.app.app_context():
                sw_admin.activate_mailing(poll_id)
        time.sleep(30)

if __name__ == '__main__':
    main()
