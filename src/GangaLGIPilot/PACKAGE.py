################################################################################
# GangaLGIPilot plugin: external packages definition
################################################################################
#
# Copyright (C) 2011 W. van Engen, Stichting FOM, The Netherlands
#
# This is free software; you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation.
#
# http://www.gnu.org/licenses/gpl.txt

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

