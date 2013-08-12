
class subliminal_firewall::pre {

    Firewall {
        require => undef,
    }


    # Default firewall rules
    firewall { '000 accept related established rules':
        proto   => 'all',
        state   => ['RELATED', 'ESTABLISHED'],
        action  => 'accept',
    } ->
    firewall { '001 accept icmp anywhere':
        proto   => 'icmp',
        action  => 'accept',
    } ->
    firewall { '002 accept all anywhere':
        proto   => 'all',
        action  => 'accept',
    } ->
    firewall { '003 accept tcp new ssh':
        proto   => 'tcp',
        state   => 'NEW',
        dport   => 22,
        action  => 'accept',
    } ->
    firewall { '004 reject reject-with icmp-host-prohibited':
        proto   => 'all',
        reject  => 'icmp-host-prohibited',
        action  => 'reject',
    } ->
    firewall { '005 fwd reject reject-with icmp-host-prohibited':
        proto   => 'all',
        reject  => 'icmp-host-prohibited',
        action  => 'reject',
        chain   => 'FORWARD',
    }

}