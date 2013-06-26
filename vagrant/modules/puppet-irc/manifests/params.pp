# Class: irc::params
#
# Description
#   This class is designed to carry default parameters for 
#   Class: irc.  
#
# Parameters:
#  $ic_packages: Packages needed to install ircd-hybrid
#  $ic_conf_dir: Directory where configs are kept for ircd-hybrid
#  $ic_daemon: daemon name for ircd-hybrid
#  $ic_module_paths: path where ircd-hybrid modules are maintained if not configured at runtime. 
#  $ic_network_name: The FQDN of the host where this server will reside if not configured at runtime. 
#  $ic_network_desc: A friendly descriptor of the IRC server if not configured at runtime. 
#  $ic_admin_name: Friendly name of the Admin of the IRC server if not configured at runtime. 
#  $ic_admin_email: Email address of the Admin if not configured at runtime. 
#  $ic_listen_ip: Default IP for IRCD to listen on if not configured at runtime. 
#  $ic_auth_domains: domains that are authorized to be in the local user class if not configured at runtime. 
#  $ic_spoof_domain: domain used to spoof users that do not have domains if not configured at runtime. 
#  $ic_operator_name: admin account for IRC management if not configured at runtime. 
#  $ic_operator_pass: admin password for IRC management if not configured at runtime. 
#
# Actions:
#   This module does not perform any actions.
#
# Requires:
#   This module has no requirements.   
#
# Sample Usage:
#   This method should not be called directly.
class irc::params {
  
  # Per OS Configuration Options
  case $::operatingsystem {
    redhat,fedora,centos: {
      $ic_packages = ['ircd-hybrid']
      $ic_conf_dir = '/etc/ircd'
      $ic_daemon   = 'ircd'
      $ic_module_paths   = ['/usr/local/ircd/modules', '/usr/local/ircd/modules/autoload']
    }
    ubuntu,debian: {
      $ic_packages     = ['ircd-hybrid', 'whois']
      $ic_conf_dir     = '/etc/ircd-hybrid'
      $ic_daemon       = 'ircd-hybrid'
      $ic_module_paths = ['/usr/lib/ircd-hybrid/modules', '/usr/lib/ircd-hybird/modules/autoload']
    }
  }

  ## General Configuration
  $ic_network_name  = 'localhost.localdomain'
  $ic_network_desc  = 'Brand New Unconfigured IRC Server!'
  $ic_admin_name    = 'root'
  $ic_admin_email   = 'root@localhost'
  $ic_listen_ip     = '127.0.0.1'
  $ic_auth_domains  = ['localhost', 'localhost.localdomain']
  $ic_spoof_domain  = 'localhost.localdomain'
  $ic_operator_name = 'god'
  $ic_operator_pass = 'password123'
}
