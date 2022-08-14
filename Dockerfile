# Docker jest do użycia na produkcji - do developowania użyj vagranta!
# Bazowane na https://github.com/robertdebock/docker-debian-systemd

# Do uruchomienia (z powodu systemd) potrzebne jest włączone systemd na hoście, i podanie 
# do docker run argumentów: --tty --privileged --volume /sys/fs/cgroup:/sys/fs/cgroup:ro

# TODO: czy --tty jest potrzebne? w README.md repo docker-debian-systemd jest podane,
# ale może być tylko jako przykład - jednak pamiętam że gdzieś w internecie pisali o tym
# że jest potrzebne przy systemd

FROM debian:11


# TODO: to coś daje/ma sens? zaimportowane z https://github.com/robertdebock/docker-debian-systemd
ENV container docker
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
RUN /opt/sw/bootstrap.sh --prod

VOLUME [ "/sys/fs/cgroup" ]
CMD ["/lib/systemd/systemd"]
