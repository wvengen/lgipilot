import os, sys

from LGIResourceThread import LGIResourceThread
from PilotThread import PilotThread
from StatsThread import StatsThread


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

