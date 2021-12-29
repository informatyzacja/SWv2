#!/bin/sh
set -ex

cd /opt/sw/sw-database

sudo -u postgres psql -c "
    CREATE USER sw WITH PASSWORD 'pw';
    CREATE DATABASE sw WITH OWNER = sw;" || true

sudo -u postgres psql sw -c '
    drop table polls;
    drop table users;' || true

sudo -u postgres psql sw -c "$(cat schema.sql)"

#sudo -u postgres psql -c 'GRANT ALL PRIVILEGES ON polls TO sw;'
#sudo -u postgres psql -c 'GRANT ALL PRIVILEGES ON users TO sw;'
#sudo -u postgres psql -c 'GRANT ALL PRIVILEGES ON polls_id_seq TO sw;'
#sudo -u postgres psql -c 'GRANT ALL PRIVILEGES ON users_id_seq TO sw;'

sudo -u postgres psql sw -c '
    GRANT ALL PRIVILEGES ON polls TO sw;
    GRANT ALL PRIVILEGES ON users TO sw;
    GRANT ALL PRIVILEGES ON polls_id_seq TO sw;
    GRANT ALL PRIVILEGES ON users_id_seq TO sw;'

./sw-create-user.py admin haker7
