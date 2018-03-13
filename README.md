# ADAGUC / adaguc-checker

This checker extends the existing cfchecker by Rosalyn Hatcher (NCAS-CMS, Univ. of Reading, UK) at https://github.com/cedadev/cf-checker by extending the CFChecker class through inheritance.

Usage information will follow when the original checker's command line argument passing is merged with the ADAGUC specific command line argument parsing.

# Getting started

## Prerequisites
For the moment, you need a compiled binary of adaguc-server with the
reporting capability. The output is not very meaningful as of yet.
You can get adaguc-server with reporting capability here:
https://github.com/saskiawagenaar/adaguc-server

Create a python virtual environment and initialize it.
```
virtualenv ./env-cf-checker
source ./env-cf-checker/bin/activate
```

Clone the existing checker repository:

```
git clone https://github.com/cedadev/cf-checker.git
```
## Running the software
Assuming that the autowms toplevel directory is /data/autowms:
```
AUTOWMS_PATH=/data/autowms ./adaguc-checker.py --checks=adaguc /nobackup/users/neutvd/data/autowms/S-O3M_GOME_ARP_02_M01_20171015063857Z_20171015073557Z_N_O_20171015134801Z.nc
CHECKING NetCDF FILE: /nobackup/users/neutvd/data/autowms/S-O3M_GOME_ARP_02_M01_20171015063857Z_20171015073557Z_N_O_20171015134801Z.nc
=====================
Using CF Checker Version 3.0.5
Checking against CF Version CF-1.6
Using Standard Name Table Version 49 (2018-02-13T08:44:33Z)
Using Area Type Table Version 6 (22 February 2017)

Checking ADAGUC extensions
```
# Running ADAGUC as Docker container

## Configure 
mkdir /tmp/input_dir
chmod 777 /tmp/input_dir
mkdir /tmp/output_dir
chmod 777 /tmp/output_dir
check adguc-checker.env:
  directories $INPUT_DIR and $OUTPUT_DIR should exist and have mods 777
source adaguc_checker.env
  
## Build ADAGUC server docker image
git clone git@github.com:saskiawagenaar/adaguc-server.git  # For now, should be ADAGUC repo.
cd adaguc-server

docker build -t $ADAGUC_CHECKER_IMAGE .
start-docker-adaguc-checker                # maybe "docker rm adaguc-checker" first



