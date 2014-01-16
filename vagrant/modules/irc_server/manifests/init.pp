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

    file { 'ngircd_conf_path':
        path    => '/etc/ngircd',
        ensure  => directory,
    }

    file { 'server_cert':
        path    => '/etc/ngircd/server.crt',
        source  => 'puppet:///modules/irc_server/server.crt',
        require => File['ngircd_conf_path'],
    }

    file { 'server_key':
        path    => '/etc/ngircd/server.key',
        source  => 'puppet:///modules/irc_server/server.key',
        require => File['ngircd_conf_path'],
    }

    file { 'ngircd_conf':
        path    => '/etc/ngircd.conf',
        content => template('irc_server/ngircd.conf.erb'),
        require => File['ngircd_conf_path'],
    }

    service { 'ngircd':
        enable  => true,
        ensure  => running,
        require => [ Package['ngircd'], File['ngircd_conf','server_cert','server_key'] ],
    }

    anchor { 'irc_server::begin': } -> Package['ngircd']

    Service['ngircd'] -> anchor { 'irc_server::end': }
}
