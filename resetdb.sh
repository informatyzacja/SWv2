#!/bin/sh
sudo -u postgres psql -c 'CREATE DATABASE sw WITH OWNER = sw;'

sudo -u postgres psql sw -c 'drop table polls'
sudo -u postgres psql sw -c 'drop table users'


sudo -u postgres psql sw -c "$(cat schema.sql)"

sudo -u postgres psql -c 'GRANT ALL PRIVILEGES ON polls TO sw;'
sudo -u postgres psql -c 'GRANT ALL PRIVILEGES ON users TO sw;'
sudo -u postgres psql -c 'GRANT ALL PRIVILEGES ON polls_id_seq TO sw;'
sudo -u postgres psql -c 'GRANT ALL PRIVILEGES ON users_id_seq TO sw;'

sudo -u postgres psql sw -c 'GRANT ALL PRIVILEGES ON polls TO sw;'
sudo -u postgres psql sw -c 'GRANT ALL PRIVILEGES ON users TO sw;'
sudo -u postgres psql sw -c 'GRANT ALL PRIVILEGES ON polls_id_seq TO sw;'
sudo -u postgres psql sw -c 'GRANT ALL PRIVILEGES ON users_id_seq TO sw;'

./sw-create-user.py admin passwords