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
LGI_START_STAMP="${LGI_ROOT}/start_stamp"
LGI_PID_FILE="${LGI_ROOT}/LGI.pid"
LGI_CONFIG="${LGI_ROOT}/LGI.cfg"
LGI_IS_PILOTJOB=1
date +%s >"${LGI_RUNNING_STAMP}"
date +%s >"${LGI_START_STAMP}"
export LGI_OPTIONS LGI_CONFIG LGI_ROOT
export LGI_RUNNING_STAMP LGI_START_STAMP LGI_PID_FILE LGI_IS_PILOTJOB

env | grep '^LGI_\|^SCHED_'

PYTHON=`which python`
if [ ! "$PYTHON" ]; then
	# this shouldn't really happen since we use Ganga, which uses Python
	echo "pilotjob: no Python found, cannot setup auto-termination environment!"
elif [ ! -e "$LGI_CONFIG" ]; then
	# lgipilot also expects this (for the resource certificates, for example)
	# so this shouldn't happen either
	echo "pilotjob: no LGI config found, cannot setup auto-termination environment!"
else
	# modify LGI.cfg to hook into scripts
	#  each project/application combination needs its own script because
	#  the original script file has te be called at the end
	python <<-"EOF"
		import os
		import xml.dom.minidom
		def c(el, tag):
		  return el.getElementsByTagName(tag)
		def incfile(fout, filenamein):
		  fin = open(filenamein, 'rb')
		  while True:
		    data = fin.read(1024)
		    if not data: break
		    fout.write(data)
		  fin.close()
		def makescript(script, origbin, incscript):
		  f = open(script, 'wb')
		  # shell script that does extra calls, then executes original binary
		  f.write('#!/bin/sh -\n')
		  incfile(f, incscript) # extra script commands
		  f.write('[ -x "$0.real" ] || { while read line; do case "$line" in "exit # EOF") break;; esac done; cat >"$0.real"; chmod a+x "$0.real"; } <"$0"\n')
		  f.write('"./$0.real" $@\n')
		  f.write('exit # EOF\n')
		  incfile(f, origbin) # original binary/script
		  f.close()
		  os.chmod(script, 0755)
		cfg = os.getenv('LGI_CONFIG')
		doc = xml.dom.minidom.parse(cfg)
		for project in c(c(doc, 'resource')[0], 'project'):
		  nproj = int(project.getAttribute('number'))
		  for app in c(project, 'application'):
		    napp = int(app.getAttribute('number'))
		    el = c(app, 'check_system_limits_script')[0]
		    if not el.firstChild.wholeText.startswith('pilotscript_autoterm'):
		        script = 'pilotscript_autoterm-%02d-%02d.sh'%(nproj,napp)
		        makescript(script, el.firstChild.wholeText.strip(), 'pilotscript_autoterm.sh')
		        el.replaceChild(doc.createTextNode(script), el.firstChild)
		    el = c(app, 'job_check_running_script')[0]
		    if not el.firstChild.wholeText.startswith('pilotscript_touch'):
		        script = 'pilotscript_touch-%02d-%02d.sh'%(nproj,napp)
		        makescript(script, el.firstChild.wholeText.strip(), 'pilotscript_touch.sh')
		        el.replaceChild(doc.createTextNode(script), el.firstChild)
		f = open(cfg, 'w')
		# LGI does not process XML correctly :( workaround: writing documentElement
		# avoids the <?xml version="1.0"?> line
		doc.documentElement.writexml(f)
		f.close()
	EOF
	echo "pilotjob: updated LGI config for auto-termination"

	# a little logging and exporting of variables
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
		echo "pilotjob: will not terminate automatically after fixed run-time"
	fi
fi

# run the daemon
"${LGI_ROOT}/rundaemon"
exit $?

