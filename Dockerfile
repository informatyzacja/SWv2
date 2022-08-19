# Dockerfile jest do użycia na produkcji/staging - do developowania 
# użyj vagranta!
#
# Do uruchomienia (z powodu wykorzystania systemd) kontener działa
# tylko na Podmanie, nie Dockerze

# Budowanie wersji na produkcję: podman build .
# Budowanie wersji na staging: podman build --build-arg SWV2_ENV=staging .

FROM debian:11

# Bazowane na https://github.com/robertdebock/docker-debian-systemd
ENV DEBIAN_FRONTEND noninteractive
RUN bash -c 'shopt -s nullglob && \
    apt-get update && \
    apt-get install -y systemd systemd-sysv && \
    rm -rf /tmp/* /var/tmp/* \
    /lib/systemd/system/multi-user.target.wants/* \
    /etc/systemd/system/*.wants/* \
    /lib/systemd/system/local-fs.target.wants/* \
    /lib/systemd/system/sockets.target.wants/*udev* \
    /lib/systemd/system/sockets.target.wants/*initctl* \
    /lib/systemd/system/sysinit.target.wants/systemd-tmpfiles-setup* \
    /lib/systemd/system/systemd-update-utmp*'

ADD . /opt/sw

ARG SWV2_ENV=production
RUN /opt/sw/bootstrap.sh --$SWV2_ENV

VOLUME [ "/sys/fs/cgroup" ]
CMD ["/lib/systemd/systemd"]
