#!/bin/bash
DIAGNOSIS_DIR=diagnosis
rm -rf $DIAGNOSIS_DIR
mkdir $DIAGNOSIS_DIR
cp log/*.log $DIAGNOSIS_DIR
cp ipsan.db $DIAGNOSIS_DIR
cp -rf /etc/tgt/conf.d $DIAGNOSIS_DIR
tar czf /opt/goldenrod/web/diagnosis.tar.gz diagnosis
