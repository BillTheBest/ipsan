#! /bin/bash

PACKAGE_NAME=goldenrod.IPSAN.tar.gz

if [ -f $PACKAGE_NAME ]; then
	rm $PACKAGE_NAME
fi

tar czf $PACKAGE_NAME api/*.py admin/*.py daemon/*.py collect_diagnosis.sh install.sh schema.sql grdisk grdport


#tar vczf - admin/*.py api/*.py daemon/*.py | ssh surveil@192.168.1.228 tar xzvf - -C /opt/goldenrod
