# File: GangaLGIPilot/BOOT.py
#
# Copyright (C) 2011 W. van Engen, Stichting FOM, The Netherlands
#
# This is free software; you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation.
#
# http://www.gnu.org/licenses/gpl.txt

from GangaLGIPilot.Lib.LGIResourceThread import LGIResourceThread
from GangaLGIPilot.Lib.PilotThread import PilotThread
from GangaLGIPilot.Lib.StatsThread import StatsThread

import os
from Ganga.Utility.Config import Config

# convenience object to export to GPI
class LGI:
    resource = LGIResourceThread()
    pilot = PilotThread()
    stats = StatsThread()
    
    # TODO following methods should move to separate file
    def pilot_cancel(cls):
        '''Cancel all pilot jobs; only works in daemon process'''
        from Ganga.GPI import jobs
        tocancel = filter(lambda j: j.status in ['submitted', 'running'], jobs)
        for j in tocancel: j.kill()
        return len(tocancel)
    pilot_cancel = classmethod(pilot_cancel)
    
    def getpid(cls):
        '''Return PID of daemon process, if any'''
        # make sure PID file exists
        pidfile = Config.getConfig('LGI')['PidFile']
        if not os.path.exists(pidfile):
            return None
        # get it
        f = open(pidfile, 'r')
        pid = int(f.read())
        f.close()
        # verify it's still running; if not, remove
        try:
            os.kill(pid, 0)
        except OSError:
            os.unlink(pidfile)
            return None
        # ok!
        return pid
    getpid = classmethod(getpid)

    def putpid(cls):
        '''Store current PID to file; should only be called in daemon process.'''
        if LGI.getpid() is not None:
            LGI.pilot.log.warning('daemon already running, not overwriting pid file')
            return False
        f = open(Config.getConfig('LGI')['PidFile'], 'w')
        f.write(str(os.getpid()))
        f.close()
        return True
    putpid = classmethod(putpid)    

    def delpid(cls):
        '''Remove current PID file; should only be called at end of daemon process.'''
        os.unlink(Config.getConfig('LGI')['PidFile'])
    delpid = classmethod(delpid)


# export to GPI
from Ganga.Runtime.GPIexport import exportToGPI
exportToGPI('LGI', LGI, 'Objects')

