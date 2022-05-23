#!/bin/bash
set -ex
for x in sw-*; do
	pushd "$x"
	grip --export
	gsed -i 's/<table>/<table border=1>/g' README.html
	echo '<style>.Box-header{display:none}</style>' >> README.html
	wkhtmltopdf --enable-local-file-access README.html README.pdf
	popd
done
