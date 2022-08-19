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

systemctl_enable() {
	local unit_name

	if [[ -d /run/systemd/system ]]; then
		if [[ $1 == --now ]]; then
			shift

			for unit_name; do
				if systemctl cat "$unit_name" | grep -q '^\[Install\]'; then
					if systemctl is-failed "$unit_name" >/dev/null; then
						# Przy re-provisioningu vagranta resetujemy status failed usługi który powoduje
						# że przy szybkim restartowaniu systemd nie włącza usługi spowrotem
						systemctl reset-failed "$unit_name"
					fi
					systemctl restart "$unit_name" || true
					systemctl enable --now "$unit_name" || true
				fi
			done
		else
			systemctl enable "$@"
		fi
	else
		if [[ $1 == --now ]]; then
			shift
		fi

		# Na dockerze/podmanie przy konfiguracji systemd nie jest dostępne - nie działa `systemctl enable`
		# można to obejść manualnie tworząc symlink w /etc/systemd/system/{target}.wants/{unit} do pliku z unitem
		for unit_name; do
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
		done
	fi
}

install-general-packages() {
	# Do an apt-get update only if there wasn't one in the last 3 hours (makes vagrant provision faster)
	if [ -z "$(find /var/cache/apt -maxdepth 0 -mmin -180)" ]; then
		apt-get update              
	fi

	apt-get install -y --no-install-recommends \
		git wget gnupg ca-certificates less procps sudo htop gunicorn gawk \
		python3 python3-flask python3-flask-login python3-psycopg2 python3-bcrypt python3-pip python3-tz python3-dateutil
	pip3 install furl
	for requirements_file in /opt/sw/*/requirements.txt; do
		pip3 install -r "$requirements_file"
	done
}

setup-vagrant-user() {
	# Allow login to root like to the vagrant user
	mkdir -p /root/.ssh
	cp /home/vagrant/.ssh/authorized_keys /root/.ssh/
	chown root:root /root/.ssh /root/.ssh/authorized_keys
	chmod 600 /root/.ssh /root/.ssh/authorized_keys
}

vagrant-windows-ntfs-workaround() {
	# Mount runtime directories as tmpfs so this works when ran on windows
	for dir in /opt/sw/{poll,v,v-archive,logs}; do
		mount -t tmpfs tmpfs "$dir" &
	done
}

setup-postgresql() {
	apt-get install -y --no-install-recommends postgresql postgresql-client
	systemctl_enable --now postgresql.service || true
}

setup-openresty() {
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

	apt-get install -y --no-install-recommends openresty-opm
	opm get 3scale/lua-resty-url

	systemctl_enable --now openresty.service || true
}

setup-postfix() {
	apt-get install -y --no-install-recommends mailutils postfix
	rm -f /etc/postfix/{main.cf,password}
	ln -s /opt/sw/sw-postfix/main.cf /etc/postfix/

	if ! [[ -f /etc/mailname ]]; then
		echo wybory.samorzad.pwr.edu.pl > /etc/mailname
	fi
	cp /opt/sw/sw-postfix/password /etc/postfix/
	postmap /etc/postfix/password # Can't do it on a symlink

	systemctl_enable --now postfix.service || true
}

create-runtime-dirs() {
	mkdir -p /opt/sw/{v,v-archive,poll,logs}
	chown -R www-data:www-data /opt/sw/{v,poll,logs}
}

copy-enable-unit-files-make-utility-scripts() {
	local services_unit_files=( /opt/sw/*/*.{service,timer,socket} )
	cp -t /etc/systemd/system/ -- "${services_unit_files[@]}" 
	if [[ -d /run/systemd/system ]]; then
		systemctl daemon-reload
	fi

	local sw_services=()
	local service_unit_file
	for service_unit_file in "${services_unit_files[@]}"; do
		sw_services+=( "$(basename "$service_unit_file")" )
	done
	systemctl_enable --now "${sw_services[@]}"

	make-script() {
		echo "#!/bin/sh
		$2" > "/usr/local/bin/$1"
		chmod +x "/usr/local/bin/$1"
	}

	local extra_services=()
	if ((enable_postgresql)); then extra_services+=(postgresql); fi
	if ((enable_postfix)); then extra_services+=(postfix); fi
	if ((enable_openresty)); then extra_services+=(openresty); fi

	make-script sw-logs "journalctl -e -b $(printf -- '-u %q"*" ' "${extra_services[@]}") -u 'sw-*' --lines=all --follow"
	make-script sw-status "systemctl status -l --no-pager --lines=100 $(printf '%q ' "${sw_services[@]}" "${extra_services[@]}")"
	make-script sw-restart "systemctl reset-failed $(printf '%q ' "${sw_services[@]}"); systemctl restart $(printf '%q ' "${sw_services[@]}" "${extra_services[@]}")"
}


case "${1: }" in
	--production)
		# Runs when setting up a Podman container from the master branch to prepare for production
		enable_postgresql=0
		enable_postfix=0
		enable_openresty=0
		vagrant_quirks=0
		;;
	--staging)
		# Runs when setting up a Podman container from a pull request branch for the live environment
		enable_postgresql=1
		enable_postfix=1
		enable_openresty=1
		vagrant_quirks=0
		;;
	--development)
		# Runs when setting up a development vagrant machine
		enable_postgresql=1
		enable_postfix=1
		enable_openresty=1
		vagrant_quirks=1
		;;
	*)
		set +x
		{
			echo "Usage: $0 [--production|--staging|--development]"
			echo ""
			echo "    --production  - setup a Podman container for production deployment"
			echo "                    (no mail server, database and http server)"
			echo ""
			echo "    --staging     - setup a Podman container for staging - automatic Pull"
			echo "                    Request deployments (include mail server, database and webserver)"
			echo ""
			echo "    --development - setup a local Vagrant box"
		} >> /dev/stderr
		exit 1
		;;
esac

install-general-packages
if ((vagrant_quirks)); then
	setup-vagrant-user
	vagrant-windows-ntfs-workaround
fi
if ((enable_postgresql)); then
	setup-postgresql
fi
if ((enable_openresty)); then
	setup-openresty
fi
if ((enable_postfix)); then
	setup-postfix
fi
copy-enable-unit-files-make-utility-scripts

wait
