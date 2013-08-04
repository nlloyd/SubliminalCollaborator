# Class: irc::config
#
# Description
#  This class is designed to configure the system to use IRC after packages have been deployed
#
# Parameters:
#  $network_name: The FQDN of the host where this server will reside.
#  $network_desc: A friendly descriptor of the IRC server
#  $admin_name: Friendly name of the Admin of the IRC server
#  $admin_email: Email address of the Admin
#  $listen_ip: Default IP for IRCD to listen on. Defaults to 127.0.0.1 if not set.
#  $auth_domains: domains that are authorized to be in the local user class.
#  $spoof_domain: domain used to spoof users that do not have domains.
#  $operator_name: admin account for IRC management
#  $operator_pass: admin password for IRC management.
# 
# Actions:
#  - Configures IRCD
#
# Requires:
#  This module has no requirements
#
# Sample Usage:
#  This module should not be called directly.
class irc::config(
  $network_name,
  $network_desc,
  $admin_name,
  $admin_email,
  $listen_ip,
  $auth_domains,
  $spoof_domain,
  $operator_name,
  $operator_pass,
  $module_paths
) {
  File {
    owner => 'root',
    group => 'root',
    mode  => '0644',
  }
  file { "${irc::params::ic_conf_dir}/ircd.conf":
    ensure  => file,
    content => template('irc/etc/ircd/ircd.conf.erb')
  }
}
