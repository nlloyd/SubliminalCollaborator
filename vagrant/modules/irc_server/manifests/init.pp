class irc_server (
    $server_name,
    $server_password,
    $oper_name,
    $oper_password,
    $ports,
    $ssl_ports,
    $interfaces
) {
    group {'ngircd':
        ensure => present,
    }

    user { 'ngircd':
        gid     => 'ngircd',
        system  => true,
        require => [
            Group['ngircd'],
        ]
    }

    ## EPEL package
    package {'ngircd':
        require => User['ngircd'],
    }

    File {
        owner   => 'ngircd',
        group   => 'ngircd',
        mode    => 0600,
        notify  => Service['ngircd'],
        require => Package['ngircd'],
    }

    file {'/etc/ngircd':
        ensure => directory,
    }

    file {'/etc/ngircd/server.crt':
        source => 'puppet:///modules/irc_server/server.crt',
    }

    file {'/etc/ngircd/server.key':
        source => 'puppet:///modules/irc_server/server.key',
    }

    file {'/etc/ngircd.conf':
        content => template('irc_server/ngircd.conf.erb'),
    }

    service {'ngircd':
        enable  => true,
        ensure  => running,
        require => Package['ngircd'],
    }
}
