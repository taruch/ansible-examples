group { 'deploy':
  ensure => present,
  gid    => 2001,
}

user { 'app_user':
  ensure     => present,
  uid        => '2001',
  gid        => 'deploy',
  shell      => '/bin/bash',
  home       => '/home/app_user',
  managehome => true,
}