#!/usr/bin/python3
import time
import sys
import re
sys.path.append("/module_scripts") #add e2eutils
from e2eutils import joule as joule_cmd
from e2eutils import nilmtool as nilmtool_cmd

def main():
  time.sleep(8) #wait for jouled to boot
  print(joule_cmd.logs("Filter"))
  check_modules()
  check_data()
  check_logs()
  
def check_modules():
  """
  Test: check module status
  Goal:
    normal1: running some nonzero memory
    normal2: running some nonzero memory
    filter:  running some nonzero memory
    broken:  present (could be running or failed)
    misconfigured: not present b/c can't be loaded
  """
  modules = joule_cmd.modules()
  assert(len(modules)==4) #normal1,normal2,filter,broken
  for module in modules:
    title = module[joule_cmd.MODULES_TITLE_FIELD]
    status = module[joule_cmd.MODULES_STATUS_FIELD]
    if(title['name'] in ['Normal1','Normal2','Filter']):
      assert(status==joule_cmd.MODULES_STATUS_RUNNING)
    elif(title['name']=='Broken'):
      pass
    else:
      assert(0) #unexpected module in status report

def check_data():
  """
  Test: check data inserted into nilmdb
  Goal:
    /normal1/data has 1 interval with >500 samples
    /normal2/subpath/data has multiple intervals each with 100 samples
    /broken/data exists but has no data
    both normal1 and normal2 have decimations
  """
  normal1_path = "/normal1/data"
  normal2_path = "/normal2/subpath/data"
  broken_path = "/broken/data"
  filter1_path = "/filter1/data"
  filter2_path = "/filter2/data"
  intervals = nilmtool_cmd.intervals(normal1_path)
  assert(len(intervals)==1)
  num_samples = nilmtool_cmd.data_count(normal1_path)
  assert(num_samples>500)
  intervals = nilmtool_cmd.intervals(normal2_path)
  assert(len(intervals)==1)
  num_samples = nilmtool_cmd.data_count(normal2_path)
  assert(num_samples>500)
  intervals = nilmtool_cmd.intervals(broken_path)
  assert(len(intervals)>1)
  for interval in intervals:
    num_samples = nilmtool_cmd.data_count(broken_path,interval)
    assert(num_samples==100)

  assert(nilmtool_cmd.is_decimated(normal1_path))
  assert(nilmtool_cmd.is_decimated(normal2_path))
  assert(nilmtool_cmd.is_decimated(broken_path))

  print(nilmtool_cmd.data_extract(normal2_path))
  print("------")
  print(nilmtool_cmd.data_extract(filter2_path))
  
def check_logs():
  """
  Test: logs should contain info and stderr from modules
  Goal: 
    Normal1: says "starting" somewhere once
    Normal2: says "starting" somewhere once
    Filter: says "starting" somewhere once
    Broken: says "starting" and more than one "restarting"
    Misconfigured: no logs
  """
  for module_name in ["Normal1","Normal2","Filter"]:
    logs = joule_cmd.logs(module_name)
    num_starts = len(re.findall(joule_cmd.LOG_STARTING_STRING,logs))
    assert(num_starts==1)

  logs = joule_cmd.logs("Broken")
  num_starts = len(re.findall(joule_cmd.LOG_STARTING_STRING,logs))
  assert(num_starts>1)

if __name__=="__main__":
  main()
  print("OK")

