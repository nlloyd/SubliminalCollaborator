
exec { "wget http://c758482.r82.cf2.rackcdn.com/Sublime%20Text%202.0.1%20x64.tar.bz2":
    cwd     => '/var/tmp',
    creates => '/var/tmp/Sublime Text 2.0.1 x64.tar.bz2',
    path    => ["/bin", "/usr/bin", "/usr/sbin"]
} ->
exec { "tar xjf \"/var/tmp/Sublime Text 2.0.1 x64.tar.bz2\"":
    cwd     => '/opt',
    creates => '/opt/Sublime Text 2',
    path    => ["/bin", "/usr/bin", "/usr/sbin"]
} -> 
file { "/usr/bin/sublime":
    ensure    => link,
    target    => "/opt/Sublime Text 2/sublime_text",
    mode      => 'a+x'
}

package { "libgtk2.0-0":
    ensure  => present
}

package { "xorg":
    ensure  => present
}
