# PlanO Deployment Guide

## Current Development Setup

In development, PlanO runs as three independent processes:

| Service          | Command                                                    | Port |
|------------------|------------------------------------------------------------|------|
| Raster Backend   | `uvicorn server.app:app --host 127.0.0.1 --port 8010`    | 8010 |
| React-Planner    | `npm start` (webpack-dev-server)                           | 5173 |
| PlanO Frontend   | `npm run dev -- --port 5174` (Vite)                        | 5174 |

## Server Deployment (hadrien-skoed-mt)

### Machine Specifications

- **Host**: hadrien-skoed-mt (172.20.1.60)
- **OS**: Ubuntu 24.04.4 LTS
- **CPU**: AMD Ryzen 7 5800X (8 cores / 16 threads)
- **RAM**: 62 GB
- **GPU**: NVIDIA RTX 4070 12GB VRAM
- **Disk**: 3.6 TB NVMe (3.4 TB free)
- **Access**: Via SSH through VPN (GlobalProtect to Simply Staking)

### Installed Software

- Node.js 24.14.0
- Python 3.10.20 (deadsnakes PPA)
- Git 2.43.0
- Build tools (gcc, make, cmake)
- Native libs (cairo, pango, libjpeg, giflib, librsvg)

### Project Location

```
/home/hadrienm/plano_master/
```

### Starting Services

#### Option A: Manual (three SSH sessions)

```bash
# Session 1
cd ~/plano_master/01_raster && source .venv/bin/activate
uvicorn server.app:app --host 127.0.0.1 --port 8010

# Session 2
cd ~/plano_master/02_react_planner/react-planner && npm start

# Session 3
cd ~/plano_master/00_frontend_skeleton/plano-ui && npm run dev -- --port 5174
```

#### Option B: tmux (single SSH session)

```bash
cd ~/plano_master && \
tmux new-session -d -s plano \
  'cd 01_raster && source .venv/bin/activate && uvicorn server.app:app --host 127.0.0.1 --port 8010' \; \
  split-window -h 'cd 02_react_planner/react-planner && npm start' \; \
  split-window -v 'cd 00_frontend_skeleton/plano-ui && npm run dev -- --port 5174' \; \
  attach
```

To detach: `Ctrl+B, D`
To reattach: `tmux attach -t plano`
To kill: `tmux kill-session -t plano`

#### Option C: systemd (production)

Create service files for each component:

**/etc/systemd/system/plano-raster.service**
```ini
[Unit]
Description=PlanO Raster Backend
After=network.target

[Service]
Type=simple
User=hadrienm
WorkingDirectory=/home/hadrienm/plano_master/01_raster
Environment=PATH=/home/hadrienm/plano_master/01_raster/.venv/bin:/usr/bin
ExecStart=/home/hadrienm/plano_master/01_raster/.venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8010
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**/etc/systemd/system/plano-planner.service**
```ini
[Unit]
Description=PlanO React-Planner Engine
After=network.target

[Service]
Type=simple
User=hadrienm
WorkingDirectory=/home/hadrienm/plano_master/02_react_planner/react-planner
Environment=PATH=/usr/bin:/usr/local/bin
ExecStart=/usr/bin/npm start
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**/etc/systemd/system/plano-frontend.service**
```ini
[Unit]
Description=PlanO Frontend
After=network.target

[Service]
Type=simple
User=hadrienm
WorkingDirectory=/home/hadrienm/plano_master/00_frontend_skeleton/plano-ui
Environment=PATH=/usr/bin:/usr/local/bin
ExecStart=/usr/bin/npm run dev -- --port 5174
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now plano-raster plano-planner plano-frontend
sudo systemctl status plano-raster plano-planner plano-frontend
```

### Remote Access

Since the server is behind a VPN (172.20.1.60), access the app via SSH port forwarding:

```bash
# From a machine with VPN access (e.g., the ROG relay)
ssh -L 5174:127.0.0.1:5174 -L 5173:127.0.0.1:5173 -L 8010:127.0.0.1:8010 gpu
```

Then open http://localhost:5174 in your local browser.

Or from the plano-client machine (two-hop):
```bash
ssh -L 5174:127.0.0.1:5174 -L 5173:127.0.0.1:5173 -L 8010:127.0.0.1:8010 skoed-mt
```

## Network Topology

```
                        Internet
                            │
                   ┌────────┴────────┐
                   │  GlobalProtect  │
                   │    VPN Gateway  │
                   │  (Simply VC)    │
                   └────────┬────────┘
                            │ 172.20.1.0/24
              ┌─────────────┼─────────────┐
              │                           │
    ┌─────────▼──────────┐     ┌──────────▼─────────┐
    │  hadrien-skoed-mt  │     │  Other Skoed infra  │
    │    172.20.1.60     │     │                     │
    │  PlanO services    │     │                     │
    └────────────────────┘     └─────────────────────┘
              ▲
              │ Reverse SSH (port 2222)
              │ or VPN tunnel
    ┌─────────┴──────────┐
    │  ROG Flow Z13      │
    │  192.168.50.226    │     ┌─────────────────────┐
    │  (jump box/relay)  │─────│  plano-client       │
    └────────────────────┘ LAN │  192.168.50.187     │
                               │  (source machine)   │
                               └─────────────────────┘
```

## Future: Docker Compose

A production-ready Docker Compose setup would look like:

```yaml
# docker-compose.yml (planned)
version: '3.8'

services:
  frontend:
    build: ./00_frontend_skeleton/plano-ui
    ports:
      - "5174:5174"
    depends_on:
      - planner
      - raster

  planner:
    build: ./02_react_planner/react-planner
    ports:
      - "5173:5173"

  raster:
    build: ./01_raster
    ports:
      - "8010:8010"
    env_file:
      - ./01_raster/.env
    volumes:
      - raster-uploads:/app/uploads
      - raster-logs:/app/logs

volumes:
  raster-uploads:
  raster-logs:
```

## Future: Reverse Proxy (nginx)

For production, put all services behind a single nginx instance:

```nginx
# /etc/nginx/sites-available/plano
server {
    listen 443 ssl;
    server_name plano.example.com;

    ssl_certificate /etc/letsencrypt/live/plano.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/plano.example.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:5174;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # React-Planner (served in iframe)
    location /planner-engine/ {
        proxy_pass http://127.0.0.1:5173/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Raster API
    location /api/raster/ {
        proxy_pass http://127.0.0.1:8010/;
        client_max_body_size 50M;
        proxy_read_timeout 300s;
    }
}
```
