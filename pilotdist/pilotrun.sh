#!/bin/sh
#
# LGI pilot job resource daemon run script
#   unpacks the pilot job tarball and sets up auto-termination environment 
#
# Copyright (C) 2011 W. van Engen, Stichting FOM, The Netherlands
#
# This is free software; you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation.
#
# http://www.gnu.org/licenses/gpl.txt

# extract LGI resource daemon and application
openssl md5 pilotjob.tar.gz | sed 's|^MD5.*=\s*||; s|^|:id:md5:pilotjob.tar.gz:|'
tar xzf pilotjob.tar.gz

# polling times
#   -ft is used when checking local script status, this can be fairly low
#         since ps is a cheap operation; gives fast small job interaction
#   -st is used when contacting the LGI project server; this should be low
#         when there are little pilotjobs and the job length is small,
#         otherwise is should be a in the order of minutes or longer.
LGI_OPTIONS='-ft 3 -st 20'

# auto-termination environment
#   SCHED_WAIT_TERM After this many seconds of not running a job, the resource
#        daemon on the grid will terminate itself. This is normally set by
#        lgipilot from lgipilot.ini's configuration option [LGI]WaitTerm.
#   SCHED_TERM_AFTER After this many seconds the resource daemon will terminate
#        itself (after any running job is finished). This is normally set by
#        lgipilot from lgipilot.ini's configuration option [LGI]MaxRuntime.
# When one of these variables is unset, the corresponding (termination) action
# does not take place. 
#                   
LGI_ROOT="`pwd`"
LGI_IS_PILOTJOB=1

export LGI_OPTIONS LGI_ROOT LGI_IS_PILOTJOB

# some logging
env | grep '^LGI_\|^SCHED_'

if [ "${SCHED_WAIT_TERM}" ]; then
	echo "pilotjob: will terminate after ${SCHED_WAIT_TERM} seconds of idle-time"
	export SCHED_WAIT_TERM
else
	echo "pilotjob: will not terminate automatically when idle"
fi

if [ "${SCHED_TERM_AFTER}" ]; then
	echo "pilotjob: will terminate after ${SCHED_TERM_AFTER} seconds of run-time"
	export SCHED_TERM_AFTER
else
	echo "pilotjob: will not terminate automatically after specified run-time"
fi

# run the daemon
"${LGI_ROOT}/rundaemon"
exit $?

