#!/usr/bin/env python

import time
import LGI
from InterpoList import InterpoList
from Ganga.Utility import Config
from Ganga.Utility.logging import getLogger
from Ganga.Core.GangaThread import GangaThread

# Module configuration
config = Config.makeConfig('LGI', 'Leiden Grid Initiative Pilot job framework settings')
config.addOption('PilotDist', 'pilotdist/pilotjob.tar.gz',
	'Pilot job resource daemon tarball, fully configured for your applications and project server')
config.addOption('PilotScript', 'pilotdist/pilotrun.sh',
	'Script to run inside pilotjob, which unpacks the tarball and executes the resource daemon')

config.addOption('SchedMin', 1, 'Minimum number of pilotjobs at all times')
config.addOption('SchedMax', 5, 'Maximum number of pilotjobs')

config.addOption('Poll', 30, 'LGI thread polling time')
config.addOption('Update', 30, 'Pilot thread update time')
config.addOption('WaitNew', 50, 'If after this many seconds there are (still) more LGI jobs than pilotjobs, spawn new pilotjobs.')
config.addOption('WaitTerm', 300, 'Terminate pilotjob after seconds of idle time')

config.addOption('StatsInterval', 0, 'Statistics logging interval, or 0 for no statistics')
config.addOption('StatsHistory', 60*60, 'Seconds of statistics history to keep')
config.addOption('StatsFile', 'runhere/stats.csv', 'CSV file to log statistics to, or empty for no statistics')


def submitpilots(n=1, doTerm=True):
	"""Submit a number of pilotjobs"""
	if n <= 0: return
	from Ganga.GPI import Job, Executable, File
	j = Job()
	j.application = Executable(exe=File(config['PilotScript']), args=[])
	j.name = 'LGIpilot'
	if not doTerm: j.name = 'LGIpilot@'
	j.inputsandbox = [File(config['PilotDist'])]
	j.application.env['LGI_IS_PILOTJOB'] = '1'

	if doTerm:
		j.application.env['SCHED_WAIT_TERM'] = str(config['WaitTerm'])

	j.submit()
	for i in range(1, n-1):
		j = j.copy()
		j.submit()
	# returns last job
	return j


class PilotThread(GangaThread):
	def __init__(self):
		GangaThread.__init__(self, 'LGI_Pilot')
		self.log = getLogger('LGI.Pilot.Thread')

	def run(self):
		# wait for GPI to become ready (taken from GangaJEM)
		while not self.should_stop():
			try:        
				from Ganga.GPI import jobs
				break
			except: pass
			time.sleep(1)
		from Ganga.GPI import LGI

		# main pilotjob loop
		self.nlgijobs = nlgijobs = InterpoList()

		self.log.debug('Starting PilotThread main loop')
		while not self.should_stop():
			# update historical list of number pilotjobs
			now = time.time()

			# TODO truncate history to avoid memory hog
			nlgijobs[now] = LGI.resource.queued
			# first make sure baseline of non-terminating pilotjobs is present
			nbaseline = sum([len(jobs.select(status=s, name='LGIpilot@')) for s in ['running', 'submitted', 'submitting']])
			newbaseline = max(0, config['SchedMin']-nbaseline)
			if newbaseline > 0:
				self.log.info('%d/%d baseline pilotjobs present, submitting %d new', nbaseline, config['SchedMin'], newbaseline)
				submitpilots(newbaseline, False)
				# To avoid to keep submitting new pilot jobs when lgi jobs
				# are waiting, do as if each pilotjob takes care of one lgi
				# job. The max(nlgijobs[<some history>]) below does the rest.
				nlgijobs[now] -= newbaseline

			curpilots = sum([len(jobs.select(status=s)) for s in ['running', 'submitted', 'submitting']])

			# find out how many pilotjobs we want right now
			# main rule: #new_pilotjobs = #lgijobs_waiting/2
			# since number of lgijobs waiting is influenced by running
			# pilots, only submit half of jobs to approach it exponentially,
			# so as to avoid spawning too many pilots during job bursts.
			newpilots = int(max(nlgijobs[now-config['WaitNew']:])/2)

			newpilots = max(newpilots, 0)
			newpilots = min(newpilots, config['SchedMax']-config['SchedMin']-curpilots)

			# some debugging
			if self.log.isEnabledFor('DEBUG'):
				self.log.debug('%d - %d pending LGI jobs in the last %d s --> %d new pilots wanted, %d running'%(
					int(min(nlgijobs[now-config['WaitNew']:])), int(max(nlgijobs[now-config['WaitNew']:])),
					config['WaitNew'], newpilots, curpilots))

			# submit any auto-terminating pilotjobs
			if newpilots > 0:
				self.log.info('Submitting %d new pilotjobs'%(newpilots))
			submitpilots(newpilots)
			nlgijobs[now] -= newpilots

			# cleanup finished jobs
			jobs.select(status='finished').remove()
			jobs.select(status='completed').remove()
			
			# and wait for next iteration
			while not self.should_stop() and time.time()-now < config['Update']:
				time.sleep(1)

