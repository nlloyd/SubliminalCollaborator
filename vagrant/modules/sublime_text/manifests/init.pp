class sublime_text (
    $sublime_version
) {

    # setup sublime text

    $sublime_version_bits = split($sublime_version, '[.]')
    $sublime_major_version = $sublime_version_bits[0]

    exec { "wget http://c758482.r82.cf2.rackcdn.com/Sublime%20Text%20${sublime_version}%20x64.tar.bz2":
        cwd     => '/var/tmp',
        creates => '/var/tmp/Sublime Text ${sublime_version} x64.tar.bz2',
        path    => ["/bin", "/usr/bin", "/usr/sbin"]
    } ->
    exec { "tar xjf \"/var/tmp/Sublime Text ${sublime_version} x64.tar.bz2\"":
        cwd     => '/opt',
        creates => '/opt/Sublime Text ${sublime_major_version}',
        path    => ["/bin", "/usr/bin", "/usr/sbin"]
    } -> 
    file { "/usr/bin/sublime":
        ensure    => link,
        target    => "/opt/Sublime Text ${sublime_major_version}/sublime_text",
        mode      => 'a+x'
    }

}