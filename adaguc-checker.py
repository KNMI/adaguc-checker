#!/usr/bin/env python

import os.path, argparse, sys
from cfchecker import cfchecks

class AdagucChecker(cfchecks.CFChecker):
    def __init__(self):
        cfchecks.CFChecker.__init__(self)

    def _checker(self):
        print "Checking ADAGUC extensions"
        cfchecks.CFChecker._checker(self)

def parse_args():
    parser = argparse.ArgumentParser(description="Check NetCDF CF file for CF and ADAGUC compliance.")
    parser.add_argument("filename", help="Path to NetCDF file to check.")

    return parser.parse_args()
        
def main():
    args = parse_args()
    checker = AdagucChecker()
    AdagucChecker.checker(checker, args.filename)
    sys.exit(0)
        
if __name__ == "__main__":
    main()
