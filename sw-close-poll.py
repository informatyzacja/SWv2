#!/usr/bin/env python3

import config
import datetime
import os
import pytz
import psycopg2
import time
import datetime
from pathlib import Path

db = psycopg2.connect(
        host=config.DATABASE_HOST,
        database=config.DATABASE_DB,
        user=config.DATABASE_USER,
        password=config.DATABASE_PW)

def query_db_all(query, args=()):
    with db, db.cursor() as cursor:
        cursor.execute(query, args)
        return cursor.fetchall()

# TODO: this is full of race conditions
# in practice that doesn't matter since there's always gonna be at most just one instance of this script running
# and nothing else really touches those files
def close_poll(poll_id, poll_name, poll_close_date):
    index_html = f'/opt/sw/poll/{poll_id}/index.html'
    index_disabled_html = f'/opt/sw/poll/{poll_id}/index-disabled.html'
    if not Path(index_html).exists():
        print(f'{datetime.datetime.now()} {index_html} does not exist - not marking as closed')
        return
    print(f'{datetime.datetime.now()} Getting rid of {index_html} for "{poll_name}" closing on {poll_close_date}')
    if Path(index_disabled_html).exists():
        os.unlink(index_disabled_html)
    os.rename(index_html, index_disabled_html)
    with db, db.cursor() as cursor:
        cursor.execute('update polls set mailing_active = false, closed = true where id = %s', (poll_id,))

def main():
    # todo: this could compare the date in postgres
    polls = query_db_all("select id, name, closes_on_date::timestamp without time zone from polls where closed = false")
    for poll in polls:
        poll_id, poll_name, poll_close_date = poll
        now = datetime.datetime.now(tz=pytz.timezone("Europe/Warsaw"))
        now = now.replace(tzinfo=None)
        poll_id = int(poll_id)
        if poll_close_date < now:
            close_poll(poll_id, poll_name, poll_close_date)

if __name__ == '__main__':
    main()
