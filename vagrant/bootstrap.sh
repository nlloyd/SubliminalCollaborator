#!/bin/bash

# from http://blog.doismellburning.co.uk/2013/01/19/upgrading-puppet-in-vagrant-boxes/

apt-get install --yes lsb-release
DISTRIB_CODENAME=$(lsb_release --codename --short)
DEB="puppetlabs-release-${DISTRIB_CODENAME}.deb"
DEB_PROVIDES="/etc/apt/sources.list.d/puppetlabs.list" # Assume that this file's existence means we have the Puppet Labs repo added

if [ ! -e $DEB_PROVIDES ]
then
    # Print statement useful for debugging, but automated runs of this will interpret any output as an error
    # print "Could not find $DEB_PROVIDES - fetching and installing $DEB"
    wget -q http://apt.puppetlabs.com/$DEB
    sudo dpkg -i $DEB
fi

sudo apt-get update

if [ -e /etc/puppet-updated ]
then
    echo 'puppet already updated'
else
    sudo apt-get install --yes puppet
    date > /etc/puppet-updated
fi

####
if [ -e /etc/puppet-stdlib-installed ]
then
    echo 'puppetlabs/stdlib already installed'
else
    puppet module install puppetlabs/stdlib
    date > /etc/puppet-stdlib-installed
fi
