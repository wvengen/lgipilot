#
# Copyright (C) 2011 W. van Engen, Stichting FOM, The Netherlands
#
# This is free software; you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation.
#
# http://www.gnu.org/licenses/gpl.txt

from Ganga.GPI import jobs

for job in jobs:
    id = job.backend.id
    if not id: id = '<no_id_yet>'
    print id, job.status
