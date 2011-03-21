#!/usr/bin/env python
#
# Copyright (C) 2011 W. van Engen, Stichting FOM, The Netherlands
#
# This is free software; you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation.
#
# http://www.gnu.org/licenses/gpl.txt

import os
import time
import LGI
from Ganga.Utility import Config
from Ganga.Utility.logging import getLogger
from Ganga.Core.GangaThread import GangaThread


class LGIResourceThread(GangaThread):
	def __init__(self):
		GangaThread.__init__(self, 'LGI_Resource')
		self.log = getLogger('LGI.Resource.Thread')
		config = Config.getConfig('LGI')
		if not os.path.exists(config['PilotDist']):
			self.log.error('cannot connect to LGI server: pilotjob tarball not found: '+config['PilotDist'])
		self.res = LGI.Resource(config['PilotDist'])
		# number of queued LGI jobs
		self.queued = None

	def run(self):
		# create connection
		self.log.info('Connecting to LGI project %s server %s'%(self.res._project, self.res._url))
		self.res.connect()
		self.queued = None
		config = Config.getConfig('LGI')

		# LGI update loop
		self.log.debug('Starting LGIResourceThread main loop')
		while not self.should_stop():
			now = time.time()

			try:
				work = [self._workForApp(app) for app in self.res.getApplications()]
				totalwork = sum(work)
				if self.log.isEnabledFor('DEBUG'):
					self.log.debug('LGI pending work: %s'%(dict(zip([str(x) for x in self.res.getApplications()], work))))
				if self.queued != totalwork:
					self.log.info('LGI jobs: %d waiting'%totalwork)
				self.queued = totalwork
			except Exception, e:
				self.log.warn(e)
		
			# and wait for next iteration
			while not self.should_stop() and time.time()-now < config['Poll']:
				time.sleep(1)

		# cleanup!
		self.res.close()


	def _workForApp(self, app):
		'''Return number of pending jobs for application'''
		# LGI project server 1.29 and later returns the total number of jobs
		# when limit=0, without locking any. Older LGI project servers always
		# report zero remaining work when limit=0.
		# Approach: first try with limit=0; if no jobs, try with default limit.
		nqueued = self.__workForApp2(app, 0)
		if nqueued > 0:
			return nqueued
		else:
			return self.__workForApp2(app, None)

	def __workForApp2(self, app, limit):
		resp = self.res.requestWork(app, limit)
		# error handling
		if not 'number_of_jobs' in resp:
			raise LGI.LGIException('Malformed LGI response: %s'%str(resp))
		# if any jobs locks were obtained, signoff to release them (for old project server)
		if resp['number_of_jobs']>0 and 'job' in resp and len(resp['job'])>0:
			self.res.signoff()
			self.res.signup()
		# return number of jobs
		return resp['number_of_jobs']

