<%@ page contentType="text/html;charset=UTF-8" %>
<%@ page import="java.net.InetSocketAddress" %>
<%@ page import="java.security.cert.X509Certificate" %>
<%@ page import="java.text.SimpleDateFormat" %>
<%@ page import="java.util.Date" %>
<%@ page import="java.util.TimeZone" %>
<%@ page import="javax.net.ssl.*" %>
<%!
    // Self-introspect: open a TLS socket to localhost on the same port the
    // request came in on, read the server cert, and return its key fields.
    // Trust manager accepts any cert because we're inspecting our own server,
    // not authenticating it.
    static String[] readLiveCert(int port) {
        try {
            SSLContext ctx = SSLContext.getInstance("TLS");
            ctx.init(null, new TrustManager[] { new X509TrustManager() {
                public X509Certificate[] getAcceptedIssuers() { return new X509Certificate[0]; }
                public void checkClientTrusted(X509Certificate[] c, String a) {}
                public void checkServerTrusted(X509Certificate[] c, String a) {}
            }}, new java.security.SecureRandom());
            try (SSLSocket sock = (SSLSocket) ctx.getSocketFactory().createSocket()) {
                sock.connect(new InetSocketAddress("127.0.0.1", port), 3000);
                sock.startHandshake();
                X509Certificate cert = (X509Certificate) sock.getSession().getPeerCertificates()[0];
                SimpleDateFormat fmt = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss z");
                fmt.setTimeZone(TimeZone.getTimeZone("UTC"));
                long days = (cert.getNotAfter().getTime() - System.currentTimeMillis())
                            / (1000L * 60 * 60 * 24);
                return new String[] {
                    cert.getSubjectX500Principal().getName(),
                    cert.getIssuerX500Principal().getName(),
                    fmt.format(cert.getNotBefore()),
                    fmt.format(cert.getNotAfter()),
                    String.valueOf(days)
                };
            }
        } catch (Exception e) {
            return new String[] { "(error reading cert)", e.getClass().getSimpleName() + ": " + e.getMessage(), "?", "?", "?" };
        }
    }
%>
<%
    String[] c = readLiveCert(request.getServerPort());
    String subject = c[0], issuer = c[1], notBefore = c[2], notAfter = c[3], daysLeft = c[4];
    String cls = "expired";
    try {
        long d = Long.parseLong(daysLeft);
        cls = d > 30 ? "fresh" : (d > 0 ? "warn" : "expired");
    } catch (NumberFormatException ignored) { cls = "warn"; }
%>
<!DOCTYPE html>
<html>
<head>
<title>Cert Renewal Demo</title>
<style>
  body { font-family: -apple-system, system-ui, sans-serif; max-width: 760px; margin: 2em auto; padding: 0 1em; color: #222; }
  h1 { margin-bottom: 0.2em; }
  .box { background: #f4f4f6; border-radius: 6px; padding: 1em 1.2em; margin-top: 1em; }
  .box h2 { margin-top: 0; font-size: 1.1em; }
  dl { margin: 0; display: grid; grid-template-columns: max-content 1fr; gap: 0.3em 1em; }
  dt { font-weight: 600; }
  dd { margin: 0; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.92em; word-break: break-all; }
  .fresh { color: #1b7f3b; font-weight: 600; }
  .warn  { color: #b27000; font-weight: 600; }
  .expired { color: #c62828; font-weight: 600; }
</style>
</head>
<body>
<h1>Hello from Tomcat on Windows</h1>
<p>This tiny app exists so the certificate-renewal demo has something to serve over HTTPS.</p>

<div class="box">
<h2>Live TLS certificate</h2>
<dl>
  <dt>Subject</dt><dd><%= subject %></dd>
  <dt>Issuer</dt><dd><%= issuer %></dd>
  <dt>Valid from</dt><dd><%= notBefore %></dd>
  <dt>Expires</dt><dd><%= notAfter %></dd>
  <dt>Days remaining</dt><dd class="<%= cls %>"><%= daysLeft %></dd>
</dl>
</div>

<div class="box">
<h2>Request</h2>
<dl>
  <dt>Time</dt><dd><%= new Date() %></dd>
  <dt>Scheme</dt><dd><%= request.getScheme() %></dd>
  <dt>Server port</dt><dd><%= request.getServerPort() %></dd>
  <dt>Server info</dt><dd><%= application.getServerInfo() %></dd>
</dl>
</div>
</body>
</html>
