#!/bin/bash

#
# Skrypt ustawiający maszynę wirtualną wirtualną przez Vagranta przy `vagrant up`
# można go uruchamiać z shella `vagrant ssh`, aby przeładować wszystko - jest to
# przydatne przy modyfikacji plików dla systemd: .service, .timer i .socket
#

# Jest też wywoływany przy budowaniu kontenera Podmana na produkcję, wtedy
# z argumentem --prod

set -xeu
shopt -s nullglob

prod=0
if [[ $# -ge 1 && $1 == --prod ]]; then
	prod=1
fi

# Na dockerze/podmanie przy konfiguracji systemd nie jest dostępne - nie działa `systemctl enable`
# można to obejść manualnie tworząc symlink w /etc/systemd/system/{target}.wants/{unit} do pliku z unitem
systemctl_enable() {
	if [[ -d /run/systemd/system ]]; then
		systemctl enable "$@"
	else
		if [[ $1 == --now ]]; then
			shift
		fi

		local unit_name="$1"
		local unit_file="/etc/systemd/system/$unit_name"
		local wanted_by=$(< "$unit_file" sed 's/\s*#.*//' | awk -F'=' '/^\[.*\]$/{section=$0;next} section=="[Install]" { $1=""; print }')
		local target
		for target in $wanted_by; do
			local target_path="/etc/systemd/system/${target}.wants/"
			local symlink_path="$target_path/$unit_name"
			local symlink_target="/etc/systemd/system/$unit_name"
			mkdir -p "$target_path"
			ln -s "$symlink_target" "$symlink_path"
		done
	fi
}


if ! ((prod)); then
	# Allow login to root like to the vagrant user
	mkdir -p /root/.ssh
	cp /home/vagrant/.ssh/authorized_keys /root/.ssh/
	chown root:root /root/.ssh /root/.ssh/authorized_keys
	chmod 600 /root/.ssh /root/.ssh/authorized_keys
fi

# Do an apt-get update only if there wasn't one in the last 3 hours (makes vagrant provision faster)
if [ -z "$(find /var/cache/apt -maxdepth 0 -mmin -180)" ]; then
    apt-get update
fi

apt-get install -y --no-install-recommends \
    git wget gnupg ca-certificates less procps sudo mailutils htop gunicorn gawk \
    python3 python3-flask python3-flask-login python3-psycopg2 python3-bcrypt python3-pip python3-tz python3-dateutil

if ! ((prod)); then
    apt-get install -y --no-install-recommends postgresql postgresql-client
fi

# Install openresty if not already installed
if ! dpkg -l openresty &> /dev/null; then
	# there's only ubuntu and debian
	# nothing else exists
	if lsb_release -a | grep -i -q ubuntu; then
		wget -O - https://openresty.org/package/pubkey.gpg | sudo gpg --dearmor -o /usr/share/keyrings/openresty.gpg
		echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/openresty.gpg] http://openresty.org/package/ubuntu $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/openresty.list > /dev/null
		apt-get update
		apt-get -y install --no-install-recommends openresty
	else
		# debian
		wget -O - https://openresty.org/package/pubkey.gpg | apt-key add - \
			&& codename=`grep -Po 'VERSION="[0-9]+ \(\K[^)]+' /etc/os-release` \
			&& echo "deb http://openresty.org/package/debian $codename openresty" | tee /etc/apt/sources.list.d/openresty.list \
			&& apt-get update \
			&& apt-get -y install --no-install-recommends openresty
	fi
fi

unlink /etc/openresty/nginx.conf || true
ln -s /opt/sw/sw-openresty/nginx.conf /etc/openresty/nginx.conf

apt-get install -y openresty-opm
opm get 3scale/lua-resty-url
pip3 install furl

if ! ((prod)); then
	rm -f /etc/postfix/{main.cf,password}
	ln -s /opt/sw/sw-postfix/main.cf /etc/postfix/

	cp /opt/sw/sw-postfix/password /etc/postfix/
	postmap /etc/postfix/password # Can't do it on a symlink

	systemctl enable --now postgresql || true
fi

for requirements_file in /opt/sw/*/requirements.txt; do
    pip3 install -r "$requirements_file"
done

mkdir -p /opt/sw/{v,v-archive,poll,logs}
chown -R www-data:www-data /opt/sw/{v,poll,logs}

# Start up all systemd services

services_unit_files=( /opt/sw/*/*.{service,timer,socket} )

cp -t /etc/systemd/system/ -- "${services_unit_files[@]}"
if ! ((prod)); then
	systemctl daemon-reload
fi

extra_services=()
if ! ((prod)); then
	extra_services+=( openresty postfix )
fi

all_services=()
for service_unit_file in "${services_unit_files[@]}" "${extra_services[@]}"; do
    all_services+=( "$(basename "$service_unit_file")" )
done

if (( prod )); then
	for service_name in "${all_services[@]}"; do
        systemctl_enable "$service_name"
    done
else
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
fi

make-script() {
    echo "#!/bin/sh
    $2" > "/usr/local/bin/$1"
    chmod +x "/usr/local/bin/$1"
}

make-script sw-logs "journalctl -e -b $(printf -- '-u %q"*" ' "${extra_services[@]}") -u 'sw-*' --lines=all --follow"
make-script sw-status "systemctl status -l --no-pager --lines=100 $(printf '%q ' "${all_services[@]}")"
make-script sw-restart "systemctl reset-failed $(printf '%q ' "${all_services[@]}"); systemctl restart $(printf '%q ' "${all_services[@]}")"

if ! ((prod)); then
	# Mount runtime directories as tmpfs so this works when ran on windows
	for dir in /opt/sw/{poll,v,v-archive,logs}; do
		mount -t tmpfs tmpfs "$dir" &
	done
	wait # wait for this "&" and previous one - when enabling systemd services
fi

