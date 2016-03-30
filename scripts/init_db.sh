#! /bin/bash

# create database
IPSANDB=ipsan.db

if [ ! -f $IPSANDB ]; then
	echo -e "\033[32mInstall ipsan database....\033[0m"
	sqlite3 $IPSANDB < scripts/schema.sql
fi
