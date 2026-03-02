# Vagrantfile to spin up an Ubuntu VM and provision the patch agent for demo
Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/focal64"
  # create a host-only network so the VM has a reachable IP
  config.vm.network "private_network", ip: "192.168.122.10"
  # also forward the agent and metrics ports to the host for convenience
  config.vm.network "forwarded_port", guest: 8080, host: 8080
  config.vm.network "forwarded_port", guest: 9100, host: 9100
  config.vm.synced_folder ".", "/vagrant"
  config.vm.provision "shell", path: "scripts/vagrant_provision.sh"
end
