#!/afs/inf.ed.ac.uk/user/s14/s1413557/miniconda2/bin/python

from __future__ import print_function

import time as sleeptime
from mpi4py import MPI
from mpi.master_slave import Master, Slave
from mpi.work_queue import WorkQueue
from f4klib import *
import shutil
import gc
import multiprocessing

#HOSTS=basso,battaglin,belloni,bergamaschi,berrendero,bertoglio,berzin,binda
#mpiexec -n 11 -host $HOSTS python ~/f4k/runMulticoreFeatureExtractNoReduction.py


class MyApp(object):

    def __init__(self, slaves):
        self.master = Master(slaves)
        self.work_queue = WorkQueue(self.master)

    def terminate_slaves(self):
        self.master.terminate_slaves()

    def run(self):
        
        time = datetime.now()
        movs = loadMovids()
        movs_length = loadLengths()
        
        #13b: 30598-30695
        
        #0: 0-24941
        #1: 24941-49433
        #2: 49433-74100
        #3: 74100-99012
        #4: 99012-123658
        #5: 123658-148701
        #6: 148701-173761
        #7: 173761-198372
        #8: 198372-223132
        #9: 223132-247825
        #a: 247825-272495
        #b: 272495-297592
        #c: 297592-322424
        #d: 322424-347142
        #e: 347142-372011
        #f: 372011-396901
        
        start = 0
        end = 1584
        
        #Put longer task at start.
        if end == 396901:
            order = np.argsort(np.append(movs_length[372011:396901-1],(movs_length[-1])))
        else:
            order = np.argsort(movs_length[start:end])
        
        #For statistics
        totWork = 0#end - start
        completed = 0
        
        #for i in np.arange(start,end)[order]:
            
        idlist = np.array([396853,396857,396859,396860,396866,396876,396880,396892,396895,396900,
                        396823,396829,396843,396852,396862,396870,396882,396885,396889,396894,
                        396856,396863,396864,396868,396869,396893,396896,396897,396898,396899,
                        396624,396639,396662,396675,396728,396737,396759,396777,396790,396804,
                        396750,396760,396767,396784,396792,396793,396872,396877,396878,396886,
                        396824,396836,396839,396854,396858,396861,396865,396871,396874,396884,
                        396720,396733,396778,396815,396820,396827,396830,396834,396879,396890,
                        396840,396841,396845,396849,396850,396851,396867,396883,396887,396891,
                        396785,396802,396811,396822,396838,396844,396873,396875,396881,396888])
        order = np.argsort(movs_length[idlist])
        #forty = [112,180,272,285,330,447,469,474,498,500,517,527,545,550,622]
        #fortyone = [10, 33, 75, 82, 101, 114, 182, 183, 275, 279, 282, 291, 306, 325, 338, 380, 420, 424]
        for i in idlist[order]:
            
            if False and earlyRemoval(movs[i], movs_length[i]):
                idee = movs[i][0]
                savepath = "/afs/inf.ed.ac.uk/group/ug4-projects/s1413557/features/{0}/{1}/{2}"
                savepath = savepath.format(idee[0],idee[0:2],idee)
                
                if not os.path.isfile(savepath+".COMPLETE.npy"):
                    print("Master removes movid {0} with early removal".format(movs[i][0]))
                    np.save(savepath+".COMPLETE",np.array([]))
                
            else:
                totWork += 1
                movid = movs[i]
                #It's modified that task is appended at front
                self.work_queue.add_work(data=('Do stuff', movid))

                
        #for i in range(tasks):
        #    self.work_queue.add_work(data=('Do stuff', i))
       
        while not self.work_queue.done():

            self.work_queue.do_work()

            #
            # reclaim returned data from completed slaves
            #
            for slave_return_data in self.work_queue.get_completed_work():
                done, message, movidf = slave_return_data
                if done:
                    if message == "FAILED":
                        self.work_queue.add_work(data=('Do stuff', movidf))
                    else:
                        completed += 1
                        print("Progress: {0}/{1}, took {2}. {3}"
                          .format(str(completed).rjust(6),str(totWork).rjust(6),str(datetime.now()-time),message))

            # sleep some time
            sleeptime.sleep(0.001)

class MySlave(Slave):
    """
    A slave process extends Slave class, overrides the 'do_work' method
    and calls 'Slave.run'. The Master will do the rest
    """

    def __init__(self):
        
        super(MySlave, self).__init__()
        self.ranges = loadRange()
        self.pca = loadPCA(self.ranges)
           
    def run(self):
        super(MySlave, self).run()
        try:
            self.p.terminate()
            print(MPI.Get_processor_name().split(".")[0] + "'s subprocess killed!")
        except Exception:
            print(MPI.Get_processor_name().split(".")[0] + "'s subprocess killing failed!")
            
    def do_work(self, data):
        
        q = multiprocessing.Queue()
        self.p = multiprocessing.Process(target=do_actual_work, args=(self,data,q,))
        self.p.start()
        ret = q.get()
        self.p.join()
        return (ret[0],ret[1],ret[2])
        

def do_actual_work(self, data, q):
    rank = MPI.COMM_WORLD.Get_rank()
    name = MPI.Get_processor_name().split(".")[0].ljust(12)
    task, movid = data
    idee = movid[0]
    fname = movid[0].split("#")[0]
    savepath = "/afs/inf.ed.ac.uk/group/ug4-projects/s1413557/features/{0}/{1}/{2}".format(idee[0],idee[0:2],idee)

    #Check if video is already extracted.
    if os.path.isfile(savepath+".COMPLETE.npy"):
        q.put([True, 'Slave: %s skipped   %s because it\'s done.' % (name, idee), movid])
        return

    #Load the video
    time = datetime.now()
    info, clip, hasContour, contour, fish_id, frames = loadVideo(movid)

    #Skipping empty videos
    if frames == 0:
        #Skipping stuff
        #print('Slave: %s skipped an empty video "%s"' % (name, idee))
        np.save(savepath+".COMPLETE",np.array([]))
        q.put([True, 'Slave: %s skipped   %s because it\'s empty' % (name, idee), movid])
        return

    #Notify the Boss
    print('                                              Slave: {0} started   {1} with {2} frames'
          .format(name, idee, str(frames).ljust(6)))

    #Prevent Opening Matlab before the prev one close.
    try: session
    except NameError: session = None
    if session is None:
        try:
            session = pymatlab.session_factory('matlab -nodisplay')
            session.run('cd /afs/inf.ed.ac.uk/user/s14/s1413557/f4k-2017-msc-master/matt-msc/workspace/f4k/fish_recog')
            jobloc = "'/afs/inf.ed.ac.uk/user/s14/s1413557/.matlab/" + name.strip() + "/'"
            
            #I hate matlab
            session.run("pc = parcluster('local')")
            session.run("mkdir('/afs/inf.ed.ac.uk/user/s14/s1413557/.matlab/','" + name.strip() + "')")
            session.run(("pc.JobStorageLocation = " + jobloc))
            session.run("parpool(pc, 4)")
        except Exception:
            print("Slave {0} failed! On Task {1}! initializing MATLAB".format(name, idee))
            q.put([True, "FAILED", movid])
            return
    
    feif_result = np.zeros(frames, dtype=bool)
    for i in range(frames):
        feif_result[i] = True

    if np.sum(feif_result) == 0:
        #Skipping stuff
        #print('Slave: %s skipped an empty video "%s"' % (name, idee))
        np.save(savepath+".COMPLETE",np.array([]))
        q.put([True, 'Slave: %s skipped   %s because it\'s all rejected' % (name, idee), movid])
        return

    #Setting up features need to be computed
    hasCL = np.sum(feif_result)
    rgbImgs = [None]*hasCL
    binImgs = [None]*hasCL
    index = 0
    for i in range(frames):
        if feif_result[i]:
            rgbImgs[index]=clip[i]
            binImgs[index]=np.full((100,100), 0, dtype=np.uint8)
            thisContour = np.int32([getContour(contour[i])])
            cv2.fillPoly(binImgs[index], thisContour, (255,))
            index += 1

    #Compute the features

    try:
        session.putvalue('A',rgbImgs)
        session.putvalue('B',binImgs)
        session.run('C = feature_batchGenerateFeatureVector(A,B)')
        f4kfeatures = session.getvalue('C')
    except Exception:
        print("Slave {0} failed! On Task {1}!".format(name, idee))
        q.put([True, "FAILED", movid])
        return

    #Get Matt's features
    mattFeatures = getMattFeatures(info, clip, hasContour, contour, fish_id)

    #Normalize and transform.
    if np.sum(feif_result) == 1:
        #I hate this
        comb = np.column_stack((f4kfeatures.reshape(1,-1), mattFeatures[feif_result]))
    else:
        comb = np.column_stack((f4kfeatures, mattFeatures[feif_result]))
    normPhi = normalizePhi(comb,self.ranges)
    transformed_features = self.pca.transform(normPhi)

    #np.save(savepath+".f4kfeature",f4kfeatures)
    #np.save(savepath+".mattfeature",mattFeatures)

    #Only save 100 first feature here to save space.
    np.save(savepath+".pcaFeature",transformed_features[:,:100])
    np.save(savepath+".feif",feif_result)
    np.save(savepath+".COMPLETE",np.array([]))

    #JustMatlabThings#
    del session
    sleeptime.sleep(1)
    if name[:7] == "ashbury":
        sleeptime.sleep(4)

    #Cleanup not sure if helps (HINT: IT DOESN'T)
    del info, clip, hasContour, contour, fish_id
    del comb, normPhi, transformed_features
    del rgbImgs, binImgs
    gc.collect()

    retString = "Slave: {0} completes {1} with {2} frames in {3}"
    retString = retString.format(name, idee, str(frames).ljust(6), str(datetime.now()-time))

    q.put([True, retString, movid])
    return
    
    
def main():

    name = MPI.Get_processor_name()
    rank = MPI.COMM_WORLD.Get_rank()
    size = MPI.COMM_WORLD.Get_size()
    os.nice(19)

    print('I am  %s rank %d (total %d)' % (name, rank, size) )

    if rank == 0: # Master

        app = MyApp(slaves=range(1, size))
        app.run()
        app.terminate_slaves()

    else: # Any slave

        MySlave().run()

    print('Task completed (rank %d)' % (rank) )

if __name__ == "__main__":
    main()

