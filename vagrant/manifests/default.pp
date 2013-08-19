
# variables

$sublime_version    = '2.0.2'
$ircd_port          = 6667
$ircd_ssl_port      = 6669
$ircd_server_passwd = 'subliminal'

$client_privkey = 'client.privkey.pem'
$client_pubkey  = 'client.pubkey.pub'

$accounts_config = '{
    "subliminal_collaborator": {
        "irc": [
            {
                "host": "localhost",
                "port": 6667,
                "username": "vagrant",
                "password": "${ircd_server_passwd}",
                "channel": "subliminalcollaboration"
            }
        ],
        "connect_all_on_startup": false
    }
}
'

# setup sublime text

class { 'sublime_text':
    sublime_version => $sublime_version
}

include x11

# setup subliminal collaborator and configuration
# we need to install x11 xvfb then launch sublime, quiting immediately, to
# generate the base Packages structure

package { 'xorg-x11-server-Xvfb':
    ensure  => present
} ->
exec { 'xvfb-run sublime --command exit':
    path            => [ '/bin', '/usr/bin' ],
    user            => 'vagrant',
    environment     => [ 'HOME=/home/vagrant' ],
    creates         => '/home/vagrant/.config',
    require         => [ Class['sublime_text'], Class['x11'] ]
} ->
file { "/home/vagrant/.config/sublime-text-2/Packages/SubliminalCollaborator":
    ensure  => link,
    target  => "/vagrant",
    require => Exec['xvfb-run sublime --command exit']
} ->
file { '/home/vagrant/.config/sublime-text-2/Packages/User/Accounts.sublime-settings':
    ensure  => file,
    content => $accounts_config
}

file { "/home/vagrant/${client_privkey}":
    ensure  => present,
    mode    => '0600',
    source  => "puppet:///modules/ssl_client/${client_privkey}"
}

# setup an ircd with ssl

class { 'irc_server':
    server_name     => 'irc.subliminal.local',
    server_password => $ircd_server_passwd,
    oper_name       => 'subliminal-op',
    oper_password   => 'imtheop',
    ports           => [$ircd_port],
    ssl_ports       => [$ircd_ssl_port],
    interfaces      => ['0.0.0.0']
}

firewall { '100 allow ircd regular and ssl access':
    port   => [$ircd_port, $ircd_ssl_port],
    proto  => tcp,
    action => accept,
}

# firewall basic setup

resources { "firewall":
    purge   => true
}

Firewall {
  before  => Class['subliminal_firewall::post'],
  require => Class['subliminal_firewall::pre'],
}

class { ['subliminal_firewall::pre', 'subliminal_firewall::post']: }
class { 'firewall': }
