#!/usr/bin/env python


import time
import LGI
from Ganga.Utility import Config
from Ganga.Utility.logging import getLogger
from Ganga.Core.GangaThread import GangaThread


class StatsThread(GangaThread):
	def __init__(self):
		GangaThread.__init__(self, 'LGI_Stats')
		self.log = getLogger('LGI.Stats.Thread')

	def run(self):
		config = Config.getConfig('LGI')
		if config['StatsInterval'] == 0: return
		if not config['StatsFile']: return

		# wait for GPI to become ready (taken from GangaJEM)
		while not self.should_stop():
			try:        
				from Ganga.GPI import jobs
				break
			except: pass
			time.sleep(1)
		from Ganga.GPI import LGI

		# LGI update loop
		self.log.debug('Starting LGI StatsThread main loop')
		self.data = []
		self._writeStats(self.data, config['StatsFile'])
		while not self.should_stop():
			now = time.time()

			try:
				# add new line of data
				lgiQueued = LGI.resource.queued
				if lgiQueued is None: lgiQueued = 0
				lgiRunning = 0 # TODO
				pilotQueued = sum([len(jobs.select(status=s)) for s in ['submitted', 'submitting']])
				pilotRunning = len(jobs.select(status='running'))
				self.data.append([
					int(now), 
					lgiQueued + lgiRunning,
					lgiRunning,
					pilotQueued + pilotRunning,
					pilotRunning
				])
				# trash too old lines
				self.data = filter(lambda x: now-x[0] < config['StatsHistory'], self.data)
				# write data
				self._writeStats(self.data, config['StatsFile'])
			except Exception, e:
				self.log.warn(e)
		
			# and wait for next iteration
			while not self.should_stop() and time.time()-now < config['StatsInterval']:
				time.sleep(1)

	def _writeStats(self, data, file):
		'''Write statistics to file'''
		f = open(file, 'w')
		f.write(', '.join(['# time', 'lgijobs_all', 'lgijobs_running', 'pilotjobs_all', 'pilotjobs_running'])+'\n')
		for l in data:
			f.write(', '.join(map(str, l))+'\n')
		f.close()

