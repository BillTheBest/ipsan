#!/bin/bash
DIAGNOSIS_DIR=diagnosis
GRANT=./grgrant

rm -rf $DIAGNOSIS_DIR
mkdir $DIAGNOSIS_DIR
$GRANT cp /var/log/messages* $DIAGNOSIS_DIR
$GRANT chown surveil.users $DIAGNOSIS_DIR/messages*
cp Changes $DIAGNOSIS_DIR
cp log/*.log $DIAGNOSIS_DIR
cp ipsan.db $DIAGNOSIS_DIR
cp -rf /etc/tgt/conf.d $DIAGNOSIS_DIR
tar czf web/diagnosis.tar.gz diagnosis
