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
tar xzf pilotjob.tar.gz

# crazy fast polling times for development
LGI_OPTIONS='-ft 5 -st 10'

# setup auto-termination environment
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

