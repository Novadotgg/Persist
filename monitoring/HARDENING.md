# Hardening & Access Control Guide

> **Personal AI Assistant OS — Production Security Hardening**

This document describes how to restrict service exposure, configure network-level access control, and harden the deployment using Tailscale VPN and reverse proxies.

---

## 1. Service Binding — Restrict to Internal Interfaces

By default Docker Compose binds service ports to `0.0.0.0`, making them reachable from any network interface. In production, services should only listen on `127.0.0.1` or the Tailscale virtual interface.

### Docker Compose Port Overrides

```yaml
services:
  backend:
    ports:
      - "127.0.0.1:8000:8000"   # Localhost only

  prometheus:
    ports:
      - "127.0.0.1:9090:9090"   # Localhost only

  grafana:
    ports:
      - "127.0.0.1:3001:3000"   # Localhost only
```

If using Tailscale, bind to the Tailscale IP instead:

```yaml
  backend:
    ports:
      - "100.x.y.z:8000:8000"   # Replace with your Tailscale IP
```

---

## 2. Tailscale VPN Setup

[Tailscale](https://tailscale.com/) creates a WireGuard-based mesh VPN that gives each device a stable `100.x.y.z` IP address. It requires zero firewall configuration.

### Installation

```bash
# Linux (Ubuntu/Debian)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# macOS
brew install tailscale
sudo tailscale up

# Windows
# Download from https://tailscale.com/download/windows
```

### Verify Connectivity

```bash
tailscale status        # List all devices on your tailnet
tailscale ip -4         # Show your Tailscale IPv4 address
ping 100.x.y.z          # Verify reachability to another device
```

---

## 3. Tailscale ACL Configuration

Tailscale Access Control Lists (ACLs) define which devices and users can reach specific ports. Configure these in the [Tailscale Admin Console → Access Controls](https://login.tailscale.com/admin/acls).

### Recommended ACL Policy

```jsonc
{
  "acls": [
    // Allow the admin user full access to the PA backend
    {
      "action": "accept",
      "src": ["group:admins"],
      "dst": ["tag:pa-server:8000"]
    },
    // Allow only monitoring nodes to scrape Prometheus metrics
    {
      "action": "accept",
      "src": ["tag:monitoring"],
      "dst": ["tag:pa-server:9090"]
    },
    // Allow admin access to Grafana dashboards
    {
      "action": "accept",
      "src": ["group:admins"],
      "dst": ["tag:pa-server:3001"]
    }
  ],

  "groups": {
    "group:admins": ["user@example.com"]
  },

  "tagOwners": {
    "tag:pa-server":  ["group:admins"],
    "tag:monitoring": ["group:admins"]
  }
}
```

### Applying Tags

```bash
# On the server running PA services
sudo tailscale up --advertise-tags=tag:pa-server

# On the monitoring/scraper node
sudo tailscale up --advertise-tags=tag:monitoring
```

---

## 4. Reverse Proxy Hardening

Place a reverse proxy in front of the backend to:
- Terminate TLS (HTTPS)
- Rate-limit requests
- Block unauthorized access to `/api/v1/metrics`

### Option A: Nginx

```nginx
server {
    listen 443 ssl;
    server_name pa.example.com;

    ssl_certificate     /etc/ssl/certs/pa.crt;
    ssl_certificate_key /etc/ssl/private/pa.key;

    # Block external access to metrics endpoint
    location /api/v1/metrics {
        # Only allow Tailscale subnet
        allow 100.64.0.0/10;
        deny all;
        proxy_pass http://127.0.0.1:8000;
    }

    # Proxy all other traffic normally
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
    location /api/ {
        limit_req zone=api burst=60 nodelay;
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### Option B: Caddy

```caddyfile
pa.example.com {
    # Restrict /metrics to Tailscale subnet
    @metrics path /api/v1/metrics
    handle @metrics {
        @denied not remote_ip 100.64.0.0/10
        respond @denied 403

        reverse_proxy localhost:8000
    }

    # All other routes
    reverse_proxy localhost:8000
}
```

Caddy automatically provisions TLS certificates via Let's Encrypt.

---

## 5. Additional Security Recommendations

| Area | Recommendation |
|---|---|
| **Secrets** | Store all secrets (DB passwords, API keys) in `.env` files excluded from Git. Use a secrets manager (e.g., Vault, AWS Secrets Manager) in production. |
| **Database** | Restrict PostgreSQL `pg_hba.conf` to only accept connections from `127.0.0.1` and the Docker bridge network. |
| **Redis** | Set `requirepass` in Redis configuration and use an ACL user for the application. |
| **Ollama** | Bind Ollama to `127.0.0.1:11434` — it has no built-in authentication. |
| **CORS** | Restrict `allow_origins` in FastAPI CORS middleware to your actual frontend domain. |
| **Logs** | Audit-log all `/api/v1/agent/chat` requests. Rotate logs with `logrotate` or a centralized logger (ELK, Loki). |
| **Updates** | Pin Docker image tags to specific versions. Regularly update base images for security patches. |

---

## 6. Pre-Deployment Checklist

- [ ] All service ports bound to `127.0.0.1` or Tailscale IP (not `0.0.0.0`)
- [ ] Tailscale installed and authenticated on server and admin devices
- [ ] ACL policy applied restricting `/metrics` to `tag:monitoring` only
- [ ] Reverse proxy (Nginx/Caddy) configured with TLS termination
- [ ] `.env` file excluded from version control (`.gitignore`)
- [ ] Redis `requirepass` set
- [ ] PostgreSQL `pg_hba.conf` restricted
- [ ] CORS `allow_origins` limited to production frontend URL
- [ ] Docker images pinned to specific versions
- [ ] Log rotation configured
