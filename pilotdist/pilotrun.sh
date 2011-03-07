#!/bin/sh
#
# Run the LGI resource daemon
#

# extract LGI resource daemon and application
tar xzf pilotjob.tar.gz

# crazy fast polling times for development
LGI_OPTIONS='-ft 5 -st 10'

# setup auto-termination environment
LGI_ROOT="`pwd`"
LGI_RUNNING_STAMP="${LGI_ROOT}/running_stamp"
LGI_PID_FILE="${LGI_ROOT}/LGI.pid"
LGI_IS_PILOTJOB=1
date +%s >"${LGI_RUNNING_STAMP}"
export LGI_OPTIONS LGI_ROOT LGI_RUNNING_STAMP LGI_PID_FILE LGI_IS_PILOTJOB

env | grep '^LGI_\|^SCHED_'

if [ "${SCHED_WAIT_TERM}" ]; then
	echo "pilotjob: will terminate after ${SCHED_WAIT_TERM} seconds of idle-time"
	export SCHED_WAIT_TERM
else
	echo "pilotjob: will not terminate automatically"
fi

# run the daemon
"${LGI_ROOT}/rundaemon"
exit $?

