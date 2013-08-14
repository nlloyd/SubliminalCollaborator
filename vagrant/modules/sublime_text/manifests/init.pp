class sublime_text (
    $sublime_version
) {

    # setup sublime text 2

    exec { "wget http://c758482.r82.cf2.rackcdn.com/Sublime%20Text%20${sublime_version}%20x64.tar.bz2":
        cwd     => '/var/tmp',
        creates => '/var/tmp/Sublime Text ${sublime_version} x64.tar.bz2',
        path    => ["/bin", "/usr/bin", "/usr/sbin"]
    } ->
    exec { "tar xjf \"/var/tmp/Sublime Text ${sublime_version} x64.tar.bz2\"":
        cwd     => '/opt',
        creates => '/opt/Sublime Text ${sublime_version}',
        path    => ["/bin", "/usr/bin", "/usr/sbin"]
    } -> 
    file { "/usr/bin/sublime":
        ensure    => link,
        target    => "/opt/Sublime Text ${sublime_version}/sublime_text",
        mode      => 'a+x'
    }

    # x11 dependencies

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

    package { "gnu-free-mono-fonts":
        ensure  => present
    }

    package { "gnu-free-sans-fonts":
        ensure  => present
    }

    package { "gnu-free-serif-fonts":
        ensure  => present
    }

    package { "gtk2":
        ensure  => present
    }

    package { "dbus":
        ensure  => present
    }

    package { "dbus-x11":
        ensure  => present
    }

    service { "messagebus":
        ensure      => running,
        enable      => true,
        hasstatus   => true,
        require     => Package[dbus]
    }

}