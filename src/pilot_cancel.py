#
# Copyright (C) 2011 W. van Engen, Stichting FOM, The Netherlands
#
# This is free software; you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation.
#
# http://www.gnu.org/licenses/gpl.txt

'''LGI pilot job manager cancel script'''

import os
import signal
from Ganga.GPI import LGI

# different behaviour if daemon is running or not
pid = LGI.getpid()
if pid is not None:
    # send signal to daemon
    os.kill(pid, signal.SIGUSR2)
    print "Signalled daemon with PID %d"%(pid)
else:
    # kill directly
    if LGI.pilot_cancel() == 0:
        print "No jobs to cancel"
