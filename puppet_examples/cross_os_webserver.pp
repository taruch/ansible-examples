# Install the right Apache package depending on OS family.
# Puppet uses the `$facts` hash; case/selector picks the package name.

$webserver_pkg = $facts['os']['family'] ? {
  'RedHat' => 'httpd',
  'Debian' => 'apache2',
  default  => fail("Unsupported OS family: ${facts['os']['family']}"),
}

package { $webserver_pkg:
  ensure => installed,
}

service { $webserver_pkg:
  ensure  => running,
  enable  => true,
  require => Package[$webserver_pkg],
}
