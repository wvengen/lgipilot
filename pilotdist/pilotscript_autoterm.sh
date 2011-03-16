#!/bin/sh
if [ "${LGI_IS_PILOTJOB}" ]; then
	NOW=`date +%s`

	# kill daemon when idle time exceeds predefined value
	if [ -e "${LGI_RUNNING_STAMP}" -a "${SCHED_WAIT_TERM}" ]; then
		LASTRUNNING=`cat "${LGI_RUNNING_STAMP}"`
		DIFF=`expr "${NOW}" - "${LASTRUNNING}"`
		if [ ${DIFF} -ge ${SCHED_WAIT_TERM} ]; then
			echo "pilotjob: killing daemon after ${DIFF} seconds of idle-time"
			kill `cat ${LGI_PID_FILE}`
		fi
	fi

	# kill daemon when run-time exceeds predefined value
	if [ -e "${LGI_START_STAMP}" -a "${SCHED_TERM_AFTER}" ]; then
		START=`cat "${LGI_START_STAMP}"`
		DIFF=`expr "${NOW}" - "${START}"`
		if [ ${DIFF} -ge ${SCHED_TERM_AFTER} ]; then
			echo "pilotjob: killing daemon after ${DIFF} seconds of run-time"
			kill `cat ${LGI_PID_FILE}`
		fi
	fi
fi
