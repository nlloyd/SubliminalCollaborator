# == Class: inspircd::params
#
# Default parameters to be used in the inspircd class.
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
class inspircd::params {
  case $::osfamily {
    Debian: { }
    default: {
      fail('This module only supports Debian-based systems')
    }
  }
  $ensure         = present
  $ensure_enable  = true
  $ensure_running = running
  $servername     = $::fqdn
  $network        = $servername
  $description    = 'InspIRCd server'
  $networkname    = 'localnet'
  $adminname      = 'root rootsen'
  $adminnick      = 'root'
  $adminemail     = "root@${::domain}"
  $ips            = ['127.0.0.1', $::ipaddress]
  $opers          = []
  $ssl            = undef
  $sslonly        = false
  $cafile         = undef
  $certfile       = undef
  $keyfile        = undef
  $ldapauth       = undef
  $use_backport   = false
}
