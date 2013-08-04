
# exec { "wget http://c758482.r82.cf2.rackcdn.com/Sublime%20Text%202.0.2%20x64.tar.bz2":
#     cwd     => '/var/tmp',
#     creates => '/var/tmp/Sublime Text 2.0.2 x64.tar.bz2',
#     path    => ["/bin", "/usr/bin", "/usr/sbin"]
# } ->
# exec { "tar xjf \"/var/tmp/Sublime Text 2.0.2 x64.tar.bz2\"":
#     cwd     => '/opt',
#     creates => '/opt/Sublime Text 2',
#     path    => ["/bin", "/usr/bin", "/usr/sbin"]
# } -> 
# file { "/usr/bin/sublime":
#     ensure    => link,
#     target    => "/opt/Sublime Text 2/sublime_text",
#     mode      => 'a+x'
# }

# package { "libgtk2.0-0":
#     ensure  => present
# }

# package { "xorg":
#     ensure  => present
# }

# package { "dbus":
#     ensure  => present
# }

# package { "dbus-x11":
#     ensure  => present
# }

# service { "dbus":
#     ensure      => running,
#     enable      => true,
#     hasstatus   => true,
#     require     => Package[dbus]
# }

# ircd

package { 'inspircd':
    ensure  => present
}

# $ircd_build_dependencies = [
#     'openssl',
#     'libssl-dev',
#     'dpkg-dev',
#     'debhelper',
#     'dpatch',
#     'docbook-to-man',
#     'flex',
#     'bison',
#     'libpcre3-dev'
#     ]

# package { $ircd_build_dependencies:
#     ensure  => present
# }

# need to rebuild ircd-hybrid to include ssl support
# following instructions found here: https://marvelserv.com/setting-up-ircd-hybrid-and-hybserv-services-with-ssl-on-ubuntu/

# $ircd_builder_script = 'build_and_install_ssl_ircd.sh'

# package { 'whois':
#     ensure  => present
# } ->
# file { "/var/tmp/${ircd_builder_script}":
#     ensure  => present,
#     mode    => 'a+x',
#     source  => "puppet:///modules/irc/${ircd_builder_script}"
# } ->
# exec { "/var/tmp/${ircd_builder_script}":
#     cwd     => '/var/tmp',
#     path    => ["/bin", "/usr/bin", "/usr/sbin"],
#     require => Package[$ircd_build_dependencies]
# }


# class { 'irc':
#     network_name  => $hostname,
#     network_desc  => 'SubliminalCollaborator Test IRC Server',
#     admin_name    => 'Faux Admin',
#     admin_email   => "faux.admin@${hostname}",
#     listen_ip     => "0.0.0.0",
#     auth_domains  => [$hostname],
#     spoof_domain  => $hostname,
#     operator_name => 'admin',
#     operator_pass => 'password',
# }
