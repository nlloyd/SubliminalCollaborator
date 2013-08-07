#!/bin/bash

if [ -e /etc/puppet-installed ]
then
    echo 'puppet already installed'
else
    rpm -ivh http://yum.puppetlabs.com/el/6/products/x86_64/puppetlabs-release-6-7.noarch.rpm
    yum -y install puppet
    date > /etc/puppet-installed
fi

####
if [ -e /etc/puppet-stdlib-installed ]
then
    echo 'puppetlabs/stdlib already installed'
else
    puppet module install puppetlabs/stdlib
    date > /etc/puppet-stdlib-installed
fi
