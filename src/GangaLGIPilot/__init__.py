    
def getEnvironment( config = {} ):
    import PACKAGE
    PACKAGE.standardSetup()

def loadPlugins( config = {} ):
    import sys
    import LGIResourceThread
    import PilotThread
    import StatsThread

