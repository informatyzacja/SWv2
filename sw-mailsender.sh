#!/bin/sh
cd /opt/sw
export SOCKS_SERVER=127.0.0.1:1337
while true; do
	 socksify /opt/sw/sw-mailsender.py >> /opt/sw/logs/mailsender.log 2>> /opt/sw/logs/mailsender-error.log
	 sleep 10 || exit 1
done
