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

import os, os.path, argparse, sys, subprocess, shutil, ssl, json, base64, logging
import xml.etree.ElementTree as ET
from urllib2 import urlopen, Request
from urllib import pathname2url, urlencode, quote
from contextlib import closing
from cfchecker import cfchecks
from PIL import Image
from io import BytesIO
import re
import warnings

NS = '{http://www.opengis.net/wms}'  # GetCapabilities XML namespace
base_url = "http://adaguc-checker:8080/adaguc-services/adagucserver?"
base_url_bgmap = "http://geoservices.knmi.nl/cgi-bin/bgmaps.cgi?"
base_url_countries = "http://geoservices.knmi.nl/cgi-bin/worldmaps.cgi?"
query_string_cap = '&'.join(("SERVICE=WMS", "VERSION=1.3.0", "REQUEST=GetCapabilities"))
query_string_map = '&'.join(("SERVICE=WMS", "REQUEST=GetMap",'WIDTH=1000', 'HEIGHT=900',
                             'FORMAT=image/png', 'TRANSPARENT=TRUE'))
query_string_par_layer = '&'.join(('CRS=EPSG:4326', 'STYLES=auto/nearest', "VERSION=1.3.0"))
query_string_par_baselayer = '&'.join(('SRS=EPSG:4326', "VERSION=1.1.1"))


warnings.simplefilter(action='ignore', category=FutureWarning)

logger = logging.getLogger('adaguc-checker')
loghandler = logging.FileHandler(filename=os.environ['LOGGING_DIR'] + '/adaguc-checker.log')
loghandler.setFormatter(logging.Formatter('%(asctime)s - [%(name)s:%(levelname)s] %(message)s'))
logger.addHandler(loghandler)
logger.setLevel(logging.DEBUG)

class AdagucChecker(cfchecks.CFChecker):
    def __init__(self, args, cfcheckstream=''):
        cfchecks.CFChecker.__init__(self)
        self.checks = args.checks.split(",")
        self.imagedir = args.imagedir
        self.cfcheckstream = cfcheckstream
        if args.base_url:
            self.base_url = args.base_url
        else:
            self.base_url = base_url

    def checker(self, filename):
        ## We need the filename later, CFChecker doesn't store it for us.
        self.fname = os.path.basename(filename)
        if (os.path.dirname(filename) == os.environ['INPUT_DIR'].rstrip('/')):
            self.dirname = "" ## file is not in a (temporary) subdir
        else:
            ## Separate the temporary subdir out to be added to the url.
            self.dirname = os.path.basename(os.path.dirname(filename))
        cfchecks.CFChecker.checker(self, filename)

    def getlayers(self, capabilities):
        """
        Retrieve all layer-information from the getcapabilities result.
        Layer-information includes:
          - layername
          - boundingbox

        """
        layers_xml = []
        try:
            layers_xml = ET.fromstring(capabilities).find(
                NS + 'Capability').find(NS + 'Layer').findall(
                    './' + NS + "Layer[" + NS + "Name]")
            layers = []
            for layer in layers_xml:
                layers.append({"name": layer.find(NS + 'Name').text, "bbox": layer.find('./' + NS + "BoundingBox[@CRS='EPSG:4326']").attrib})
            return layers
        except Exception, e:
            print >>sys.stderr, "Not possible to determine layers: "+str(e)
            logger.exception("Not possible to determine layers: "+str(e))

        return None

    def getcapabilities(self, source):
        os.environ["QUERY_STRING"] = '&'.join((source, query_string_cap))
        request = Request(''.join((self.base_url, '&'.join((source, query_string_cap)))))
        logger.debug("get_cap_request:\n %s" % request.get_full_url())

        getCapabilitiesResult = ""
        try:
            getCapabilitiesResult = urlopen(url=request, context=ssl._create_unverified_context()).read()
        except Exception, e:
            print >>sys.stderr, "Error occured while performing getCapabilities request: "+str(e)
            logger.exception("Error occured while performing getCapabilities request: "+str(e))



        getcap_dict = {"getcap":{"reportname":"GetCapabilities", "nerrors":0, "nwarnings":0, "ninfo":0, "xml":"empty for now"}}
        if (os.path.exists("%s/checker_report.txt" % os.environ['OUTPUT_DIR'])):
            # shutil.copyfile("%s/checker_report.txt" % os.environ['OUTPUT_DIR'], "getcap_report.txt")
            with (open("%s/checker_report.txt" % os.environ['OUTPUT_DIR'])) as reportfile:
                getcap_dict["getcap"].update(json.loads(reportfile.read()))

        for message in getcap_dict["getcap"]["messages"]:
            if(message["severity"]=='ERROR'):
                getcap_dict["getcap"]["nerrors"]+=1
            elif(message["severity"]=='WARNING'):
                getcap_dict["getcap"]["nwarnings"]+=1
            elif(message["severity"]=='INFO'):
                getcap_dict["getcap"]["ninfo"]+=1

        return getCapabilitiesResult, getcap_dict

    def getmap(self, source, layer):
        """
        Performs a get map request for the specified layer. This results in an image of the getmap result as well as
        a checker report written to the output directory of the checker.
        :param source: autoWMS directory where the file to check is located
        :param layer: layer dictionary including the name and the boundingbox of the layer
        :return: image data for the get map result.
        """

        layer_par = '='.join(("LAYERS", layer["name"]))

        # Note: The order of the boundingbox definition is different for the baselayer service and ADAGUC autoWMS
        bounding_box_arg = ','.join((layer["bbox"]["minx"], layer["bbox"]["miny"], layer["bbox"]["maxx"], layer["bbox"]["maxy"]))
        bounding_box_par = '='.join(("BBOX", bounding_box_arg))

        get_map_request = ''.join((self.base_url, '&'.join((source, layer_par, query_string_map, query_string_par_layer, bounding_box_par))))
        logger.debug("get_map_request:\n" + get_map_request)

        try:
            with closing(urlopen(url=get_map_request, context=ssl._create_unverified_context())) as r:
                imgdata = r.read()
            if self.imagedir and os.path.exists(self.imagedir):
                imgfile = open("%s/%s.%s.png" % (self.imagedir, self.fname, layer["name"]), "wb")
                imgfile.write(imgdata)
                imgfile.close()
            elif not os.path.exists(self.imagedir):
                print >>sys.stderr, "Path "+self.imagedir+" does not exists. Not writing image file."

        except: pass

        return imgdata

    def getbaselayers(self, layer_bbox):
        """
        Retrieves a background layer and country outlines for the given bounding box from geoservices.knmi.nl.
        :param layer_bbox: The required bounding box.
        :return: Image data for the background layer and the country outlines
        """

        # Note: The order of the boundingbox definition is different for the baselayer service and ADAGUC autoWMS
        bounding_box_arg = ','.join((layer_bbox["miny"], layer_bbox["minx"], layer_bbox["maxy"], layer_bbox["maxx"]))
        bounding_box_par = '='.join(("BBOX", bounding_box_arg))

        # Retrieve the background map.
        get_bgmap_request = ''.join((base_url_bgmap, '&'.join((
            "LAYERS=naturalearth2", query_string_map, query_string_par_baselayer, bounding_box_par))))
        logger.debug("get_bgmap_request:\n" + get_bgmap_request)
        bg_imgdata=None
        countries_imgdata=None
        try:
            with closing(urlopen(url=get_bgmap_request, context=ssl._create_unverified_context())) as r:
                bg_imgdata = r.read()

            # Retrieve the countries map.
            get_countries_request = ''.join((base_url_countries, '&'.join((
                "LAYERS=ne_10m_admin_0_countries_simplified", query_string_map, query_string_par_baselayer, bounding_box_par))))
            logger.debug("get_countries_request:\n" + get_countries_request)
            with closing(urlopen(url=get_countries_request, context=ssl._create_unverified_context())) as r:
                countries_imgdata = r.read()

        except Exception, e:
            print >>sys.stderr, "Error occured while retrieving baselayers: "+str(e)
            logger.exception("Error occured while retrieving baselayers: "+str(e))


        return (bg_imgdata, countries_imgdata)

    def combineimages(self, background_imgdata, foreground_imgdata_list):
        """
        Overlays the background imagedata with the images in the foreground_imgdata_list.
        The forground images are added in the order in which they are added to the foreground_imgdata_list.
        :param background_imgdata: The binary background imgdata
        :param foreground_imgdata_list: An array of the binary foreground imgdata
        :return: A BytesIO object containing the combined image.
        """

        merged_imgdata = BytesIO()

        try:
            background=None
            if(background_imgdata is not None):
                background = Image.open(BytesIO(background_imgdata))

            for foreground_imgdata in foreground_imgdata_list:
                if(foreground_imgdata is not None):
                    foreground = Image.open(BytesIO(foreground_imgdata)).convert("RGBA")
                    if(background is None):
                        background = foreground
                    else:
                        background.paste(foreground, mask=foreground)

            background.save(merged_imgdata, "PNG")
        except Exception, e:
            print >>sys.stderr, "Error occured while merging images: "+str(e)
            logger.exception("Error occured while merging images: "+str(e))


        return merged_imgdata

    def createlayerreport(self, layername, layerimage):
        """
        Creates a report in json form for the specified layer, using the current checker report in the output directory.
        This includes the layer name as well as the layer image encoded as a base64 string.
        :param layername: The layer name.
        :param layerimage: The layer image.
        :return:
        """
        reportobj_str = ""
        if (os.path.exists("%s/checker_report.txt" % os.environ['OUTPUT_DIR'])):
            with (open("%s/checker_report.txt" % os.environ['OUTPUT_DIR'])) as reportfile:
                reportobj_str = reportfile.read()
        reportobj = json.loads(reportobj_str)
        reportobj["image"] = base64.b64encode(layerimage.getvalue())
        reportobj["reportname"] = layername
        reportobj["nerrors"] = 0
        reportobj["nwarnings"] = 0
        reportobj["ninfo"] = 0

        for message in reportobj["messages"]:
            if(message["severity"]=='ERROR'):
                reportobj["nerrors"] += 1
            elif(message["severity"]=='WARNING'):
                reportobj["nwarnings"] += 1
            elif(message["severity"]=='INFO'):
                reportobj["ninfo"] += 1

        return reportobj

    def _checker(self):
        report_dict = {"nerrors":0, "nwarnings":0, "ninfo":0}
        if ("all" in self.checks or "standard" in self.checks):

            cfchecks_dict = {"cfcheck_report":{"nerrors":0,"ninfo":0,"nwarnings":0,"header":"","messages":[]}}

            try:
                cfchecks.CFChecker._checker(self)

                curblock=None
                curname=None
                for line in self.cfcheckstream.data.splitlines():
                    if(line.strip()==''):
                        curblock='empty'
                    if(line.startswith('=====================')):
                        curblock='header'
                    elif(line.startswith('------------------')):
                        curblock='check'
                    elif(line.startswith('Checking variable: ')):
                        curblock='check'
                        curname=line[len('Checking variable: '):]
                    elif(line.startswith('WARN: ')):
                        curblock='WARNING'
                        line=line[len('WARN: '):]
                        cfchecks_dict["cfcheck_report"]["nwarnings"]+=1
                    elif(line.startswith('ERROR: ')):
                        curblock='ERROR'
                        line=line[len('ERROR: '):]
                        cfchecks_dict["cfcheck_report"]["nerrors"]+=1
                    elif(line.startswith('INFO: ')):
                        curblock='INFO'
                        line=line[len('INFO: '):]
                        cfchecks_dict["cfcheck_report"]["ninfo"]+=1
                    elif(curblock=='header'):
                        cfchecks_dict["cfcheck_report"]["header"]+=line+"\n"
                    elif(line.startswith('ERRORS detected:')):
                        curblock='summary'

                    if(curblock=='ERROR') or (curblock=='INFO') or (curblock=='WARNING'):
                        if(curname):
                            line='Variable '+curname+': '+line
                        cfchecks_dict["cfcheck_report"]["messages"].append(
                            {
                                "category"          : "GENERAL",
                                "documentationLink" : "",
                                "message"           : line,
                                "severity"          : curblock
                            }
                            )

            except Exception, e:

                cfchecks_dict["cfcheck_report"]["nerrors"]+=1

                cfchecks_dict["cfcheck_report"]["messages"].append(
                        {
                            "category"          : "GENERAL",
                            "documentationLink" : "",
                            "message"           : "Exception occurred during CF-checks.",
                            "severity"          : "ERROR"
                        }
                )

                print >>sys.stderr, "Error occured during CF-checks: "+str(e)
                logger.exception("Error occured during CF-checks: "+str(e))

            report_dict["nerrors"]+=cfchecks_dict["cfcheck_report"]["nerrors"]
            report_dict["nwarnings"]+=cfchecks_dict["cfcheck_report"]["nwarnings"]
            report_dict["ninfo"]+=cfchecks_dict["cfcheck_report"]["ninfo"]

            report_dict.update(cfchecks_dict)

        sys.stdout = sys.__stdout__


        if ("all" in self.checks or "adaguc" in self.checks):
            if not self.dirname:
                query_string_src = '='.join(("source", "/%s" % self.fname))
            else:
                query_string_src = '='.join(("source", "/%s/%s" % (self.dirname, self.fname)))
            capabilities, cap_dict = self.getcapabilities(query_string_src)

            report_dict["nerrors"]+=cap_dict["getcap"]["nerrors"]
            report_dict["nwarnings"]+=cap_dict["getcap"]["nwarnings"]
            report_dict["ninfo"]+=cap_dict["getcap"]["ninfo"]

            layers = self.getlayers(capabilities)
            map_dict = {"getmap":[]}
            for layer in layers:
                layer_imgdata = self.getmap(query_string_src, layer)
                bgmap_imgdata, countries_imgdata = self.getbaselayers(layer["bbox"])

                merged_imgdata = self.combineimages(bgmap_imgdata, (countries_imgdata, layer_imgdata))
                layer_dict = self.createlayerreport(layer["name"], merged_imgdata)

                if(bgmap_imgdata is None) or (countries_imgdata is None):
                    if("messages" not in layer_dict):
                        layer_dict["messages"]=[]
                    layer_dict["messages"].append(
                            {
                                "category"          : "GENERAL",
                                "documentationLink" : "",
                                "message"           : "No response from mapserver; mapimage could not be shown. This is not a Layer report error",
                                "severity"          : "WARNING"
                            }
                    )
                map_dict["getmap"].append(layer_dict)

                layer_dict["nerrors"]=0
                layer_dict["nwarnings"]=0
                layer_dict["ninfo"]=0
                for message in layer_dict["messages"]:
                    if(message["severity"]=='ERROR'):
                        layer_dict["nerrors"]+=1
                        report_dict["nerrors"]+=1
                    elif(message["severity"]=='WARNING'):
                        layer_dict["nwarnings"]+=1
                        report_dict["nwarnings"]+=1
                    elif(message["severity"]=='INFO'):
                        layer_dict["ninfo"]+=1
                        report_dict["ninfo"]+=1


            report_dict.update(cap_dict)
            report_dict.update(map_dict)

        print json.dumps(report_dict)

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
    parser.add_argument("--imagedir", type=str, dest="imagedir", nargs="?", action="store", default=None,
                        required=False, help=("Directory to store images in if you want to "
                                              "keep them. If this option is not given, no images "
                                              "will be kept on disk."))
    parser.add_argument("--baseurl", type=str, dest="base_url", nargs="?", action="store", default=None,
                        required=False, help=("Base url consisting of hostname, port and pathname. "
                                              "This is used to construct the first part of the WMS "
                                              "request. Default is %s which is suitable for the "
                                              "dockers started with the start-docker.sh script." % base_url))
    return parser.parse_args()

class StreamToStr():
    """
    Catches all stdoutput and concatenates to self.data
    :return: A class-instance, with StreamToStr.data containing the stream
    """
    def __init__(self):
        self.data=''
    def write(self, s):
        self.data+=s

def main():
    args = parse_args()
    sys.stdout = cfcheckstream = StreamToStr()
    checker = AdagucChecker(args, cfcheckstream)
    AdagucChecker.checker(checker, args.filename)
    sys.exit(0)

if __name__ == "__main__":
    main()
