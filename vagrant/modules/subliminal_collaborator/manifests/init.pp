## SubliminalCollaborator plugin setup manifest
class subliminal_collaborator (
    $accounts_config,
) {
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
    file { 'account_config':
        path    => '/home/vagrant/.config/sublime-text-2/Packages/User/Accounts.sublime-settings',
        ensure  => file,
        content => $accounts_config
    }

    file { 'ssl_client_key':
        path    => "/home/vagrant/${client_privkey}",
        ensure  => present,
        mode    => '0600',
        source  => "puppet:///modules/ssl_client/${client_privkey}"
    }

    anchor { 'subliminal_collaborator::begin': } -> Package['xorg-x11-server-Xvfb']
    File['account_config','ssl_client_key'] -> anchor { 'subliminal_collaborator::end': }
}
