# Manages an nginx webserver with a templated landing page.
class webserver (
  String  $package_name  = 'nginx',
  String  $service_name  = 'nginx',
  String  $document_root = '/usr/share/nginx/html',
  String  $site_title    = 'Default site',
  Integer $listen_port   = 80,
) {
  package { $package_name:
    ensure => installed,
  }

  file { "${document_root}/index.html":
    ensure  => file,
    owner   => 'root',
    group   => 'root',
    mode    => '0644',
    content => template('webserver/index.html.erb'),
    require => Package[$package_name],
    notify  => Service[$service_name],
  }

  service { $service_name:
    ensure  => running,
    enable  => true,
    require => Package[$package_name],
  }
}
