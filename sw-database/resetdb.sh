#!/bin/sh
set -ex

cd /opt/sw/sw-database

sudo -u postgres psql -c "DROP DATABASE sw;" || true
sudo -u postgres psql -c "CREATE USER sw WITH PASSWORD 'pw';" || true
sudo -u postgres psql -c "CREATE DATABASE sw WITH OWNER = sw;"

sudo -u postgres psql sw -c "$(cat schema.sql)"

sudo -u postgres psql sw -c '
    GRANT ALL PRIVILEGES ON polls TO sw;
    GRANT ALL PRIVILEGES ON users TO sw;
    GRANT ALL PRIVILEGES ON polls_id_seq TO sw;
    GRANT ALL PRIVILEGES ON users_id_seq TO sw;'

./sw-create-user.py admin haker7
