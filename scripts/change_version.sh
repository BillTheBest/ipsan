#! /bin/bash

# change version
VER=`cat grpack.ini | grep 'version=' | cut -c9-`
echo -e "\033[32mSoftware version is $VER\033[0m"
sed -i "s/'version': '.*'/'version': '$VER'/g" api/config_override.py
