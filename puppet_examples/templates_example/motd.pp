# Render /etc/motd from an ERB template.
# Variables in scope here are exposed to the template as @var_name.
# In a real Puppet codebase this would live inside a class in a module so that
# `template('module_name/motd.erb')` can locate the .erb file.

$env_name         = 'production'
$maintenance_mode = false
$fqdn             = $facts['networking']['fqdn']
$os_family        = $facts['os']['family']
$os_release       = $facts['os']['release']['major']

file { '/etc/motd':
  ensure  => file,
  owner   => 'root',
  group   => 'root',
  mode    => '0644',
  content => template('profile/motd.erb'),
}
