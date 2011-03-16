# File: GangaLGIPilot/__init__.py

def getEnvironment( config = {} ):
    import PACKAGE
    PACKAGE.standardSetup()

def loadPlugins( config = {} ):
    import Lib.LGIResourceThread
    import Lib.PilotThread
    import Lib.StatsThread
    return None

