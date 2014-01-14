
# variables

$sublime_version    = '2.0.2'
$ircd_port          = 6667
$ircd_ssl_port      = 6669
$ircd_server_passwd = 'subliminal'

$client_privkey = 'client.privkey.pem'
$client_pubkey  = 'client.pubkey.pub'

$accounts_config = "{
    \"subliminal_collaborator\": {
        \"irc\": [
            {
                \"host\": \"localhost\",
                \"port\": ${ircd_port},
                \"username\": \"vagrant\",
                \"password\": \"${ircd_server_passwd}\",
                \"channel\": \"subliminalcollaboration\"
            }
        ],
        \"irc\": [
            {
                \"host\": \"localhost\",
                \"port\": ${ircd_ssl_port},
                \"useSSL\": true
                \"username\": \"vagrant_ssl\",
                \"password\": \"${ircd_server_passwd}\",
                \"channel\": \"subliminalcollaboration\"
            }
        ],
        \"connect_all_on_startup\": false
    }
}
"

# make sure to open up the firewall ports
# we don't care about any other firewall config

class { 'firewall': } ->
firewall { '100 allow ircd regular and ssl access':
    port   => [$ircd_port, $ircd_ssl_port],
    proto  => tcp,
    action => accept,
}

# setup sublime text

class { 'sublime_text':
    sublime_version => $sublime_version
}

class { 'subliminal_collaborator':
    accounts_config => $accounts_config
}

include x11

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
