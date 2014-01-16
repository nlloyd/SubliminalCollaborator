class x11 {

    $packages = [
        'xorg-x11-server-Xorg',
        'xorg-x11-apps',
        'xorg-x11-utils',
        'xorg-x11-xdm',
        'xorg-x11-xkb-utils',
        'gnu-free-mono-fonts',
        'gnu-free-sans-fonts',
        'gnu-free-serif-fonts',
        'gtk2',
        'dbus',
        'dbus-x11',
    ]

    anchor { 'x11::begin': } ->
    package { $packages:
        ensure  => present
    }

    service { "messagebus":
        ensure      => running,
        enable      => true,
        hasstatus   => true,
        require     => Package[dbus]
    } ->
    anchor { 'x11::end': }

}
