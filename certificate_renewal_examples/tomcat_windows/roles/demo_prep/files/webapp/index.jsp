<%@ page contentType="text/html;charset=UTF-8" %>
<!DOCTYPE html>
<html>
<head><title>Cert Renewal Demo</title></head>
<body>
<h1>Hello from Tomcat on Windows</h1>
<p>This tiny app exists so the certificate-renewal demo has something to serve over HTTPS.</p>
<ul>
  <li>Time: <%= new java.util.Date() %></li>
  <li>Scheme: <%= request.getScheme() %></li>
  <li>Server port: <%= request.getServerPort() %></li>
  <li>Server info: <%= application.getServerInfo() %></li>
</ul>
</body>
</html>
