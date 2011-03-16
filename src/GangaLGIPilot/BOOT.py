# File: GangaLGIPilot/BOOT.py

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

