#! /bin/bash

echo
echo "--------------Installing ipsan-----------------------"
echo 


# init web server
scripts/init_websrv.sh


# get sata and SN
scripts/get_sata_sn.sh

# update version
scripts/change_version.sh

# init database
scripts/init_db.sh

# init supervisor
scripts/init_supervisor.sh

# init target
scripts/init_target.sh

echo 
echo "--------------Install completed---------------------"
echo 
exit 0
