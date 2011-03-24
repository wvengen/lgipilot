#
# Copyright (C) 2011 W. van Engen, Stichting FOM, The Netherlands
#
# This is free software; you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation.
#
# http://www.gnu.org/licenses/gpl.txt

'''LGI pilot job manager daemon script'''

import time
import Ganga.Runtime
from Ganga.GPI import LGI

# start LGI pilot job manager threads
LGI.resource.start()
LGI.pilot.start()
LGI.stats.start()

# and wait forever in batch mode
while not Ganga.Runtime._prog.interactive:
	time.sleep(60)

