import numpy as np
import argparse
import joule

ARGS_DESC = """
---
:name:
  Mean Filter
:author:
  John Donnal
:license:
  Open
:url:
  http://git.wattsworth.net/wattsworth/joule.git
:description:
  adjustable moving average
:usage:
    Apply a moving average to the input stream with an
    adjustable window size
    
    | Arguments | Description                     |
    |-----------|---------------------------------|
    |``window`` | samples to average, must be odd |


:inputs:
  input
  :  **<any type>** with N elements

:outputs:
  output
  :  **float32** with N elements

:stream_configs:
  #input#
     [Main]
     name = Raw Data
     path = /path/to/input
     datatype = int32
     keep = 1w

     [Element1]
     name = Element 1

     [Element2]
     name = Element 2

     #additional elements...

  #output#
     [Main]
     name = Filtered Data
     path = /path/to/output
     datatype = float32
     keep = 1w

     #same number of elements as input
     [Element1]
     name = Element 1

     [Element2]
     name = Element 2

     #additional elements...

:module_config:
    [Main]
    name = Mean Filter
    exec_cmd = joule-mean-filter

    [Arguments]
    window = 11 # must be odd

    [Inputs]
    input = /path/to/input 

    [Outputs]
    output = /path/to/output
---
"""


class MeanFilter(joule.FIRFilterModule):
    "Compute the moving average of the input"
    
    def custom_args(self, parser):
        parser.add_argument("window", type=int,
                            help="window length (odd)")
        parser.description = ARGS_DESC
        parser.formatter_class = argparse.RawDescriptionHelpFormatter

    def make_filter(self, parsed_args):
        N = parsed_args.window
        return np.ones((N,))/N

                
def main():
    r = MeanFilter()
    r.start()

    
if __name__ == "__main__":
    main()
