# == Class: inspircd
#
# Install, configure and run InspIRCd.
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
class inspircd {
  include inspircd::package
  include inspircd::config
  include inspircd::service
}
