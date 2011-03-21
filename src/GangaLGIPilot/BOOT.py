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

# convenience object to export to GPI
class LGI:
    resource = LGIResourceThread()
    pilot = PilotThread()
    stats = StatsThread()

# start threads
LGI.resource.start()
LGI.pilot.start()
LGI.stats.start()

# export to GPI
from Ganga.Runtime.GPIexport import exportToGPI
exportToGPI('LGI', LGI, 'Objects')

