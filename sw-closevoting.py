from datetime import datetime
import os
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
        polls = query_db_all("""select id, closes_on_date from polls """)
        for poll in polls:
            poll_close_date = datetime.strptime(poll[1], "%Y-%m-%dT%H:%M:%S.000Z")
            now = datetime.now()
            if poll_close_date < now:
                os.unlink(f'/opt/sw/poll/{int(poll[0])}/index.html')
        time.sleep(60)


if __name__ == '__main__':
    main()
