# ipsan
ipsan server base on linux
IPSAN web api modules:

  1) System settings(apisystem)
     1.1) View system information
     1.2) Datetime setting
     1.3) Reboot & Shutdown

  2) Network setting(apisystem)
     2.1) IP Address, Gateway, Route

  3) User Management(apiuser)
     3.1) Add/Delete/Update user

  4) RAID Management(apiarray)
     4.1) View RAID
     4.2) Create RAID (0, 1, 5,6,10)

  5) Storage Management(apilvm, apivg)
     5.1) Volume group management(apivg). Add/Delete volume group
     5.2) LVM Management(apilvm), Add/Delete/Update LVM


  6) SAN Management
     6.1) ISCSI Target Management. Add/Delete target. Modify target name.

  7) Mantance/Update(apisystem, apievent)
     7.1) Software upgrade. support upload files to upgrade
     7.2) Event log



IPSAN api provide HTTP API. JSON fomatted data

Response success:
{
  "retcode": 0
  ....
}

Response failure:
{
  "retcode": 400,
  "message": "add user failure"
}

Success: retcode=0
Failure: retcode != 0. message member store failure reason.

----------------------------------------------------------
IPSAN Server
Dependency:
  >= python3
  aiohttp: http server
  supervisor: unix process control
  nginx: web/proxy server

Install:
  1) $ zypper in python-pip
  2) $ pip install supervisor --pre or 
     $ pip install supervisor   or
     $ easy_setup supervisor
  3) config supervisor

     $ echo_supervisord_conf > /etc/supervisord.conf
  4) chkconfig supervisord on

  5) install aiohttp
     $ pip3 install aiohttp or
     $ easy_setup aiohttp
 
  6) nginx
     Suse:
        $ zypper in nginx
        $ chkconfig nginx on
        $ chkconfig nginx start

        $ vim /etc/nginx/nginx.conf      #nginx server configuration
        $ mkdir -p /etc/nginx/vhosts.d
        $ cd /et/nginx/vhosts-d
        $ vim sanweb.conf
        serrver {
          listen        80; 
          server_name   localhost;

          location / {
            root  /srv/san/sanweb;
            index index.html;
          }
        }
        $ nginx -s reload

    Ubuntu:
     $ apt-get install nginx
     $ vim /etc/nginx/sites-available/default
     server {
      listen       80;
      server_name  localhost;
        location / {
            root  /srv/san/sanweb;
            index index.html;
          }
     }
     $ nginx -s reload


