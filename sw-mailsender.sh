#!/bin/bash
cd /opt/sw
export SOCKS_SERVER=127.0.0.1:1337
while true; do
	 socksify /opt/sw/sw-mailsender.py 2>&1 >> /opt/sw/logs/mailsender.log
	 sleep 10 || exit 1
done
