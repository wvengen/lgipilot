%define name lgipilot
%define version_major 0
%define version_minor 2
%define release 1

%define version %{version_major}.%{version_minor}
%define source http://github.com/wvengen/lgipilot/tarball/%{name}-%{version_major}-%{version_minor}
%define url http://github.com/wvengen/lgipilot

# XXX installing packages in /usr/local is evil, but LGI does that as well
%define prefix /usr/local/LGI
%define sbindir %{prefix}/sbin
%define sharedir %{prefix}/lgipilot
%define docdir %{prefix}/docs
%define etcdir %{_sysconfdir}
%define vardir %{_localstatedir}/local/lgipilot
%define logdir %{_localstatedir}/log
%define spooldir %{_localstatedir}/spool/lgipilot
%define rundir %{_localstatedir}/run

%define rungroup lgi
%define runuser lgipilot

# package provides 32bit binaries that run on a gLite grid
%global _binaries_in_noarch_packages_terminate_build 0
%{?filter_setup:
%filter_provides_in %{vardir}
%filter_requires_in %{vardir}
%filter_setup
}

Summary: Leiden Grid Infrastructure pilotjob manager
Name: %{name}
Version: %{version}
Release: %{release}%{?dist}
License: GPLv3
Group: Applications/Interface
Distribution: rhel
Source: %{source}
URL: %{url}
Vendor: Stichting FOM / Nikhef
Packager: W. van Engen <wvengen+lgi@nikhef.nl>
BuildArch: noarch
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-build-%(%{__id_u} -n)
Prefix: %{prefix}
Requires: /bin/sh, /usr/bin/env, /usr/bin/python
Requires(pre): shadow-utils
Provides: bundled(libcrypto.so.4(x86-32)) bundled(libssl.so.4(x86-32)) bundled(libcurl.so.3(x86-32))

%description
Daemon for running Leiden Grid Infrastructure (LGI) jobs on a grid (like gLite)
using pilot jobs. This eliminates the latency inherent in grids, and allows
users of LGI to use a grid without the need for grid certificates.

%prep
# github serves directory name with commit hash; we want to work without it
%setup -q -c %{name}-%{version}
mv wvengen-%{name}-*/* wvengen-%{name}-*/.[a-zA-Z0-9]* .
rmdir wvengen-%{name}-*

%build
# nothing to do

%install
# copy sources to sharedir (when there's a proper setup.py this can change)
mkdir -p %{buildroot}/%{sharedir}
cp lgipilot %{buildroot}/%{sharedir}
cp -R src %{buildroot}/%{sharedir}
# symlink to share, so dirname(realpath($0)) works to find the sources
mkdir -p %{buildroot}/%{sbindir}
ln -sf %{sharedir}/lgipilot %{buildroot}/%{sbindir}
# configuration
mkdir -p %{buildroot}/%{etcdir}
sed 's|^#\?\(PilotDist\s*=\).*$|\1 %{vardir}/pilotjob.tar.gz|;
     s|^#\?\(PilotScript\s*=\).*$|\1 %{vardir}/pilotrun.sh|;
     s|^#\?\(StatsFile\s*=\).*$|\1 %{logdir}/lgipilot.stats|;
     s|^#\?\(PidFile\s*=\).*$|\1 %{rundir}/lgipilot.pid|;
     s|^#\?\(_logfile\s*=\).*$|\1 %{logdir}/lgipilot.log|;
     s|^#\?\(gangadir\s*=\).*$|\1 %{spooldir}|;
     ' <lgipilot.ini >%{buildroot}/%{etcdir}/lgipilot.ini
# documentation in prefix
mkdir -p %{buildroot}/%{docdir}
cp README %{buildroot}/%{docdir}/README.lgipilot
cp pilotdist/README.pilot %{buildroot}/%{docdir}/README.lgipilot.pilot
# pilotdist in var
mkdir -p %{buildroot}/%{vardir}
cp pilotdist/pilotrun.sh %{buildroot}/%{vardir}
cp pilotdist/pilottest.jdl %{buildroot}/%{vardir}
cp -R pilotdist/pilotjob %{buildroot}/%{vardir}
ln -sf %{docdir}/README.lgipilot.pilot %{buildroot}/%{vardir}/README.pilot
mkdir -p %{buildroot}/%{vardir}/pilotjob/certificates || true
mkdir -p %{buildroot}/%{spooldir}
# workaround for pre-config logging
ln -s %{logdir}/lgipilot.log %{buildroot}/%{vardir}/.ganga.log
# precompile python files (to avoid selinux issues and improve performance as non-root)
python -mcompileall %{buildroot}/%{sharedir}/src
python -O -mcompileall %{buildroot}/%{sharedir}/src
# startup script
mkdir -p %{buildroot}/%{_initrddir}
cat <<'EOF' >%{buildroot}/%{_initrddir}/lgipilot
#!/bin/sh
#
# lgipilot: script to start/stop the LGI pilot job manager
#
# chkconfig: 2345 55 25
# description: LGI pilot job manager
#

. %{_initrddir}/functions

LGIPILOT=%{sbindir}/lgipilot
PIDFILE=%{rundir}/lgipilot.pid
LOGFILE=%{logdir}/lgipilot.log
LOCKFILE=/var/lock/subsys/lgipilot

start() {
	echo -n "Starting LGI pilot job manager: "
	touch ${LOGFILE} && chown %{runuser}:%{rungroup} ${LOGFILE} # make sure logging will work
	daemon --user %{runuser} --pidfile ${PIDFILE} ${LGIPILOT} --config=%{etcdir}/lgipilot.ini
	RETVAL=$?
	echo
	[ $RETVAL -eq 0 ] && touch ${LOCKFILE}
	return $RETVAL
}

stop() {
	echo -n "Stopping LGI pilot job manager: "
	killproc -p ${PIDFILE} ${LGIPILOT}
	RETVAL=$?
	rm -f ${PIDFILE}
	echo
	[ $RETVAL -eq 0 ] && rm -f ${LOCKFILE}
	return $RETVAL
}

case "$1" in
start)       start ;;
stop)        stop ;;
status)      status ${LGIPILOT} ;;
restart)     stop; start ;;
condrestart) [ -f ${LOCKFILE} ] && restart ;;
reload)      [ -f ${LOCKFILE} ] && kill -USR1 `cat ${PIDFILE}` ;;
*)           echo "Usage: $0 {start|stop|reload|restart|condrestart|status}"; exit 1 ;;
esac

exit $?
EOF
# logrotation is done by lgipilot

%files
%{sharedir}
%attr(0755,-,-) %{sbindir}/lgipilot
%doc %{docdir}/README.lgipilot
%doc %{docdir}/README.lgipilot.pilot
%{vardir}
%attr(700,-,-) %{vardir}/pilotjob/certificates
#%ghost %{vardir}/pilotjob.tar.gz
%attr(750,lgipilot,lgi) %dir %{spooldir}
%config %{etcdir}/lgipilot.ini
%attr(755,-,-) %{_initrddir}/lgipilot

%pre
getent group %{rungroup} >/dev/null || groupadd -r %{rungroup}
getent passwd %{runuser} >/dev/null || \
	useradd -r -g %{rungroup} -d %{vardir} -s /sbin/nologin \
	-c "LGI pilot job manager" %{runuser}
exit 0

%preun
if [ $1 -eq 0 ]; then
	service lgipilot stop &>/dev/null
	chkconfig --del lgipilot &>/dev/null
fi

# TODO restart daemon after upgrade using pre+post

%post
if [ $1 -eq 1 ]; then
	cat <<-EOM
	The LGI pilot job manager has been installed on this machine.

	Before it can be used, please make sure that
	 * The LGI resource key and certificates are available in the files
	     %{vardir}/pilotjob/certificates/resource.crt
	     %{vardir}/pilotjob/certificates/resource.key
	 * The LGI CA certificate is present in the file
	     %{vardir}/pilotjob/certificates/LGI+CA.crt
	 * The LGI project server is configured in the file
	     %{vardir}/pilotjob/LGI.cfg
	 * You have ran create_package from the same directory.
	 * The resource certificate is inserted into the LGI project server database.
	 * The grid or batch system client tools used (default gLite) are installed.
	 * The user %{runuser} has a valid proxy certificate (when needed)
	Please see %{docdir} for more information.

	Start the daemon with 'service lgipilot start'.
	To survive a reboot, use 'chkconfig lgipilot on'.
	EOM
fi

%clean
rm -rf %{buildroot}

