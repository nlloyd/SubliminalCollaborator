# == Class: inspircd::config
#
# Create configuration files for InspIRCd, based on default settings
# from inspircd::params and hiera.
#
# === Parameters
#
# None
#
# === Authors
#
# Evgeni Golov <evgeni@golov.de>
#
# === Copyright
#
# Copyright 2013 Evgeni Golov
#
class inspircd::config (
  $ensure      = hiera('ensure', $inspircd::params::ensure),
  $servername  = hiera('servername', $inspircd::params::servername),
  $network     = hiera('network', $inspircd::params::network),
  $description = hiera('description', $inspircd::params::description),
  $networkname = hiera('networkname', $inspircd::params::networkname),
  $adminname   = hiera('adminname', $inspircd::params::adminname),
  $adminemail  = hiera('adminemail', $inspircd::params::adminemail),
  $adminnick   = hiera('adminnick', $inspircd::params::adminnick),
  $ips         = hiera('ips', $inspircd::params::ips),
  $opers       = hiera('opers', $inspircd::params::opers),
  $ssl         = hiera('ssl', $inspircd::params::ssl),
  $sslonly     = hiera('sslonly', $inspircd::params::sslonly),
  $cafile      = hiera('cafile', $inspircd::params::cafile),
  $certfile    = hiera('certfile', $inspircd::params::certfile),
  $keyfile     = hiera('keyfile', $inspircd::params::keyfile),
  $ldapauth    = hiera('ldapauth', $inspircd::params::ldapauth),
) inherits inspircd::params {
  file { '/etc/inspircd/inspircd.conf':
    ensure  => $ensure,
    owner   => 'irc',
    group   => 'irc',
    mode    => '0400',
    content => template('inspircd/inspircd.conf.erb'),
    require => Package['inspircd'],
    notify  => Class['inspircd::service'],
  }

  file { '/etc/default/inspircd':
    ensure  => $ensure,
    owner   => 'irc',
    group   => 'irc',
    mode    => '0400',
    source  => 'puppet:///modules/inspircd/default',
    require => Package['inspircd'],
    notify  => Class['inspircd::service'],
  }
}
