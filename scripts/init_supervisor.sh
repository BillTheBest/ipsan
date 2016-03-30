#! /bin/bash


# for colorful output
function show_fail()
{
	echo -e "\033[41;37m$1.\033[0m"
}

function show_success()
{
	echo -e "\033[42;37m$1.\033[0m"
}

function show_info()
{
	echo -e "\033[32m$1.\033[0m"
}

GRANT=./grgrant

# check supervisord
SUPERVISORD=/usr/bin/supervisord
SUPERVISORCTL=/usr/bin/supervisorctl
SUPERVISORCFG=/etc/supervisord.conf
NEWCFG=`basename $SUPERVISORCFG`

if [ ! -f $SUPERVISORD ]; then
	show_fail "Missing $SUPERVISORD"
	exit 1
fi

# make supervisord started when boot
$GRANT chkconfig `basename $SUPERVISORD` on

show_info "Initialize supervisor configuration..."

cp $SUPERVISORCFG $NEWCFG

# add ipsanapi supervisor
cat $SUPERVISORCFG | grep "ipsanapi" > /dev/null
RET=`echo $?`
if [ $RET != 0 ]; then
	echo -e "
[program:ipsanapi]
command=/usr/bin/python3 api/app.py
directory=/opt/goldenrod
autostart=true
user=surveil
" >> $NEWCFG
	show_info "Add ipsanapi supervisord"
fi

# add ipsand supervisor
cat $SUPERVISORCFG | grep "ipsand" > /dev/null
RET=`echo $?`
if [ $RET != 0 ]; then
	echo -e "
[program:ipsand]
command=/usr/bin/python3 daemon/ipsand.py
directory=/opt/goldenrod
autostart=true
user=surveil
" >> $NEWCFG
	show_info "Add ipsand supervisord"
fi

$GRANT mv $NEWCFG $SUPERVISORCFG

show_success "Supervisor configuration initialize completed"

show_info "Restarting supervisor..."
#$GRANT $SUPERVISORCTL reload
RET=`echo $?`
if [ $RET != 0 ]; then 
	show_fail "Restart supervisor failure"
fi

show_success "Supervisor started"

# start ipsan api service
show_info "Starting IPSan API service..."
$GRANT $SUPERVISORCTL restart ipsanapi
RET=`echo $?`
if [ $RET != 0 ]; then 
	show_fail "Start IPSan API service failure"
fi
show_success "IPSan API service started"

# start ipsan daemon
show_info "Starting IPSan daemon..."
$GRANT $SUPERVISORCTL restart ipsand
RET=`echo $?`
if [ $RET != 0 ]; then 
	show_fail "Start IPSan daemon failure"
fi
show_success "IPSan daemon started"
