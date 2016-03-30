#!/bin/bash

GRANT=./grgrant


# remove goldenrod.conf from /etc/lighttpd/lighttpd.conf
$GRANT sed -i.bak '/goldenrod.conf/d' /etc/lighttpd/lighttpd.conf

# start web server
$GRANT service lighttpd start

# make web server autostart when reboot
$GRANT chkconfig lighttpd on
