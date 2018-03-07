#!/usr/bin/env python

 #*****************************************************************************
 # 
 # Author:   Ian van der Neut <neutvd@knmi.nl>
 # Date:     2015-05-06
 #
 #*****************************************************************************
 #
 # Copyright 2018, Royal Netherlands Meteorological Institute (KNMI)
 #
 # Licensed under the Apache License, Version 2.0 (the "License");
 # you may not use this file except in compliance with the License.
 # You may obtain a copy of the License at
 # 
 #      http://www.apache.org/licenses/LICENSE-2.0
 # 
 # Unless required by applicable law or agreed to in writing, software
 # distributed under the License is distributed on an "AS IS" BASIS,
 # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 # See the License for the specific language governing permissions and
 # limitations under the License.
 # 
 #*****************************************************************************/



import os.path, argparse, sys
from cfchecker import cfchecks

class AdagucChecker(cfchecks.CFChecker):
    def __init__(self, checks):
        cfchecks.CFChecker.__init__(self)
        self.checks = checks.split(",")

    def _checker(self):
        print "Checking ADAGUC extensions"
        if ("all" in self.checks or "adaguc" in self.checks):
            self._check_dimensions()
        if ("all" in self.checks or "standard" in self.checks):
            cfchecks.CFChecker._checker(self)

    def _check_latlon_bounds(self):
        pass
    def _check_latlon(self):
        pass
    def _check_time(self):
        pass
    def _check_variables(self):
        pass
    def _check_dimensions(self):
        dims = self.f.dimensions.keys()
        if ('nv' not in dims):
            self._add_error("The nv dimension does not exist.")
        if ('time' not in dims):
            self._add_error("The time dimenstion does not exist.")

def parse_args():
    parser = argparse.ArgumentParser(description="Check NetCDF CF file for CF and ADAGUC compliance.")
    parser.add_argument("filename", help="Path to NetCDF file to check.")
    parser.add_argument("--checks", type=str, dest="checks", nargs="?", action="store",
                        default="all", required=False,
                        help=("Checks to perform: all, adaguc, standard.\n"
                              "all: perform both adaguc and standard cf."
                              "adaguc: perform only adaguc related checks."
                              "standard: perform only standard cf checks."))

    return parser.parse_args()
        
def main():
    args = parse_args()
    checker = AdagucChecker(args.checks)
    AdagucChecker.checker(checker, args.filename)
    sys.exit(0)
        
if __name__ == "__main__":
    main()
