#!/bin/bash

## this script will be after upgrade

#chnage version
scripts/change_version.sh

#update sata and SN
scripts/get_sata_sn.sh

#update api server
scripts/init_network.sh
