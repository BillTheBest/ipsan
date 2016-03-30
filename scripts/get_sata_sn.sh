#! /bin/bash

# get sata controller information

GRANT=./grgrant


SATA=`$GRANT /sbin/lspci | grep 'SATA controller:' | grep -v 'Intel Corporation' | wc -l`
PANEL=0  #default is 8 panel
if [ $SATA == 2 ]; then
	PANEL=3  # 8 panel
elif [ $SATA == 3 ]; then
	PANEL=8  # 16 panel
else
	PANEL=8
fi

echo -e "\033[32mMachine have $PANEL slot.\033[0m"
sed -i "s/'panel': .*/'panel': $PANEL/g" api/config_defaults.py

# generate SN
SN=`./grsn NVR | cut -c4-`
echo -e "\033[32mMachine serial number is\033[0m \033[31m$SN\033[0m"
sed -i "s/'SN': '.*'/'SN': '$SN'/g" api/config_defaults.py
