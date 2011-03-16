################################################################################
# GangaLGIPilot plugin: external packages definition
################################################################################

"""
Refer to Ganga/PACKAGE.py for details on the purpose of this module.
"""

_external_packages = {
    # none
}

from Ganga.Utility.Setup import PackageSetup
setup = PackageSetup(_external_packages)

def standardSetup(setup=setup):
    import Ganga.Utility.Setup
    pass

