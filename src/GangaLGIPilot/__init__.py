# File: GangaLGIPilot/__init__.py
#
# Copyright (C) 2011 W. van Engen, Stichting FOM, The Netherlands
#
# This is free software; you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation.
#
# http://www.gnu.org/licenses/gpl.txt

def getEnvironment( config = {} ):
    import PACKAGE
    PACKAGE.standardSetup()

def loadPlugins( config = {} ):
    import Lib.LGIResourceThread
    import Lib.PilotThread
    import Lib.StatsThread
    return None

