# Cloudflare Tunnel (optional)

A Cloudflare Tunnel lets you SSH into the Pi from anywhere without opening ports on your router. This is optional — HydroPi works fine without it.

## Prerequisites

- A free [Cloudflare](https://cloudflare.com) account.
- A domain managed by Cloudflare.

## Setup

### 1. Install cloudflared

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -o cloudflared
sudo mv cloudflared /usr/local/bin/
sudo chmod +x /usr/local/bin/cloudflared
```

Use `arm` instead of `arm64` for older 32-bit Pi models.

### 2. Authenticate

```bash
cloudflared tunnel login
```

Follow the browser link to authorise your Cloudflare account.

### 3. Create a tunnel

```bash
cloudflared tunnel create hydropi
```

Note the tunnel ID printed in the output.

### 4. Create the config file

```bash
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << EOF
tunnel: <tunnel-id>
credentials-file: /home/<your-user>/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: <your-hostname>.yourdomain.com
    service: ssh://localhost:22
  - service: http_status:404
EOF
```

### 5. Add a DNS record

```bash
cloudflared tunnel route dns hydropi <your-hostname>.yourdomain.com
```

### 6. Install and start as a service

```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

The `cloudflared.service` file in `setup/services/` is installed automatically by `setup.sh` if present, but you must complete steps 1–5 manually first.

## Connecting

```bash
ssh <user>@<your-hostname>.yourdomain.com
```
