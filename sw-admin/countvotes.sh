#!/bin/sh
find "/opt/sw/poll/$1/results/" -type f -exec tail -q -n1 '{}' '+' \
	| awk -F '&' '{delete voted_for; for(i=1;i<=NF;i+=1){split($i, a, "="); if(! voted_for[a[1]]) print a[1]; voted_for[a[1]]=1;}}' \
	| awk '/^option_[0-9][0-9]*$/ {count[$0] += 1} END {for(name in count){print name, count[name]}}'
