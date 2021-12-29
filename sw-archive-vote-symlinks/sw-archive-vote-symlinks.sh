#!/bin/bash
mkdir -p /opt/sw/v-archive
find /opt/sw/v/ -mindepth 1 -maxdepth 1 \
    | gawk '@load "filefuncs"; { if(stat($0 "/index.html", fstat) != 0) print $0; }' \
    | xargs --no-run-if-empty -d$'\n' mv -v -t /opt/sw/v-archive/ --
