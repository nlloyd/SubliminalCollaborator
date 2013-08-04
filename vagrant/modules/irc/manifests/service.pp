# Class: irc::service
#
# This module manages irc service management
#
# Parameters:
#
# There are no default parameters for this class.
#
# Actions:
#
# Requires:
#
# Sample Usage:
#
# This class file is not called directly
class irc::service {
  service { $irc::params::ic_daemon:
    ensure    => 'running',
    enable    => 'true',
    hasstatus => 'false',
  }
}
