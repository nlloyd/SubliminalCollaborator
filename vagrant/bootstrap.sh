#!/bin/bash

# install EPEL repo
if [ -e /etc/epel-repo-installed ]
then
    echo 'epel repo installed'
else
    rpm -ivh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
    date > /etc/epel-repo-installed
fi

# install puppet
if [ -e /etc/puppet-installed ]
then
    echo 'puppet already installed'
else
    rpm -ivh http://yum.puppetlabs.com/el/6/products/x86_64/puppetlabs-release-6-7.noarch.rpm
    yum -y install puppet
    date > /etc/puppet-installed
fi

# install puppetlabs/stdlib
if [ -e /etc/puppet-stdlib-installed ]
then
    echo 'puppetlabs/stdlib already installed'
else
    puppet module install puppetlabs/stdlib
    date > /etc/puppet-stdlib-installed
fi
