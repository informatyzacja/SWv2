#!/bin/bash

#
# Skrypt ustawiający maszynę wirtualną wirtualną przez Vagranta przy `vagrant up`
# można go uruchamiać z shella `vagrant ssh`, aby przeładować wszystko - jest to
# przydatne przy modyfikacji plików dla systemd: .service, .timer i .socket
#

set -xeu
shopt -s nullglob

# Allow login to root like to the vagrant user
mkdir -p /root/.ssh
cp /home/vagrant/.ssh/authorized_keys /root/.ssh/
chown root:root /root/.ssh /root/.ssh/authorized_keys
chmod 600 /root/.ssh /root/.ssh/authorized_keys

# Do an apt-get update only if there wasn't one in the last 3 hours (makes vagrant provision faster)
if [ -z "$(find /var/cache/apt -maxdepth 0 -mmin -180)" ]; then
    apt-get update              
fi

apt-get install -y --no-install-recommends \
    git wget gnupg ca-certificates less procps sudo mailutils htop gunicorn \
    python3 python3-flask python3-flask-login python3-psycopg2 python3-bcrypt python3-pip python3-tz python3-dateutil \
    postgresql postgresql-client

# Install openresty if not already installed
if ! dpkg -l openresty &> /dev/null; then
    wget -O - https://openresty.org/package/pubkey.gpg | apt-key add - \
	&& codename=`grep -Po 'VERSION="[0-9]+ \(\K[^)]+' /etc/os-release` \
	&& echo "deb http://openresty.org/package/debian $codename openresty" | tee /etc/apt/sources.list.d/openresty.list \
	&& apt-get update \
	&& apt-get -y install --no-install-recommends openresty
fi

unlink /etc/openresty/nginx.conf
ln -s /opt/sw/sw-openresty/nginx.conf /etc/openresty/nginx.conf

apt-get install -y openresty-opm
opm get 3scale/lua-resty-url
pip3 install furl

rm -f /etc/postfix/{main.cf,password}
ln -s /opt/sw/sw-postfix/main.cf /etc/postfix/

cp /opt/sw/sw-postfix/password /etc/postfix/
postmap /etc/postfix/password # Can't do it on a symlink

systemctl enable --now postgresql || true

for requirements_file in /opt/sw/*/requirements.txt; do
    pip3 install -r "$requirements_file"
done

mkdir -p /opt/sw/{v,v-archive,poll,logs}
chown -R www-data:www-data /opt/sw/{v,poll,logs}

# Start up all systemd services

services_unit_files=( /opt/sw/*/*.{service,timer,socket} )

cp -t /etc/systemd/system/ -- "${services_unit_files[@]}" 
systemctl daemon-reload

extra_services=( openresty postfix )

all_services=()
for service_unit_file in "${services_unit_files[@]}" "${extra_services[@]}"; do
    all_services+=( "$(basename "$service_unit_file")" )
done

for service_name in "${all_services[@]}"; do
    {
	if systemctl cat "$service_name" | grep -q '^\[Install\]'; then
	    if systemctl is-failed "$service_name" >/dev/null; then
		systemctl reset-failed "$service_name"
	    fi
	    systemctl restart "$service_name" || true
	    systemctl enable --now "$service_name" || true
	fi
    } &
done

make-script() {
    echo "#!/bin/sh
    $2" > "/usr/local/bin/$1"
    chmod +x "/usr/local/bin/$1"
}

make-script sw-logs "journalctl -e -b $(printf -- '-u %q"*" ' "${extra_services[@]}") -u 'sw-*' --lines=all --follow"
make-script sw-status "systemctl status -l --no-pager --lines=100 $(printf '%q ' "${all_services[@]}")"
make-script sw-restart "systemctl reset-failed $(printf '%q ' "${all_services[@]}"); systemctl restart $(printf '%q ' "${all_services[@]}")"

# Mount runtime directories as tmpfs so this works when ran on windows
for dir in /opt/sw/{poll,v,v-archive,logs}; do
  mount -t tmpfs tmpfs "$dir" &
done

wait
