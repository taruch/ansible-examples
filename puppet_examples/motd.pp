file { '/etc/motd':
  ensure  => file,
  owner   => 'root',
  group   => 'root',
  mode    => '0644',
  content => "Welcome to this server!\nThis system is managed by Puppet.\n",
}