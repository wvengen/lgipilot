#!/bin/sh
if [ "${LGI_IS_PILOTJOB}" ]; then
	# keep track of non-idle time
	date "+%s" >"${LGI_RUNNING_STAMP}"
fi
