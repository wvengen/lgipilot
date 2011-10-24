%define name lgipilot
%define version_major 0
%define version_minor 2
%define commit ebd2c1d
%define release 1

%define version %{version_major}.%{version_minor}
%define source http://github.com/wvengen/lgipilot/tarball/lgipilot-%{version_major}-%{version_minor}
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
Provides: bundled(libcrypto.so.4(x86-32)) bundled(libssl.so.4(x86-32)) bundled(libcurl.so.3(x86-32))

%description
Daemon for running Leiden Grid Infrastructure (LGI) jobs on a grid (like gLite)
using pilot jobs. This eliminates the latency inherent in grids, and allows
users of LGI to use a grid without the need for grid certificates.

%prep
%setup -q -n wvengen-%{name}-%{commit}

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
cp lgipilot.ini %{buildroot}/%{etcdir}
sed -i 's|^#\(PilotDist\s*=\).*$|\1 %{vardir}/pilotjob.tar.gz|;
        s|^#\(PilotScript\s*=\).*$|\1 %{vardir}/pilotrun.sh|;
        s|^#\(StatsFile\s*=\).*$|\1 %{logdir}/lgipilot.stats|;
        s|^#\(PidFile\s*=\).*$|\1 %{rundir}/lgipilot.pid|;
        s|^#\(_logfile\s*=\).*$|\1 %{logdir}/lgipilot.log|;
        s|^#\(gangadir\s*=\).*$|\1 %{spooldir}|;
       ' %{buildroot}/%{etcdir}/lgipilot.ini
# documentation in prefix
mkdir -p %{buildroot}/%{docdir}
cp README %{buildroot}/%{docdir}/README.lgipilot
cp pilotdist/README.pilot %{buildroot}/%{docdir}/README.lgipilot.pilot
# pilotdist in var
mkdir -p %{buildroot}/%{vardir}
cp pilotdist/pilotrun.sh %{buildroot}/%{vardir}
cp pilotdist/pilottest.jdl %{buildroot}/%{vardir}
cp -R pilotdist/pilotjob %{buildroot}/%{vardir}
ln -sf %{docdir}/README.pilot %{buildroot}/%{vardir}/README.lgipilot.pilot
mkdir -p %{buildroot}/%{vardir}/pilotjob/certificates
mkdir -p %{buildroot}/%{spooldir}
# precompile python files (to avoid selinux issues and improve performance as non-root)
python -mcompileall %{buildroot}/%{sharedir}/src
python -O -mcompileall %{buildroot}/%{sharedir}/src
# startup script
mkdir -p %{buildroot}/%{_initrddir}
cat <<EOF >%{buildroot}/%{_initrddir}/lgipilot
#!/bin/sh
#
# lgipilot: script to start/stop the LGI pilot job manager
#
# chkconfig: 2345 55 25
# description: LGI pilot job manager
#

. %{_initrddir}/functions

start() {
	echo -n "Starting LGI pilot job manager: "
	daemon %{sbindir}/lgipilot --config=%{etcdir}/lgipilot.ini
	echo
}

stop() {
	echo -n "Stopping LGI pilot job manager: "
	killproc %{sbindir}/lgipilot
	echo
}

case "$1" in
start)  [ ! -f /var/run/lgipilot.pid ] && start ;;
stop)   [ -f /var/run/lgipilot.pid ] && stop ;;
status) status %{sbindir}/lgipilot ;;
*)      echo $"Usage: $0 {start|stop|restart|status}" ;;
esac
EOF
# logrotation is done by lgipilot

%files
%defattr(0444,root,root)
%{sharedir}/src
%attr(0755,-,-) %{sharedir}/lgipilot
%attr(0755,-,-) %{sbindir}/lgipilot
%{docdir}/README.lgipilot
%{docdir}/README.lgipilot.pilot
%{vardir}
%dir %{spooldir}
%attr(700,-,-) %{vardir}/pilotjob/certificates
%config %{etcdir}/lgipilot.ini
%attr(755,-,-) %{_initrddir}/lgipilot

%preun
if [ "$1" = "0" ]; then
	service lgipilot stop &>/dev/null
	chkconfig lgipilot off &>/dev/null
fi

# TODO restart daemon after upgrade using pre+post

%post
if [ "$1" = "1" ]; then
	echo "TODO: configuration message"
fi

%clean
rm -rf %{buildroot}

