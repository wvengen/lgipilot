#!/usr/bin/env python


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
					self.log.info('%d LGI jobs waiting'%totalwork)
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
		# TODO check we have at least LGI project server version 1.29, which
		# supports receiving limit=0 to return the number of queued jobs
		# (instead of just 0).
		resp = self.res.requestWork(app, limit=0)
		# error handling
		if 'error' in resp:
			raise LGI.LGIException('LGI error %d: %s'%(resp['error']['number'], resp['error']['message']))
		if not 'number_of_jobs' in resp:
			raise LGI.LGIException('Malformed LGI response: %s'%str(resp))
		# we can't get jobs back since limit=0; do check anyway
		if resp['number_of_jobs']>0 and 'job' in resp and len(resp['job'])>0:
			raise LGI.LGIException('Unexpected LGI response: limit=0 and number_of_jobs=%d'%len(resp['job']))
		# return number of jobs
		return resp['number_of_jobs']

