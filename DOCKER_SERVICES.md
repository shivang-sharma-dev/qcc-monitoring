# QCC Monitoring - Docker Services Overview

This repository contains the complete Docker infrastructure for the QCC (Quantum Command Center) Drone Management System. The setup is split into two main stacks: the **core application stack** and the **monitoring stack**. Both stacks share the same Docker network (`drone-net`) which allows seamless communication between services.

---

## Table of Contents
- [Quick Reference](#quick-reference)
- [Core Application Stack](#core-application-stack)
- [Monitoring Stack](#monitoring-stack)
- [Network Architecture](#network-architecture)
- [Getting Started](#getting-started)

---

## Quick Reference

### Application Stack (`docker-compose.yaml`)
| Service | Local Port | Container Port | Purpose |
|---------|-----------|----------------|---------|
| PostgreSQL | 5432 | 5432 | Primary database |
| pgAdmin | - | 80 (internal) | Database management UI |
| InfluxDB | 8086 | 8086 | Time-series database for telemetry |
| Keycloak | - | 8080 (internal) | Authentication & identity management |
| DFR API | 8080 | 8080 | Drone Flight Record backend API |
| VMS API | 9083 | 9083 | Vehicle Management System API |
| Ant Media | 5080, 1935, 5443 | 5080, 1935, 5443 | Video streaming server |
| NGINX | 80, 443, 9101 | 80, 443, 9101 | Reverse proxy & SSL termination |

### Monitoring Stack (`docker-compose.yml`)
| Service | Local Port | Container Port | Purpose |
|---------|-----------|----------------|---------|
| Prometheus | 9090 | 9090 | Metrics collection & storage |
| Grafana | 3001 | 3000 | Metrics visualization dashboards |
| Node Exporter | 9100 | 9100 | Host system metrics |
| Smartctl Exporter | - | 9633 (internal) | Disk health metrics |
| NGINX Exporter | 9113 | 9113 | NGINX performance metrics |
| cAdvisor | 7070 | 8080 | Container resource metrics |
| Promtail | - | (internal) | Log collection agent |
| Loki | 3100 | 3100 | Log aggregation & storage |

---

## Core Application Stack

The application stack runs the main drone management platform. Everything here supports the core business logic - from user authentication to video streaming to database management.

### Database Layer

#### PostgreSQL (db)
**Image:** `postgres:16-alpine`  
**Container:** `postgres`  
**Ports:** `5432:5432`

PostgreSQL is the backbone of our data storage. We're running a single Postgres instance that hosts multiple databases:
- **dmdfrdb** - The main Drone Management & Flight Record database
- **keycloak** - Stores all user authentication and authorization data

The instance is configured with `pg_stat_statements` enabled, which helps us track query performance and optimize slow queries. We've also bumped the max connections to 300 to handle concurrent requests from multiple services.

The initialization scripts in `./db/init` run automatically on first startup to create the required databases.

#### pgAdmin (pgadmin)
**Image:** `dpage/pgadmin4:latest`  
**Container:** `pgadmin`  
**Ports:** Internal only (80), exposed through NGINX

This gives us a web-based interface to manage PostgreSQL. It's particularly useful when debugging database issues or running manual queries. The service is only accessible internally - NGINX handles the external routing with proper authentication.

#### InfluxDB (influxdb)
**Image:** `influxdb:2.1`  
**Container:** `influxdb`  
**Ports:** `8086:8086`

InfluxDB stores time-series data from our drones - think telemetry, GPS coordinates, altitude changes, battery levels over time, etc. It's optimized for write-heavy workloads where data comes in at high frequency.

The companion `influxdb_cli` container runs once during initial setup to configure the bucket, organization, and authentication tokens. After that, it exits - it's not a long-running service.

### Authentication & Identity

#### Keycloak (keycloak)
**Image:** `quay.io/keycloak/keycloak:18.0.2`  
**Container:** `keycloak`  
**Ports:** Internal only (8080), exposed through NGINX

Keycloak handles all authentication and authorization for the platform. It manages:
- User login and session management
- OAuth2/OIDC token generation
- Role-based access control (RBAC)
- Multi-factor authentication (if configured)

It runs in "edge" proxy mode since it sits behind NGINX, which handles SSL termination. The service connects to the `keycloak` database in PostgreSQL for persistence.

### Application APIs

#### DFR API (dfr-api)
**Image:** `ghcr.io/grok-digital/drone-api:master`  
**Container:** `dfr-api-server`  
**Ports:** `8080:8080`

The Drone Flight Record API is the primary backend service. It handles:
- Flight planning and mission management
- Drone registration and configuration
- Flight record storage and retrieval
- Integration with external flight operations systems
- Email notifications for flight events

This is a Spring Boot application that communicates with PostgreSQL for relational data and InfluxDB for telemetry streams.

#### VMS API (vms-api)
**Image:** `ghcr.io/grok-digital/drone-vms-api:master`  
**Container:** `vms-api-server`  
**Ports:** `9083:9083`

The Vehicle Management System API focuses on the drone fleet itself:
- Drone inventory and asset tracking
- Maintenance schedules and records
- Vehicle health monitoring
- Battery and component lifecycle management

Both APIs are labeled with Watchtower labels, meaning they'll auto-update when new versions are pushed to the container registry.

### Media Streaming

#### Ant Media Server (antmedia)
**Image:** `antmedia/enterprise:2.17.1`  
**Container:** `antmedia`  
**Ports:** 
- `5080:5080` - HTTP/WebSocket
- `1935:1935` - RTMP streaming
- `5443:5443` - HTTPS/WebSocket

Ant Media handles real-time video streaming from drones. During flights, video feeds are streamed via RTMP and made available through WebRTC for low-latency viewing in the web interface.

The enterprise edition provides clustering capabilities and advanced features like adaptive bitrate streaming. Videos can also be recorded and stored for later review.

### Reverse Proxy

#### NGINX (nginx)
**Image:** `nginx:1.25-alpine`  
**Container:** `nginx`  
**Ports:** 
- `80:80` - HTTP
- `443:443` - HTTPS
- `9101:9101` - Metrics endpoint for monitoring

NGINX sits at the edge of the stack and routes all incoming traffic. It handles:
- SSL/TLS termination (certificates in `./ssl`)
- Reverse proxying to backend services
- Load balancing (when multiple instances run)
- Static file serving
- WebSocket proxying for real-time features

The configuration (`nginx.conf`) defines routing rules for each service. The metrics endpoint on port 9101 exposes NGINX stats for Prometheus scraping.

---

## Monitoring Stack

The monitoring stack gives us visibility into how everything is performing - from infrastructure health to application metrics to logs.

### Metrics Collection

#### Prometheus (prometheus)
**Image:** `prom/prometheus:v3`  
**Container:** `prometheus`  
**Ports:** `9090:9090`

Prometheus is the central metrics database. It scrapes metrics from all the exporters and stores them in a time-series format. Every 15 seconds (configurable), it pulls data from:
- Node Exporter (system metrics)
- cAdvisor (container metrics)
- NGINX Exporter (web server metrics)
- Smartctl Exporter (disk health)
- Application endpoints (if they expose /metrics)

The web UI at port 9090 lets you run PromQL queries and explore metrics directly, though most visualization happens through Grafana.

#### Grafana (grafana)
**Image:** `grafana/grafana:12.3`  
**Container:** `grafana`  
**Ports:** `3001:3000`

Grafana is where all the monitoring data comes together visually. The dashboards (from the various JSON files in the repo) display:
- Container health and resource usage
- API response times and error rates
- Database performance
- Host system vitals (CPU, memory, disk, network)
- Application-specific metrics
- Logs from Loki

The provisioning folder contains pre-configured data sources (Prometheus, Loki) so everything works out of the box. Access Grafana at `http://localhost:3001` (default credentials are in the environment variables).

### System Exporters

#### Node Exporter (node-exporter)
**Image:** `prom/node-exporter:latest`  
**Container:** `node-exporter`  
**Ports:** `9100:9100`

This exposes hardware and OS metrics from the host machine:
- CPU usage per core
- Memory utilization (used, free, cached)
- Disk I/O statistics
- Network interface stats
- Filesystem usage
- System load averages

The entire host filesystem is mounted read-only at `/host` so the exporter can gather accurate metrics even though it's running in a container.

#### Smartctl Exporter (smartctl-exporter)
**Image:** `prometheuscommunity/smartctl-exporter`  
**Container:** `smartctl-exporter`  
**Ports:** Internal (9633)

Runs with privileged access to read S.M.A.R.T. data from physical disks. This helps predict disk failures before they happen by tracking:
- Reallocated sectors
- Spin retry counts
- Temperature
- Power-on hours
- Pending sector counts

Critical for preventing data loss on systems with traditional hard drives.

#### NGINX Prometheus Exporter (nginx-prometheus-exporter)
**Image:** `nginx/nginx-prometheus-exporter:1.5.1`  
**Container:** `prometheus-nginx-exporter`  
**Ports:** `9113:9113`

Scrapes the NGINX stub status endpoint and converts it to Prometheus metrics. Tracks:
- Active connections
- Total requests handled
- Reading/writing/waiting states
- Request rate

Helps identify if NGINX becomes a bottleneck or if we're getting unusual traffic patterns.

#### cAdvisor (cadvisor)
**Image:** `gcr.io/cadvisor/cadvisor:latest`  
**Container:** `cadvisor`  
**Ports:** `7070:8080`

Container Advisor monitors resource usage of all running Docker containers:
- CPU usage per container
- Memory consumption and limits
- Network I/O per container
- Filesystem I/O
- Container restart counts

This is especially valuable for identifying which services are resource hogs or experiencing memory leaks. The UI at port 7070 provides a quick visual overview.

### Log Management

#### Loki (loki)
**Image:** `grafana/loki:3.0.0`  
**Container:** `loki`  
**Ports:** `3100:3100`

Loki is like Prometheus but for logs. Instead of storing full-text logs like Elasticsearch, it only indexes metadata (labels) and stores the log lines separately. This makes it much more cost-effective while still allowing powerful queries.

Logs are organized by:
- Container name
- Service name
- Log level (if structured)
- Custom labels from Promtail

You can search logs in Grafana using LogQL, which feels similar to PromQL.

#### Promtail (promtail)
**Image:** `grafana/promtail:latest`  
**Container:** `promtail`  
**Ports:** Internal only

Promtail is the log collection agent. It:
- Tails log files from `/var/log`
- Reads Docker container logs from `/var/lib/docker/containers`
- Parses and labels log entries
- Ships everything to Loki

The configuration (`promtail-config.yml`) defines which logs to collect and how to label them. It automatically discovers new containers and starts tailing their logs.

---

## Network Architecture

Both Docker Compose files reference an **external network** called `drone-net`. This needs to be created before starting any services:

```bash
docker network create drone-net
```

Using a shared external network allows containers from different Compose files to communicate. For example:
- Prometheus can scrape metrics from the NGINX container
- Grafana can query both Prometheus and Loki
- Monitoring exporters can connect to application services

All inter-service communication happens over this private network. Only the explicitly mapped ports are exposed to the host machine or the internet.

### Internet vs. Local Access

**Publicly Accessible (through NGINX):**
- Main application UI and APIs (via ports 80/443)
- Keycloak login pages
- pgAdmin (if configured in NGINX)

**Local Machine Only:**
- PostgreSQL (5432) - direct database access for development
- InfluxDB (8086) - direct API access
- APIs (8080, 9083) - can be accessed directly, bypassing NGINX
- Prometheus (9090) - metrics UI
- Grafana (3001) - dashboard UI
- All exporters - metrics endpoints

**Internal Only (container-to-container):**
- pgAdmin default port (proxied through NGINX)
- Keycloak (proxied through NGINX)
- Promtail
- Smartctl Exporter

In production, you'd typically firewall off all the "Local Machine Only" ports and only allow traffic through NGINX.

---

## Getting Started

### Prerequisites

Create the required Docker volumes and network:

```bash
# Create the network
docker network create drone-net

# Create the volumes
docker volume create db_data
docker volume create pgadmin_data
docker volume create influxdb_data
docker volume create antmedia_data
docker volume create prometheus_data
docker volume create grafana_data
docker volume create loki_data
```

### Environment Configuration

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Make sure to set all required variables like database passwords, Keycloak credentials, email settings, etc.

### Starting the Stacks

Start the application stack first:

```bash
docker-compose -f docker-compose.yaml up -d
```

Wait for all services to be healthy, then start the monitoring stack:

```bash
docker-compose -f docker-compose.yml up -d
```

### Accessing Services

- **Application:** https://your-domain.com (via NGINX)
- **Grafana:** http://localhost:3001
- **Prometheus:** http://localhost:9090
- **InfluxDB:** http://localhost:8086
- **PostgreSQL:** localhost:5432

### Verifying Everything Works

Check that all containers are running:

```bash
docker ps
```

Check logs if something isn't starting:

```bash
docker logs <container-name>
```

Test connectivity between stacks:

```bash
# From inside the Prometheus container
docker exec prometheus wget -qO- http://nginx:9101/metrics
```

---

## Maintenance Notes

### Updates

The DFR API and VMS API containers are configured with Watchtower labels. If you're running Watchtower separately, these will auto-update when new images are pushed to the registry.

### Backups

Critical data is stored in Docker volumes. Regular backups should cover:
- `db_data` - PostgreSQL databases
- `influxdb_data` - Time-series telemetry
- `grafana_data` - Dashboard configurations (unless using provisioning)

### Scaling

To scale horizontally:
- Run multiple instances of the API containers
- Configure NGINX for load balancing
- Ensure database connection pools are sized appropriately

### Troubleshooting

**Service won't start:**
- Check logs: `docker logs <container>`
- Verify environment variables are set
- Ensure dependent services are running
- Check volume permissions

**Can't connect between services:**
- Verify both containers are on `drone-net`
- Check firewall rules
- Use container names (not localhost) for inter-container communication

**High resource usage:**
- Check cAdvisor at http://localhost:7070
- Review Grafana dashboards for anomalies
- Look for memory leaks in application logs

---

## Additional Resources

- **Dashboards:** Pre-configured Grafana dashboards are in the `grafana-*-dashboard.json` files
- **Documentation:** `QCC_Docker_Services_Documentation.docx` contains additional operational details
- **Diagrams:** `monitoring-stack-diagram.png` shows the architecture visually
- **Email Integration:** `azure-grafana-email-integration.docx` explains alert notifications

---

*This infrastructure supports the QCC drone management platform, providing a complete stack for flight operations, video streaming, authentication, and comprehensive monitoring.*
