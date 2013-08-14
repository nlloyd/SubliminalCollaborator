class x11 {

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
