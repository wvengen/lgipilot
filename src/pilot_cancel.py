#
# Copyright (C) 2011 W. van Engen, Stichting FOM, The Netherlands
#
# This is free software; you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation.
#
# http://www.gnu.org/licenses/gpl.txt

from Ganga.GPI import jobs

tocancel = filter(lambda j: j.status in ['submitting', 'submitted', 'running'], jobs)
if tocancel:
    for j in tocancel: j.kill()
else:
    print "No jobs to cancel"
