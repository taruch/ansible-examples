# Example: Ensuring SSH security
service { 'sshd':
  ensure => running,
  enable => true,
}

file_line { 'disable_root_login':
  path  => '/etc/ssh/sshd_config',
  line  => 'PermitRootLogin no',
  match => '^#?PermitRootLogin',
  notify => Service['sshd'],
}