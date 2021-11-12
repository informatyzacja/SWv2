import config
import datetime
import os
import pytz
import psycopg2
import time

db = psycopg2.connect(host=config.DATABASE_HOST, database=config.DATABASE_DB, user=config.DATABASE_USER,
                      password=config.DATABASE_PW)


def query_db_all(query, args=()):
    with db, db.cursor() as cursor:
        cursor.execute(query, args)
        return cursor.fetchall()


def main():
    while True:
        polls = query_db_all("""select id, closes_on_date, closed from polls """)
        for poll in polls:
            poll_id, poll_close_date, poll_closed = poll
            now = datetime.datetime.now(tz=pytz.timezone("Europe/Warsaw"))
            now = now.replace(tzinfo=None)
            poll_id = int(poll_id)
            if poll_close_date < now:
                os.unlink(f'/opt/sw/poll/{poll_id}/index.html')
        time.sleep(60)


if __name__ == '__main__':
    main()
