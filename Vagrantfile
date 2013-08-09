Vagrant.configure("2") do |config|

  # config.vm.box = "precise64"
  config.vm.box = "centos-64-x64-vbox4210-nocm"
  config.vm.box_url = "http://puppet-vagrant-boxes.puppetlabs.com/centos-64-x64-vbox4210-nocm.box"
  # config.vm.box = "fedora-18-x64-vbox4210-nocm"
  # config.vm.box_url = "http://puppet-vagrant-boxes.puppetlabs.com/fedora-18-x64-vbox4210-nocm.box"

  config.vm.hostname = "subliminal.local"
  config.vm.network :private_network, type: :dhcp
  config.vm.network :forwarded_port, host: 6667, guest: 6667
  config.vm.network :forwarded_port, host: 6669, guest: 6669

  config.ssh.forward_x11 = true

  # Share an additional folder to the guest VM. The first argument is
  # the path on the host to the actual folder. The second argument is
  # the path on the guest to mount the folder. And the optional third
  # argument is a set of non-required options.
  # config.vm.synced_folder "../data", "/vagrant_data"

  config.vm.provision :shell, :path => "vagrant/bootstrap.sh"

  config.vm.provision :puppet do |puppet|
    puppet.options = "--verbose --debug"
    puppet.manifests_path = "vagrant/manifests"
    puppet.module_path = "vagrant/modules"
    puppet.hiera_config_path = "vagrant/hiera.yaml"
  end

end
