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

import os, os.path, argparse, sys, subprocess, shutil, ssl, json, base64
import xml.etree.ElementTree as ET
from urllib2 import urlopen, Request
from urllib import pathname2url, urlencode, quote
from contextlib import closing
from cfchecker import cfchecks

NS = '{http://www.opengis.net/wms}'  # GetCapabilities XML namespace
base_url = "http://adaguc-checker:8080/adaguc-services/adagucserver?"
#base_url = "http://localhost:8090/adaguc-services/adagucserver?"
query_string_cap = '&'.join(("SERVICE=WMS", "VERSION=1.3.0", "REQUEST=GetCapabilities"))
query_string_map = '&'.join(("SERVICE=WMS", "VERSION=1.3.0", "REQUEST=GetMap"))
query_string_par = '&'.join(('WIDTH=1000', 'HEIGHT=900', 'CRS=EPSG:4326', 'STYLES=auto/nearest',
                             'FORMAT=image/png', 'TRANSPARENT=TRUE'))

class AdagucChecker(cfchecks.CFChecker):
    def __init__(self, checks):
        cfchecks.CFChecker.__init__(self)
        self.checks = checks.split(",")
        
    def checker(self, filename):
        ## We need the filename later, CFChecker doesn't store it for us.
        self.fname = os.path.basename(filename)
        if (os.path.dirname(filename) == os.environ['INPUT_DIR'].rstrip('/')):
            self.dirname = "" ## file is not in a (temporary) subdir
        else:
            ## Separate the temporary subdir out to be added to the url.
            self.dirname = os.path.basename(os.path.dirname(filename))
        cfchecks.CFChecker.checker(self, filename)

    def getlayer(self, capabilities):
        """
        Retrieve the first layer from the getcapabilities result.
        """
        layers = []
        try:
            layers = ET.fromstring(capabilities).find(
                NS + 'Capability').find(NS + 'Layer').findall(
                    './' + NS + "Layer[" + NS + "Name]")
            layernames = []
            for layer in layers:
                layernames.append(layer.find(NS + 'Name').text)
            return layernames
        except Exception, e:
            print "Not possible to determine layers: %s" % str(e)
        return None

    def getcapabilities(self, source):
        os.environ["QUERY_STRING"] = '&'.join((source, query_string_cap))
        request = Request(''.join((base_url, '&'.join((source, query_string_cap)))))
        getCapabilitiesResult = ""
        try:
            getCapabilitiesResult = urlopen(url=request, context=ssl._create_unverified_context()).read()
        except Exception, e:
            print "Exception occured while performing getCapabilities request: %s" % str(e)

        #print ("========= BEGIN GETCAPABILITIES REPORT ==========")
        getcap_dict = {"getcap":{"xml":"empty for now"}}
        if (os.path.exists("%s/checker_report.txt" % os.environ['OUTPUT_DIR'])):
            # shutil.copyfile("%s/checker_report.txt" % os.environ['OUTPUT_DIR'], "getcap_report.txt")
            with (open("%s/checker_report.txt" % os.environ['OUTPUT_DIR'])) as reportfile:
                getcap_dict["getcap"].update(json.loads(reportfile.read()))
        #print ("========== END GETCAPABILITIES REPORT ===========")
        return getCapabilitiesResult, getcap_dict

    def getmap(self, source, layer):
        #print "Obtaining report and data for layer", layer

        layer_par = '='.join(("LAYERS", layer))
        get_map_request = ''.join((base_url, '&'.join((source, layer_par, query_string_map, query_string_par))))
        #print "URL:", get_map_request
        try:
            with closing(urlopen(url=get_map_request, context=ssl._create_unverified_context())) as r:
                imgdata = r.read()
            imgfile = open("%s/image.%s.png" % (os.environ['INPUT_DIR'], self.fname), "wb")
            imgfile.write(imgdata)
        except: pass

        #print ("========= BEGIN GETMAP REPORT ==========")
        reportobj_str = ""
        if (os.path.exists("%s/checker_report.txt" % os.environ['OUTPUT_DIR'])):
            with (open("%s/checker_report.txt" % os.environ['OUTPUT_DIR'])) as reportfile:
                reportobj_str = reportfile.read()
        reportobj = json.loads(reportobj_str)
        reportobj["image"] = base64.b64encode(imgdata)
        reportobj["layer"] = layer
        return reportobj
        #print ("========== END GETMAP REPORT ===========")
                    
                    
    def _checker(self):
        #print "Checking ADAGUC extensions"
        sys.stdout = sys.__stdout__
        if ("all" in self.checks or "adaguc" in self.checks):
            if not self.dirname:
                query_string_src = '='.join(("source", "/%s" % self.fname))
            else:
                query_string_src = '='.join(("source", "/%s/%s" % (self.dirname, self.fname)))
            capabilities, cap_dict = self.getcapabilities(query_string_src)
            #print capabilities
            layers = self.getlayer(capabilities)
            map_dict = {"getmap":[]}
            for layer in layers:
                layer_report = self.getmap(query_string_src, layer)
                map_dict["getmap"].append(layer_report)
            report_dict = cap_dict.copy()
            report_dict.update(map_dict)
            print json.dumps(report_dict)
            

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
    sys.stdout = open("/dev/null", "w")
    checker = AdagucChecker(args.checks)
    AdagucChecker.checker(checker, args.filename)
    sys.exit(0)
        
if __name__ == "__main__":
    main()
