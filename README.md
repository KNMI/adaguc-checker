# ADAGUC / adaguc-checker

This checker extends the existing cfchecker by Rosalyn Hatcher (NCAS-CMS, Univ. of Reading, UK) at https://github.com/cedadev/cf-checker by extending the CFChecker class through inheritance.

Usage information will follow when the original checker's command line argument passing is merged with the ADAGUC specific command line argument parsing.

# Getting started

Create a python virtual environment and initialize it.
```
virtualenv ./env-cf-checker
source ./env-cf-checker/bin/activate
```

Clone the existing checker repository:

```
git clone https://github.com/cedadev/cf-checker.git
```

Run it:
```
./adaguc-checker.py --checks=adaguc /nobackup/users/neutvd/data/autowms/S-O3M_GOME_ARP_02_M01_20171015063857Z_20171015073557Z_N_O_20171015134801Z.nc
CHECKING NetCDF FILE: /nobackup/users/neutvd/data/autowms/S-O3M_GOME_ARP_02_M01_20171015063857Z_20171015073557Z_N_O_20171015134801Z.nc
=====================
Using CF Checker Version 3.0.5
Checking against CF Version CF-1.6
Using Standard Name Table Version 49 (2018-02-13T08:44:33Z)
Using Area Type Table Version 6 (22 February 2017)

Checking ADAGUC extensions
```

