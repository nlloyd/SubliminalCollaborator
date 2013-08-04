# == Class: inspircd::service
#
# Define a service for InspIRCd.
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
class inspircd::service (
  $ensure_enable  = hiera('ensure_enable', $inspircd::params::ensure_enable),
  $ensure_running = hiera('ensure_running', $inspircd::params::ensure_running),
) inherits inspircd::params {
  service { 'inspircd':
    ensure     => $ensure_running,
    enable     => $ensure_enable,
    hasrestart => true,
    restart    => '/etc/init.d/inspircd reload',
    hasstatus  => true,
    require    => Class['inspircd::config'],
  }
}
