"""Generate Prerequisites PDF for PatchMaster project."""
from fpdf import FPDF
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


class SopPDF(FPDF):
    def __init__(self, title, doc_id, *a, **kw):
        super().__init__(*a, **kw)
        self._title = title
        self._doc_id = doc_id
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, f"PatchMaster  |  {self._doc_id}", align="L")
        self.ln(4)
        self.set_draw_color(0, 120, 215)
        self.set_line_width(0.6)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}  |  Confidential  |  {self._title}", align="C")

    def cover_page(self, title, subtitle, version="2.0.0", date="March 2026"):
        self.add_page()
        self.ln(60)
        self.set_font("Helvetica", "B", 32)
        self.set_text_color(0, 90, 180)
        self.cell(0, 14, "PatchMaster", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(40, 40, 40)
        self.cell(0, 12, title, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(6)
        self.set_font("Helvetica", "", 13)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, subtitle, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(20)
        self.set_font("Helvetica", "", 11)
        for line in [
            f"Document ID: {self._doc_id}",
            f"Version: {version}",
            f"Date: {date}",
            "Classification: Internal",
        ]:
            self.cell(0, 7, line, align="C", new_x="LMARGIN", new_y="NEXT")

    def section(self, num, title):
        self.ln(4)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(0, 90, 180)
        self.cell(0, 10, f"{num}. {title}", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_text_color(30, 30, 30)

    def sub(self, title):
        self.ln(2)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(50, 50, 50)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self.set_text_color(30, 30, 30)

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def bullet(self, items):
        self.set_font("Helvetica", "", 10)
        for item in items:
            self.cell(6)
            self.cell(4, 5.5, "-")
            self.multi_cell(0, 5.5, item)
            self.ln(0.5)
        self.ln(1)

    def numbered(self, items):
        self.set_font("Helvetica", "", 10)
        for i, item in enumerate(items, 1):
            self.cell(6)
            self.cell(8, 5.5, f"{i}.")
            self.multi_cell(0, 5.5, item)
            self.ln(0.5)
        self.ln(1)

    def code(self, text):
        self.set_font("Courier", "", 9)
        self.set_fill_color(240, 240, 240)
        self.set_text_color(30, 30, 30)
        for line in text.strip().split("\n"):
            self.cell(6)
            self.cell(0, 5, f"  {line}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_font("Helvetica", "", 10)

    def table(self, headers, rows, col_widths=None):
        if col_widths is None:
            col_widths = [190 // len(headers)] * len(headers)
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(0, 90, 180)
        self.set_text_color(255, 255, 255)
        for w, h in zip(col_widths, headers):
            self.cell(w, 7, f" {h}", border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", 9)
        self.set_text_color(30, 30, 30)
        fill = False
        for row in rows:
            if self.get_y() > 265:
                self.add_page()
            self.set_fill_color(245, 248, 255) if fill else self.set_fill_color(255, 255, 255)
            for w, c in zip(col_widths, row):
                self.cell(w, 6, f" {c}", border=1, fill=True)
            self.ln()
            fill = not fill
        self.ln(2)

    def note(self, text):
        self.set_font("Helvetica", "BI", 10)
        self.set_text_color(180, 120, 0)
        self.cell(6)
        self.multi_cell(0, 5.5, f"Note: {text}")
        self.set_text_color(30, 30, 30)
        self.ln(1)

    def warning(self, text):
        self.set_font("Helvetica", "BI", 10)
        self.set_text_color(200, 50, 50)
        self.cell(6)
        self.multi_cell(0, 5.5, f"Warning: {text}")
        self.set_text_color(30, 30, 30)
        self.ln(1)


def build_prerequisites():
    pdf = SopPDF("Prerequisites Guide", "PRE-REQ-001")
    pdf.alias_nb_pages()

    # ── Cover ──
    pdf.cover_page(
        "Prerequisites Guide",
        "Hardware, Software & Network Requirements",
    )

    # ── TOC ──
    pdf.add_page()
    pdf.section("", "Table of Contents")
    toc = [
        "1.  Overview",
        "2.  Server Hardware Requirements",
        "3.  Server Operating System",
        "4.  Docker & Docker Compose",
        "5.  Network & Firewall Requirements",
        "6.  Managed Host (Agent) Requirements",
        "7.  Developer Workstation Requirements",
        "8.  Agent Build Machine Requirements",
        "9.  Browser Requirements",
        "10. Monitoring Stack Requirements",
        "11. Optional / Production Enhancements",
        "12. Pre-Deployment Checklist",
        "13. Quick Verification Commands",
    ]
    pdf.bullet(toc)

    # ═══════════════════════════════════════
    # 1  Overview
    # ═══════════════════════════════════════
    pdf.add_page()
    pdf.section("1", "Overview")
    pdf.body(
        "PatchMaster is a centralized Linux patch management platform consisting of 6 Docker "
        "services (PostgreSQL, FastAPI backend, React frontend, Flask agent, Prometheus, Grafana) "
        "and distributed agents installed on managed Linux hosts."
    )
    pdf.body(
        "This document lists all hardware, software, network, and configuration prerequisites "
        "needed before deploying PatchMaster. It is divided into sections for the central server, "
        "managed hosts (agents), developer workstations, and the agent build environment."
    )
    pdf.sub("Architecture Summary")
    pdf.code(
        "Central Server (Docker Host)\n"
        "  [PostgreSQL] [FastAPI Backend] [React Frontend]\n"
        "  [Prometheus] [Grafana]\n"
        "\n"
        "Managed Linux Hosts (Fleet)\n"
        "  [patch-agent] -- heartbeat --> [Backend]\n"
        "  [patch-agent-api :8080] <-- proxy <-- [Backend]"
    )

    # ═══════════════════════════════════════
    # 2  Server Hardware
    # ═══════════════════════════════════════
    pdf.section("2", "Server Hardware Requirements")
    pdf.body(
        "The central PatchMaster server runs 6 Docker containers. Hardware requirements "
        "depend on fleet size."
    )
    pdf.sub("Minimum (up to 50 hosts)")
    pdf.table(
        ["Resource", "Minimum", "Recommended"],
        [
            ["CPU", "2 cores", "4 cores"],
            ["RAM", "4 GB", "8 GB"],
            ["Disk (OS + Docker)", "20 GB", "40 GB"],
            ["Disk (PostgreSQL data)", "5 GB", "20 GB"],
            ["Disk (Prometheus data)", "5 GB", "20 GB (30-day retention)"],
            ["Network", "100 Mbps", "1 Gbps"],
        ],
        [55, 55, 80],
    )
    pdf.sub("Medium (50-500 hosts)")
    pdf.table(
        ["Resource", "Minimum", "Recommended"],
        [
            ["CPU", "4 cores", "8 cores"],
            ["RAM", "8 GB", "16 GB"],
            ["Disk (OS + Docker)", "40 GB", "80 GB"],
            ["Disk (PostgreSQL data)", "20 GB", "50 GB"],
            ["Disk (Prometheus data)", "20 GB", "100 GB"],
            ["Network", "1 Gbps", "1 Gbps"],
        ],
        [55, 55, 80],
    )
    pdf.sub("Large (500+ hosts)")
    pdf.table(
        ["Resource", "Minimum", "Recommended"],
        [
            ["CPU", "8 cores", "16 cores"],
            ["RAM", "16 GB", "32 GB"],
            ["Disk (OS + Docker)", "80 GB", "200 GB SSD"],
            ["Disk (PostgreSQL data)", "50 GB", "200 GB SSD"],
            ["Disk (Prometheus data)", "100 GB", "500 GB SSD"],
            ["Network", "1 Gbps", "10 Gbps"],
        ],
        [55, 55, 80],
    )
    pdf.note("SSD storage is strongly recommended for PostgreSQL and Prometheus data volumes.")

    # ═══════════════════════════════════════
    # 3  Server OS
    # ═══════════════════════════════════════
    pdf.add_page()
    pdf.section("3", "Server Operating System")
    pdf.body("The PatchMaster server can run on any OS that supports Docker.")
    pdf.sub("Supported Server Operating Systems")
    pdf.table(
        ["Operating System", "Version", "Status"],
        [
            ["Ubuntu Server", "22.04 LTS / 24.04 LTS", "Recommended"],
            ["Debian", "11 (Bullseye) / 12 (Bookworm)", "Supported"],
            ["RHEL / Rocky / Alma", "8.x / 9.x", "Supported"],
            ["Windows + WSL2", "Windows 10/11 + WSL2 Ubuntu", "Supported (Dev/Lab)"],
            ["macOS + Docker Desktop", "macOS 12+", "Supported (Dev only)"],
        ],
        [55, 70, 65],
    )
    pdf.note(
        "Production deployments should use native Linux. "
        "Windows WSL2 is suitable for development and lab environments."
    )
    pdf.sub("Required OS Packages (if not using Docker)")
    pdf.bullet([
        "Python 3.10 or later",
        "Node.js 18 or later + npm",
        "PostgreSQL 15",
        "Nginx (for frontend reverse proxy)",
    ])

    # ═══════════════════════════════════════
    # 4  Docker
    # ═══════════════════════════════════════
    pdf.section("4", "Docker & Docker Compose")
    pdf.body("PatchMaster is deployed using Docker Compose with 6 services.")
    pdf.sub("Required Versions")
    pdf.table(
        ["Software", "Minimum Version", "Recommended", "Check Command"],
        [
            ["Docker Engine", "20.10+", "24.x / 25.x+", "docker --version"],
            ["Docker Compose", "v2.0+", "v2.20+", "docker compose version"],
        ],
        [40, 40, 40, 70],
    )
    pdf.sub("Installation (Ubuntu/Debian)")
    pdf.code(
        "# Install Docker (official method)\n"
        "curl -fsSL https://get.docker.com | sudo sh\n"
        "\n"
        "# Add your user to docker group (avoids sudo)\n"
        "sudo usermod -aG docker $USER\n"
        "newgrp docker\n"
        "\n"
        "# Verify\n"
        "docker --version\n"
        "docker compose version"
    )
    pdf.sub("Installation (RHEL/Rocky/Alma)")
    pdf.code(
        "sudo dnf config-manager --add-repo \\\n"
        "  https://download.docker.com/linux/centos/docker-ce.repo\n"
        "sudo dnf install docker-ce docker-ce-cli containerd.io \\\n"
        "  docker-compose-plugin -y\n"
        "sudo systemctl enable --now docker\n"
        "sudo usermod -aG docker $USER"
    )
    pdf.sub("Installation (Windows WSL2)")
    pdf.code(
        "# Option A: Docker Desktop for Windows\n"
        "# Download from https://www.docker.com/products/docker-desktop\n"
        "# Enable WSL2 backend in settings\n"
        "\n"
        "# Option B: Docker inside WSL2 distro\n"
        "wsl --install -d Ubuntu\n"
        "# Then install Docker inside WSL Ubuntu (same as Linux above)"
    )
    pdf.sub("Docker Resource Allocation")
    pdf.bullet([
        "Ensure Docker has at least 4 GB RAM allocated (Docker Desktop settings)",
        "Allocate at least 2 CPU cores to Docker",
        "Ensure sufficient disk space for Docker images and volumes",
    ])

    # ═══════════════════════════════════════
    # 5  Network / Firewall
    # ═══════════════════════════════════════
    pdf.add_page()
    pdf.section("5", "Network & Firewall Requirements")
    pdf.sub("Ports Required on Central Server")
    pdf.table(
        ["Port", "Protocol", "Service", "Direction", "Access"],
        [
            ["3000", "TCP", "Frontend (Web UI)", "Inbound", "Users/Admins"],
            ["3001", "TCP", "Grafana Dashboards", "Inbound", "Admins/Ops"],
            ["8000", "TCP", "Backend API", "Inbound", "Agents + UI"],
            ["9090", "TCP", "Prometheus", "Inbound", "Admins (optional)"],
            ["5432", "TCP", "PostgreSQL", "Internal only", "Backend container"],
        ],
        [20, 22, 48, 40, 60],
    )
    pdf.sub("Ports Required on Managed Hosts (Agents)")
    pdf.table(
        ["Port", "Protocol", "Service", "Direction", "Access"],
        [
            ["8080", "TCP", "Agent API (Flask)", "Inbound", "From server only"],
            ["9100", "TCP", "Agent Prometheus metrics", "Inbound", "From Prometheus"],
        ],
        [20, 22, 55, 40, 53],
    )
    pdf.sub("Network Connectivity Requirements")
    pdf.table(
        ["From", "To", "Port", "Purpose"],
        [
            ["Agent", "Server", "8000", "Registration + heartbeat (every 60s)"],
            ["Server", "Agent", "8080", "Proxy commands (patch, snapshot, etc.)"],
            ["Server", "Internet", "80/443", "Download .deb packages (if not air-gapped)"],
            ["Prometheus", "Backend", "8000", "Scrape /metrics every 15s"],
            ["Prometheus", "Agent", "9100", "Scrape agent metrics"],
            ["Grafana", "Prometheus", "9090", "Query metrics data"],
            ["User Browser", "Server", "3000", "Access Web UI"],
            ["User Browser", "Server", "3001", "Access Grafana dashboards"],
        ],
        [40, 40, 20, 90],
    )
    pdf.sub("DNS / Hostname Requirements")
    pdf.bullet([
        "Server must be reachable by agents via IP or hostname",
        "Each managed host should have a unique hostname",
        "If using FQDN, ensure DNS resolution works from both server and agents",
    ])
    pdf.sub("Firewall Configuration (UFW Example)")
    pdf.code(
        "# On the PatchMaster server:\n"
        "sudo ufw allow 3000/tcp   # Web UI\n"
        "sudo ufw allow 3001/tcp   # Grafana\n"
        "sudo ufw allow 8000/tcp   # Backend API\n"
        "sudo ufw allow 9090/tcp   # Prometheus (optional)\n"
        "\n"
        "# On managed hosts (agents):\n"
        "sudo ufw allow from <server-ip> to any port 8080  # Agent API\n"
        "sudo ufw allow from <server-ip> to any port 9100  # Prometheus scrape"
    )
    pdf.sub("Firewall Configuration (firewalld / RHEL)")
    pdf.code(
        "# On the PatchMaster server:\n"
        "sudo firewall-cmd --permanent --add-port=3000/tcp\n"
        "sudo firewall-cmd --permanent --add-port=3001/tcp\n"
        "sudo firewall-cmd --permanent --add-port=8000/tcp\n"
        "sudo firewall-cmd --reload\n"
        "\n"
        "# On managed hosts:\n"
        "sudo firewall-cmd --permanent --add-rich-rule=\\\n"
        "  'rule family=ipv4 source address=<server-ip> port port=8080 protocol=tcp accept'\n"
        "sudo firewall-cmd --reload"
    )

    # ═══════════════════════════════════════
    # 6  Managed Host (Agent)
    # ═══════════════════════════════════════
    pdf.add_page()
    pdf.section("6", "Managed Host (Agent) Requirements")
    pdf.body(
        "Each Linux host to be managed by PatchMaster requires the PatchMaster agent. "
        "The agent is a self-contained .deb package with all dependencies bundled."
    )
    pdf.sub("Supported Operating Systems")
    pdf.table(
        ["OS", "Version", "Architecture", "Status"],
        [
            ["Ubuntu", "20.04 / 22.04 / 24.04", "amd64 / arm64", "Fully Supported"],
            ["Debian", "11 / 12", "amd64 / arm64", "Fully Supported"],
            ["Linux Mint", "20+ (Ubuntu-based)", "amd64", "Supported"],
            ["Pop!_OS", "22.04+", "amd64", "Supported"],
        ],
        [40, 50, 45, 55],
    )
    pdf.note("The agent uses dpkg/apt for package management. Only Debian-based distros are supported.")

    pdf.sub("Agent Host Requirements")
    pdf.table(
        ["Resource", "Minimum", "Notes"],
        [
            ["CPU", "1 core (any)", "Agent is lightweight"],
            ["RAM", "256 MB free", "Agent uses ~50 MB"],
            ["Disk", "50 MB free", "For agent + snapshots"],
            ["Python", "3.8+", "Must be pre-installed"],
            ["systemd", "Required", "For service management"],
            ["dpkg", "Required", "Package management"],
            ["Network", "Reach server:8000", "For registration & heartbeat"],
            ["Root/sudo", "Required", "For package installation"],
        ],
        [40, 50, 100],
    )

    pdf.sub("Pre-Installation Checklist for Each Agent Host")
    pdf.numbered([
        "Verify Python 3.8+ is installed: python3 --version",
        "Verify systemd is running: systemctl --version",
        "Verify dpkg is available: dpkg --version",
        "Verify network connectivity to server: curl http://<server-ip>:8000/api/health",
        "Verify port 8080 is not in use: ss -tlnp | grep 8080",
        "Verify sufficient disk space: df -h /var/lib",
        "Verify root/sudo access is available",
    ])

    pdf.sub("Air-Gapped / Offline Host Requirements")
    pdf.bullet([
        "No internet required -- agent .deb is self-contained with bundled Python venv",
        "Transfer .deb via USB, SCP, NFS, or any file copy method",
        "Network to server:8000 still required (internal network, not internet)",
        "Server-side patching downloads .debs on the server and pushes to agent",
    ])

    # ═══════════════════════════════════════
    # 7  Developer Workstation
    # ═══════════════════════════════════════
    pdf.add_page()
    pdf.section("7", "Developer Workstation Requirements")
    pdf.body("For developers who want to build, test, and modify PatchMaster locally.")
    pdf.sub("Required Software")
    pdf.table(
        ["Software", "Version", "Purpose", "Install Command"],
        [
            ["Git", "2.30+", "Source control", "apt install git"],
            ["Docker", "20.10+", "Container runtime", "curl -fsSL https://get.docker.com | sh"],
            ["Docker Compose", "v2.0+", "Orchestration", "(included with Docker)"],
            ["Python", "3.10+", "Backend development", "apt install python3.10 python3.10-venv"],
            ["Node.js", "18+", "Frontend development", "apt install nodejs npm"],
            ["npm", "8+", "Package manager", "(included with Node.js)"],
            ["VS Code", "Latest", "IDE (recommended)", "Download from code.visualstudio.com"],
        ],
        [30, 20, 48, 92],
    )
    pdf.sub("Recommended VS Code Extensions")
    pdf.bullet([
        "Python (Microsoft)",
        "Pylance",
        "Docker",
        "ES7+ React snippets",
        "REST Client or Thunder Client",
        "GitLens",
        "GitHub Copilot (optional)",
    ])
    pdf.sub("Python Development Setup")
    pdf.code(
        "# Create virtual environment\n"
        "cd backend/\n"
        "python3 -m venv venv\n"
        "source venv/bin/activate   # Linux/Mac\n"
        ".\\venv\\Scripts\\activate    # Windows\n"
        "\n"
        "# Install dependencies\n"
        "pip install -r requirements.txt\n"
        "\n"
        "# Required Python packages:\n"
        "#   fastapi, uvicorn, pydantic, python-dotenv\n"
        "#   httpx, sqlalchemy[asyncio], asyncpg\n"
        "#   python-jose[cryptography], passlib[bcrypt], bcrypt==4.0.1\n"
        "#   prometheus-client"
    )
    pdf.sub("Frontend Development Setup")
    pdf.code(
        "cd frontend/\n"
        "npm install\n"
        "npm start          # Dev server on port 3000\n"
        "npm run build       # Production build"
    )

    # ═══════════════════════════════════════
    # 8  Agent Build Machine
    # ═══════════════════════════════════════
    pdf.section("8", "Agent Build Machine Requirements")
    pdf.body(
        "To build the self-contained .deb agent package, you need an Ubuntu machine."
    )
    pdf.table(
        ["Requirement", "Details"],
        [
            ["OS", "Ubuntu 22.04 or 24.04 (native or WSL2)"],
            ["Python", "3.8+ with python3-venv and pip"],
            ["dpkg-deb", "For building .deb packages (pre-installed on Ubuntu)"],
            ["Internet", "Required during build (to pip install dependencies into venv)"],
            ["Disk", "500 MB free (for venv + build artifacts)"],
        ],
        [40, 150],
    )
    pdf.sub("Build Process")
    pdf.code(
        "cd agent/\n"
        "chmod +x build-deb.sh\n"
        "sudo ./build-deb.sh\n"
        "\n"
        "# Output: backend/static/agent-latest.deb (~4.4 MB)\n"
        "# Contains: Python venv + all pip deps + systemd service files"
    )
    pdf.note(
        "The build machine needs internet to pip install Flask, requests, and prometheus-client "
        "into the bundled venv. The resulting .deb requires no internet on target hosts."
    )

    # ═══════════════════════════════════════
    # 9  Browser
    # ═══════════════════════════════════════
    pdf.add_page()
    pdf.section("9", "Browser Requirements")
    pdf.body("PatchMaster Web UI and Grafana are accessed via web browser.")
    pdf.table(
        ["Browser", "Minimum Version", "Status"],
        [
            ["Google Chrome", "90+", "Recommended"],
            ["Mozilla Firefox", "90+", "Recommended"],
            ["Microsoft Edge", "90+ (Chromium)", "Supported"],
            ["Safari", "15+", "Supported"],
            ["Internet Explorer", "Any", "NOT Supported"],
        ],
        [55, 55, 80],
    )
    pdf.bullet([
        "JavaScript must be enabled",
        "Cookies must be enabled (for JWT token storage)",
        "Pop-up blockers should allow PatchMaster URLs",
        "Screen resolution: 1280x720 minimum, 1920x1080 recommended",
    ])

    # ═══════════════════════════════════════
    # 10 Monitoring
    # ═══════════════════════════════════════
    pdf.section("10", "Monitoring Stack Requirements")
    pdf.body(
        "Prometheus and Grafana run as Docker containers. No additional installation needed."
    )
    pdf.sub("Included in Docker Compose (no extra setup)")
    pdf.table(
        ["Component", "Image", "Port", "Notes"],
        [
            ["Prometheus", "prom/prometheus:latest", "9090", "Scrapes backend + agents"],
            ["Grafana", "grafana/grafana:latest", "3001", "Pre-provisioned dashboards"],
        ],
        [35, 65, 25, 65],
    )
    pdf.sub("For Zabbix Integration (Optional)")
    pdf.bullet([
        "Zabbix Server 5.0+ (installed separately, not part of PatchMaster)",
        "Configure HTTP Agent items pointing to PatchMaster API endpoints",
        "Or use Zabbix trapper items with the /api/zabbix/export/trapper endpoint",
        "PatchMaster provides LLD discovery endpoints for automatic host/CVE discovery",
    ])
    pdf.sub("Monitoring Disk Requirements")
    pdf.bullet([
        "Prometheus: ~1-2 MB per host per day (15s scrape interval, 30-day retention)",
        "Grafana: Minimal (~100 MB for config and plugins)",
        "Example: 100 hosts x 30 days = ~3-6 GB Prometheus storage",
    ])

    # ═══════════════════════════════════════
    # 11 Optional / Production
    # ═══════════════════════════════════════
    pdf.section("11", "Optional / Production Enhancements")
    pdf.body("These are not required but recommended for production deployments.")
    pdf.table(
        ["Enhancement", "Purpose", "Details"],
        [
            ["TLS Certificates", "HTTPS encryption", "Add to Nginx, use Let's Encrypt or internal CA"],
            ["LDAP/AD Integration", "Enterprise authentication", "Planned for future release"],
            ["Backup Solution", "Data protection", "Backup pgdata volume regularly"],
            ["Log Aggregation", "Centralized logging", "Forward Docker logs to ELK/Loki"],
            ["Reverse Proxy", "External access", "Nginx/HAProxy in front with TLS"],
            ["Container Registry", "Image distribution", "Push built images to private registry"],
            ["CI/CD Pipeline", "Automated deployment", "GitHub Actions or Jenkins"],
            ["Secrets Manager", "Secure credentials", "HashiCorp Vault, AWS Secrets Manager"],
        ],
        [40, 45, 105],
    )

    # ═══════════════════════════════════════
    # 12 Pre-Deployment Checklist
    # ═══════════════════════════════════════
    pdf.add_page()
    pdf.section("12", "Pre-Deployment Checklist")
    pdf.body("Complete this checklist before deploying PatchMaster.")
    pdf.sub("Server Preparation")
    pdf.table(
        ["#", "Task", "Check"],
        [
            ["1", "Server meets hardware requirements (CPU, RAM, Disk)", "[ ]"],
            ["2", "OS installed and updated", "[ ]"],
            ["3", "Docker Engine installed and running", "[ ]"],
            ["4", "Docker Compose v2 installed", "[ ]"],
            ["5", "User added to docker group", "[ ]"],
            ["6", "Firewall configured (ports 3000, 3001, 8000, 9090)", "[ ]"],
            ["7", "Git installed", "[ ]"],
            ["8", "Repository cloned", "[ ]"],
            ["9", "DNS/hostname configured (if applicable)", "[ ]"],
            ["10", "Disk volumes have sufficient space", "[ ]"],
        ],
        [10, 140, 40],
    )
    pdf.sub("Security Preparation")
    pdf.table(
        ["#", "Task", "Check"],
        [
            ["1", "Changed JWT_SECRET in docker-compose.yml", "[ ]"],
            ["2", "Changed PostgreSQL password in docker-compose.yml", "[ ]"],
            ["3", "Changed Grafana admin password in docker-compose.yml", "[ ]"],
            ["4", "TLS certificates obtained (if using HTTPS)", "[ ]"],
            ["5", "Network segmentation planned (agents -> server only)", "[ ]"],
            ["6", "Backup strategy defined for pgdata volume", "[ ]"],
        ],
        [10, 140, 40],
    )
    pdf.sub("Agent Preparation")
    pdf.table(
        ["#", "Task", "Check"],
        [
            ["1", "Agent .deb built (or downloaded from server)", "[ ]"],
            ["2", "Target hosts have Python 3.8+ installed", "[ ]"],
            ["3", "Target hosts have systemd running", "[ ]"],
            ["4", "Network path from agents to server:8000 verified", "[ ]"],
            ["5", "Network path from server to agents:8080 verified", "[ ]"],
            ["6", "Root/sudo access available on target hosts", "[ ]"],
            ["7", "Port 8080 free on target hosts", "[ ]"],
        ],
        [10, 140, 40],
    )

    # ═══════════════════════════════════════
    # 13 Verification Commands
    # ═══════════════════════════════════════
    pdf.add_page()
    pdf.section("13", "Quick Verification Commands")
    pdf.body("Run these commands to verify prerequisites are met.")
    pdf.sub("On the PatchMaster Server")
    pdf.code(
        "# Docker\n"
        "docker --version              # Should be 20.10+\n"
        "docker compose version        # Should be v2.0+\n"
        "docker info                   # Check Docker is running\n"
        "\n"
        "# Disk space\n"
        "df -h /var/lib/docker         # Docker storage\n"
        "df -h                         # Overall disk\n"
        "\n"
        "# Memory\n"
        "free -h                       # Should have 4GB+ available\n"
        "\n"
        "# Git\n"
        "git --version\n"
        "\n"
        "# Clone and deploy\n"
        "git clone https://github.com/yashkumardubey/Linux-tool-test.git\n"
        "cd Linux-tool-test\n"
        "docker compose up -d --build  # Deploy all 6 services\n"
        "docker compose ps             # Verify all services running\n"
        "curl http://localhost:8000/api/health  # Test backend"
    )
    pdf.sub("On Managed Linux Hosts (Before Agent Install)")
    pdf.code(
        "# Python\n"
        "python3 --version             # Should be 3.8+\n"
        "\n"
        "# systemd\n"
        "systemctl --version           # Must be systemd\n"
        "\n"
        "# dpkg\n"
        "dpkg --version                # Must be available\n"
        "\n"
        "# Network connectivity to server\n"
        "curl -s http://<server-ip>:8000/api/health\n"
        "# Should return: {\"status\":\"ok\"}\n"
        "\n"
        "# Port 8080 available\n"
        "ss -tlnp | grep 8080          # Should be empty\n"
        "\n"
        "# Disk space\n"
        "df -h /var/lib                # Need 50MB+ free"
    )
    pdf.sub("Post-Deployment Verification")
    pdf.code(
        "# All 6 services running\n"
        "docker compose ps\n"
        "\n"
        "# Backend API\n"
        "curl http://localhost:8000/api/health\n"
        "\n"
        "# Frontend\n"
        "curl -s http://localhost:3000 | head -5\n"
        "\n"
        "# Prometheus metrics\n"
        "curl http://localhost:8000/metrics | grep patchmaster\n"
        "\n"
        "# Prometheus targets\n"
        "curl http://localhost:9090/api/v1/targets\n"
        "\n"
        "# Grafana\n"
        "curl http://localhost:3001/api/health\n"
        "\n"
        "# Register first admin user via browser\n"
        "# Open http://<server-ip>:3000 and register"
    )

    path = os.path.join(OUTPUT_DIR, "SOP_PatchMaster_Prerequisites.pdf")
    pdf.output(path)
    print(f"Created: {path}")
    return path


if __name__ == "__main__":
    build_prerequisites()
