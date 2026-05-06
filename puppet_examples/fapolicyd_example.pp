# 1. Install the daemon
package { 'fapolicyd':
  ensure => installed,
}

# 2. Manage the main configuration file
file { '/etc/fapolicyd/fapolicyd.conf':
  ensure  => file,
  owner   => 'root',
  group   => 'fapolicyd',
  mode    => '0644',
  # Using a simple string for this example, but usually managed via a template
  content => "permissive = 0\nintegrity = sha256\n", 
  require => Package['fapolicyd'],
  notify  => Service['fapolicyd'], # Restart service if this file changes
}

# 3. Ensure the service is running and enabled at boot
service { 'fapolicyd':
  ensure  => running,
  enable  => true,
  require => File['/etc/fapolicyd/fapolicyd.conf'],
}

# 4. Optional: Refresh the trust database after policy changes
exec { 'fapolicyd-db-update':
  command     => '/usr/sbin/fapolicyd-cli --update',
  refreshonly => true,
  subscribe   => File['/etc/fapolicyd/fapolicyd.conf'],
}