#!/bin/bash

BUILD_RESULT=0

if [ -e /etc/ircd-hybrid-ssl-built ]
then
    echo 'ircd-hybrid with ssl support already built'
else
    echo 'building ircd-hybrid with ssl support'
    apt-get source ircd-hybrid
    sed -i 's/^\(MAXCLIENTS.*\)$/\1\nUSE_OPENSSL = 1/g' ircd-hybrid-*/debian/rules
    cd ircd-hybrid-*
    dpkg-buildpackage -rfakeroot -uc -b &> /var/log/ircd-hybrid-build.out
    BUILD_RESULT=$?
    cd ../
    mv /var/tmp/ircd-hybrid*.deb /var/tmp/ircd-hybrid_ssl.deb
    date > /etc/ircd-hybrid-ssl-built
    echo 'installing ircd-hybrid with ssl support'
    dpkg -i /var/tmp/ircd-hybrid_ssl.deb 2>&1 /var/tmp/ircd-hybrid_ssl.install.log
fi

exit $BUILD_RESULT
