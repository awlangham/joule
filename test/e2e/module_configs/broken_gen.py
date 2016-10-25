#!/usr/bin/python3

from nilmdb.utils.time import now as time_now
import time
import numpy as np
import sys,os
rows = 100
freq = 4 #Hz

"""
Inserts 100 samples and then fails with an exception
"""
  
def main(ts):
  data = np.sin(np.arange(0,2*np.pi,2*np.pi/rows))
  data.shape=(rows,1)
  ts_inc = 1/rows*(1/freq)*1e6 #microseconds
  data_ts = ts
  while(True):
    top_ts = data_ts+100*ts_inc
    ts = np.array(np.linspace(data_ts,top_ts,rows,endpoint=False), dtype=np.uint64)
    ts.shape = (rows,1)
    ts_data = np.hstack((ts,data))
    os.write(sys.stdout.fileno(),ts_data.tobytes())
    print("added data",file=sys.stderr)
    sys.stderr.flush()
    data_ts = top_ts
    time.sleep(1/freq)
    raise ValueError
  
if __name__=="__main__":
  print("starting!",file=sys.stderr)
  main(time_now())
  
