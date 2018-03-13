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

import os, os.path, argparse, sys, subprocess, shutil
import xml.etree.ElementTree as ET
from cfchecker import cfchecks

NS = '{http://www.opengis.net/wms}'  # GetCapabilities XML namespace
query_string_cap = '&'.join(("SERVICE=WMS", "VERSION=1.3.0", "REQUEST=GetCapabilities"))
query_string_map = '&'.join(("SERVICE=WMS", "VERSION=1.3.0", "REQUEST=GetMap"))
query_string_par = '&'.join(('WIDTH=1000', 'HEIGHT=900', 'CRS=EPSG:4326',
                             'BBOX=-179.0,179.0,-89.0,89.0', 'STYLES=auto/nearest',
                             'FORMAT=image/png', 'TRANSPARENT=TRUE'))

class AdagucChecker(cfchecks.CFChecker):
    def __init__(self, checks):
        cfchecks.CFChecker.__init__(self)
        self.checks = checks.split(",")
        try:
            self.adaguc = os.path.join(os.environ['ADAGUC_PATH'], "adagucserverEC/adagucserver")
            if (not os.path.exists(self.adaguc)):
                raise Exception(("adagucserver executable not found at %s. "
                                 "Please set ADAGUC_PATH environment variable correctly.") % self.adaguc)
        except KeyError:
            print("Could not determine path to adaguc. "
                  "ADAGUC_PATH environment variable not set.")
            sys.exit(1)
        except Exception, e:
            print(e)
            sys.exit(1)


    def checker(self, filename):
        ## We need the filename later, CFChecker doesn't store it for us.
        self.fname = os.path.basename(filename)
        self.autowmspath = os.path.join(os.environ['AUTOWMS_PATH'], self.fname)
        if (os.path.exists(self.autowmspath)):
            os.unlink(self.autowmspath)
        os.link(filename, self.autowmspath)
        cfchecks.CFChecker.checker(self, filename)

    def getlayer(self, capabilities):
        """
        Retrieve the first layer from the getcapabilities result.
        """
        layers = []
        try:
            layers = ET.fromstring(capabilities).find(
                NS + 'Capability').find(NS + 'Layer').findall('./' + NS + "Layer[" + NS + "Name]")
            return layers[0].find(NS + 'Name').text
        except Exception, e:
            print "Not possible to determine layers: %s" % str(e)
        return None

    def getcapabilities(self, source):
        os.environ["QUERY_STRING"] = '&'.join((source, query_string_cap))
        #print "QUERY_STRING=",os.environ['QUERY_STRING']
        adagucproc = subprocess.Popen(self.adaguc, stdout=subprocess.PIPE)
        (o, i) = adagucproc.communicate(input=None) 

        if (os.path.exists("checker_report.txt")):
            shutil.copyfile("checker_report.txt", "getcap_report.txt")
        return '\n'.join(o.split('\n')[2:]) ## return with first two lines (HTTP response) stripped

    def getmap(self, source, layer):
        print "Obtaining report and data for layer", layer
        layer_par = '='.join(("LAYERS", layer))
        os.environ["QUERY_STRING"] = '&'.join((source, layer_par, query_string_map, query_string_par))
        print "QUERY_STRING=",os.environ['QUERY_STRING']
        adagucproc = subprocess.Popen(self.adaguc, stdout=subprocess.PIPE)
        (o, i) = adagucproc.communicate(input=None)
        imgdata_start = o.find('PNG')
        img = open("image.png", "w")
        img.write(o[imgdata_start:])
        #img.write(o)
        img.close()
        
        if (os.path.exists("checker_report.txt")):
            shutil.copyfile("checker_report.txt", "getmap_report.txt")
                    
    def _checker(self):
        print "Checking ADAGUC extensions"
        if ("all" in self.checks or "adaguc" in self.checks):
            query_string_src = '='.join(("source", os.path.join("/checker", self.fname)))
            capabilities = self.getcapabilities(query_string_src)
            layer = self.getlayer(capabilities)
            self.getmap(query_string_src, layer)

        if ("all" in self.checks or "standard" in self.checks):
            cfchecks.CFChecker._checker(self)

        ## Cleanup
        #if (os.path.exists(self.autowmspath)):
        #    os.unlink(self.autowmspath)

    def _check_latlon_bounds(self):
        pass
    def _check_latlon(self):
        pass
    def _check_time(self):
        pass
    def _check_variables(self):
        pass
    def _check_dimensions(self):
        pass

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
