from common import *
from TaskApplication import ExecutableTask, taskApp
from Ganga.GPIDev.Lib.Job.Job import JobError
from Ganga.GPIDev.Lib.Registry.JobRegistry import JobRegistrySlice, JobRegistrySliceProxy
from Ganga.Core.exceptions import ApplicationConfigurationError
from Ganga.GPIDev.Base.Proxy import addProxy, stripProxy
import time

class IUnit(GangaObject):
   _schema = Schema(Version(1,0), {
        'status'         : SimpleItem(defvalue='new', protected=1, copyable=0, doc='Status - running, pause or completed', typelist=["str"]),
        'name'           : SimpleItem(defvalue='Simple Unit', doc='Name of the unit (cosmetic)', typelist=["str"]),
        'inputdata'      : ComponentItem('datasets', defvalue=None, optional=1, load_default=False,doc='Input dataset'),
        'outputdata'     : ComponentItem('datasets', defvalue=None, optional=1, load_default=False,doc='Output dataset'),
        'active'         : SimpleItem(defvalue=False, hidden=1,doc='Is this unit active'),
        'active_job_ids' : SimpleItem(defvalue=[], typelist=['int'], sequence=1, hidden=1,doc='Active job ids associated with this unit'),
        'prev_job_ids' : SimpleItem(defvalue=[], typelist=['int'], sequence=1,  hidden=1,doc='Previous job ids associated with this unit'),
        'minor_resub_count' : SimpleItem(defvalue=0, hidden=1,doc='Number of minor resubmits'),
        'major_resub_count' : SimpleItem(defvalue=0, hidden=1,doc='Number of major resubmits'),
        'req_units' : SimpleItem(defvalue=[], typelist=['str'], sequence=1, hidden=1,doc='List of units that must complete for this to start (format TRF_ID:UNIT_ID)'),
        'start_time' : SimpleItem(defvalue=0, hidden=1,doc='Start time for this unit. Allows a delay to be put in'),
        'copy_output' : ComponentItem('datasets', defvalue=None, load_default=0,optional=1, doc='The dataset to copy the output of this unit to, e.g. Grid dataset -> Local Dataset'),
        'merger'    : ComponentItem('mergers', defvalue=None, load_default=0,optional=1, doc='Merger to be run after this unit completes.'),
    })

   _category = 'units'
   _name = 'IUnit'
   _exportmethods = [  ]
   
## Special methods:
   def __init__(self):
       super(IUnit,self).__init__()
       self.updateStatus("new")
   
   def _readonly(self):
       """A unit is read-only if the status is not new."""
       if self.status == "new":
           return 0
       return 1
   
   def validate(self):
       """Validate that this unit is OK and set it to active"""
       self.active = True
       return True

   def getID(self):
      """Get the ID of this unit within the transform"""
      trf = self._getParent()
      if not trf:
         raise ApplicationConfigurationError(None, "This unit has not been associated with a transform and so there is no ID available")
      return trf.units.index(self)
      
   def updateStatus(self, status):
      """Update status hook"""
      self.status = status

   def createNewJob(self):
      """Create any jobs required for this unit"""
      pass

   def checkCompleted(self, job):
      """Check if this unit is complete"""
      if job.status == "completed":
         return True
      else:
         return False

   def checkForSubmission(self):
      """Check if this unit should submit a job"""

      # check the delay
      if time.time() < self.start_time:
         return False

      # check if we already have a job
      if len(self.active_job_ids) == 0:
         return True
      else:
         return False
      
   def checkMajorResubmit(self, job):
      """check if this job needs to be fully rebrokered or not"""
      pass
   
   def majorResubmit(self, job):
      """perform a mjor resubmit/rebroker"""
      self.prev_job_ids.append(job.id)
      self.active_job_ids.remove(job.id)

   def minorResubmit(self, job):
      """perform just a minor resubmit"""
      job.resubmit()
      
   def update(self):
      """Update the unit and (re)submit jobs as required"""
      #logger.warning("Entered Unit %d update function..." % self.getID())

      # if we're complete, then just return
      if self.status == "completed" or not self.active:
         return 0

      # check if submission is needed
      task = self._getParent()._getParent()
      trf = self._getParent()
      maxsub = task.n_tosub()

      # check parent unit(s)
      req_ok = True
      for req in self.req_units:
         req_trf_id = int( req.split(":")[0] )
         req_unit_id = int( req.split(":")[1] )

         if task.transforms[req_trf_id].units[req_unit_id].status != "completed":
            req_ok = False
            break

      # set the start time if not already set
      if len(self.req_units) > 0 and req_ok and self.start_time == 0:
         self.start_time = time.time() + trf.chain_delay * 60 - 1
         
      if req_ok and self.checkForSubmission() and maxsub > 0:

         # create job and submit
         j = self.createNewJob()
         j.name = "T%i:%i U%i" % (task.id, trf.getID(), self.getID())

         try:
            j.submit()
         except:
            logger.error("Couldn't submit the job. Deactivating unit.")
            self.prev_job_ids.append(j.id)
            self.active = False
            trf._setDirty()  # ensure everything's saved

            # add a delay in to make sure the trf repo is updated
            for i in range(0, 100):
               if not trf._dirty:
                  break
               time.sleep(0.1)
               
            return 1

         self.active_job_ids.append(j.id)
         self.updateStatus("running")
         trf._setDirty()  # ensure everything's saved

         # add a delay in to make sure the trf repo is updated
         for i in range(0, 100):
            if not trf._dirty:
               break
            time.sleep(0.1)
            
         return 1

      # update any active jobs
      for jid in self.active_job_ids:

         # we have an active job so see if this job is OK and resubmit if not
         job = GPI.jobs(jid)         
         task = self._getParent()._getParent()
         trf = self._getParent()
                           
         if job.status == "completed":
            
            # check if actually completed
            if not self.checkCompleted(job):
               return 0
               
            # check for DS copy
            if trf.unit_copy_output:
               if not self.copy_output:
                  trf.createUnitCopyOutputDS(self.getID())

               if not self.copyOutput():
                  return 0
            
            # check for merger
            if trf.unit_merger:
               if not self.merger:
                  self.merger = trf.createUnitMerger(self.getID())

               if not self.merge():
                  return 0
               
            # all good so mark unit as completed
            self.updateStatus("completed")
            
         elif job.status == "failed" or job.status == "killed":
               
            # check for too many resubs
            if self.minor_resub_count + self.major_resub_count > trf.run_limit-1:
               logger.error("Too many resubmits (%i). Deactivating unit." % (self.minor_resub_count + self.major_resub_count))
               self.active = False
               return 0

            rebroker = False
            
            if self.minor_resub_count > trf.minor_run_limit-1:
               if self._getParent().rebroker_on_job_fail:
                  rebroker = True
               else:
                  logger.error("Too many minor resubmits (%i). Deactivating unit." % self.minor_resub_count)
                  self.active = False
                  return 0
               
            if self.major_resub_count > trf.major_run_limit-1:
               logger.error("Too many major resubmits (%i). Deactivating unit." % self.major_resub_count)
               self.active = False
               return 0
            
            # check the type of resubmit
            if rebroker or self.checkMajorResubmit(job):
               
               self.major_resub_count += 1
               self.minor_resub_count = 0
               
               try:
                  self.majorResubmit(job)
               except:
                  logger.error("Couldn't resubmit the job. Deactivating unit.")
                  self.active = False

               # break the loop now because we've probably changed the active jobs list           
               return 1
            else:
               self.minor_resub_count += 1
               try:
                  self.minorResubmit(job)
               except:
                  logger.error("Couldn't resubmit the job. Deactivating unit.")
                  self.active = False
                  return 1


   def reset(self):
      """Reset the unit completely"""
      self.minor_resub_count = 0
      self.major_resub_count = 0
      if len(self.active_job_ids) > 0:
         self.prev_job_ids += self.active_job_ids
      self.active_job_ids = []

      self.active = True
      self.updateStatus("running")
      
   # Info routines
   def n_active(self):

      if self.status == 'completed':
         return 0
      
      tot_active = 0
      active_states = ['submitted','running']
      for jid in self.active_job_ids:
         j = stripProxy( GPI.jobs(jid) )

         # try to preserve lazy loading
         if hasattr(j, '_index_cache') and j._index_cache and j._index_cache.has_key('subjobs:status'):
            for sj_stat in j._index_cache['subjobs:status']:
               if sj_stat in active_states:
                  tot_active += 1
         else:            
            #logger.warning("WARNING: (active check) No index cache for job object %d" % jid)
            if j.status in active_states:
               for sj in j.subjobs:
                  if sj.status in active_states:
                     tot_active += 1
                     
      return tot_active

   def n_status(self, status):
      tot_active = 0
      for jid in self.active_job_ids:
         j = stripProxy( GPI.jobs(jid) )

         # try to preserve lazy loading
         if hasattr(j, '_index_cache') and j._index_cache and j._index_cache.has_key('subjobs:status'):
            for sj_stat in j._index_cache['subjobs:status']:
               if sj_stat == status:
                  tot_active += 1
         else:            
            #logger.warning("WARNING: (status check) No index cache for job object %d" % jid)
            for sj in j.subjobs:
               if sj.status == status:
                  tot_active += 1

      return tot_active
   
   def n_all(self):
      total = 0
      for jid in self.active_job_ids:
         j = stripProxy( GPI.jobs(jid) )

         # try to preserve lazy loading
         if hasattr(j, '_index_cache') and j._index_cache and j._index_cache.has_key('subjobs:status'):
            total += len(j._index_cache['subjobs:status'])
         else:            
            #logger.warning("WARNING: (status check) No index cache for job object %d" % jid)
            total = len(j.subjobs)

      return total
         

   def overview(self):
      """Print an overview of this unit"""
      o = "    Unit %d: %s        " % (self.getID(), self.name)

      for s in ["submitted", "running", "completed", "failed", "unknown"]:
         o += markup("%i   " % self.n_status(s), overview_colours[s])

      print o

   def copyOutput(self):
      """Copy any output to the given dataset"""
      logger.error("No default implementation for Copy Output - contact plugin developers")
      return False

   
