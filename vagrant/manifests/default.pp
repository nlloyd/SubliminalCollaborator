
exec { "wget http://c758482.r82.cf2.rackcdn.com/Sublime%20Text%202.0.2%20x64.tar.bz2":
    cwd     => '/var/tmp',
    creates => '/var/tmp/Sublime Text 2.0.2 x64.tar.bz2',
    path    => ["/bin", "/usr/bin", "/usr/sbin"]
} ->
exec { "tar xjf \"/var/tmp/Sublime Text 2.0.2 x64.tar.bz2\"":
    cwd     => '/opt',
    creates => '/opt/Sublime Text 2',
    path    => ["/bin", "/usr/bin", "/usr/sbin"]
} -> 
file { "/usr/bin/sublime":
    ensure    => link,
    target    => "/opt/Sublime Text 2/sublime_text",
    mode      => 'a+x'
}

package { "xorg-x11-server-Xorg":
    ensure  => present
}

package { "xorg-x11-apps":
    ensure  => present
}

package { "xorg-x11-utils":
    ensure  => present
}

package { "xorg-x11-xdm":
    ensure  => present
}

package { "xorg-x11-xkb-utils":
    ensure  => present
}

package { "xorg-x11-fonts-75dpi":
    ensure  => present
}

package { "xorg-x11-fonts-100dpi":
    ensure  => present
}

package { "dbus":
    ensure  => present
}

package { "dbus-x11":
    ensure  => present
}

service { "dbus":
    ensure      => running,
    enable      => true,
    hasstatus   => true,
    require     => Package[dbus]
}

# setup an ircd with ssl

class {'irc_server':
    server_name     => 'irc.subliminal.local',
    server_password => 'subliminal',
    oper_name       => 'subliminal-op',
    oper_password   => 'imtheop',
    ports           => [6667],
    ssl_ports       => [6669],
    interfaces      => ['0.0.0.0']
}
