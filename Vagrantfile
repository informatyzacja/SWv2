$msg_up = <<MSG_UP
--------------------------------------------------------

System Wyborczy v2

    - Panel administratora:
          http://localhost:8080/admin

    - Konsola maszyny wirtualnej:
          $ vagrant ssh

--------------------------------------------------------
MSG_UP

$msg_ssh = <<MSG_SSH
--------------------------------------------------------

System Wyborczy v2

    Panel administratora:
        http://localhost:8080/admin

    Logi:
        $ sw-logs

    Restart usług:
        $ sw-restart

    Status usług:
        $ sw-status

--------------------------------------------------------
MSG_SSH

Vagrant.configure("2") do |config|
  config.vm.box = "generic/debian11"
  config.vm.host_name = "system-wyborczy-development"

  # Use a script to provision the VM
  config.vagrant.plugins = [ "vagrant-vbguest" ]
  config.vm.provision :shell, path: "bootstrap.sh", run: "always"

  # Only reset the database when provisioning explicitly
  config.vm.provision :shell, path: "sw-database/resetdb.sh"

  # Mount the repository at /opt/sw
  config.vm.synced_folder ".", "/opt/sw", owner: "www-data", group: "www-data"

  # Forward ports for openresty
  # it's important for these ports to be the same, as otherwise nginx/openresty redirects redirect to the wrong port
  config.vm.network "forwarded_port", guest: 8080, host: 8080, host_ip: "127.0.0.1", auto_correct: false

  config.vm.post_up_message = $msg_up

  VAGRANT_COMMAND = ARGV[0]
  if VAGRANT_COMMAND == "ssh"
    # Change the default ssh username to root
    config.ssh.username = "root"

    # Default directory if no extra arguments: /opt/sw
    if ARGV.length == 1
      config.ssh.extra_args = ["-t", "cd /opt/sw; echo '#{$msg_ssh}'; exec bash --login"]
    end
  end
end
