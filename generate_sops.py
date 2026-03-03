"""Generate two SOP PDF documents for PatchMaster — User SOP & Developer SOP."""
from fpdf import FPDF
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


class SopPDF(FPDF):
    """Custom PDF with header/footer for PatchMaster SOPs."""

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

    # ── helpers ──
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
        # header
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(0, 90, 180)
        self.set_text_color(255, 255, 255)
        for w, h in zip(col_widths, headers):
            self.cell(w, 7, f" {h}", border=1, fill=True)
        self.ln()
        # rows
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


# ═══════════════════════════════════════════
#  SOP 1 — USER GUIDE
# ═══════════════════════════════════════════
def build_user_sop():
    pdf = SopPDF("User SOP", "SOP-USR-001")
    pdf.alias_nb_pages()

    # Cover
    pdf.cover_page(
        "Standard Operating Procedure",
        "User Guide -- Operating PatchMaster from Start to End",
    )

    # ── TOC ──
    pdf.add_page()
    pdf.section("", "Table of Contents")
    toc = [
        "1.  Purpose & Scope",
        "2.  Prerequisites",
        "3.  Accessing PatchMaster",
        "4.  First-Time Setup (Admin Registration)",
        "5.  Dashboard Overview",
        "6.  Onboarding Linux Hosts",
        "7.  Managing Hosts",
        "8.  Host Groups & Tags",
        "9.  Patching Workflows",
        "10. Snapshots & Rollback",
        "11. Offline / Air-Gapped Patching",
        "12. Patch Scheduling",
        "13. CVE Tracking",
        "14. Compliance Monitoring",
        "15. Jobs & Audit Logs",
        "16. Notifications",
        "17. User Management (Admin)",
        "18. Monitoring (Grafana & Prometheus)",
        "19. Settings & Password Change",
        "20. Troubleshooting",
    ]
    pdf.bullet(toc)

    # ── 1 ──
    pdf.add_page()
    pdf.section("1", "Purpose & Scope")
    pdf.body(
        "This SOP provides step-by-step instructions for end users to operate PatchMaster -- "
        "a centralized Linux patch management platform. It covers daily operations including "
        "host onboarding, patching, snapshot management, CVE tracking, compliance monitoring, "
        "and monitoring integration."
    )
    pdf.body(
        "Target audience: System administrators, IT operators, security analysts, and auditors "
        "who use the PatchMaster web interface to manage Linux host patching."
    )

    # ── 2 ──
    pdf.section("2", "Prerequisites")
    pdf.bullet([
        "PatchMaster stack deployed and running (6 Docker services)",
        "Web browser (Chrome, Firefox, Edge recommended)",
        "Network access to the PatchMaster server",
        "Admin credentials (created during first-time setup)",
    ])
    pdf.sub("Access URLs")
    pdf.table(
        ["Service", "URL", "Credentials"],
        [
            ["Web UI (Frontend)", "http://<server-ip>:3000", "Login required"],
            ["Grafana Dashboards", "http://<server-ip>:3001", "admin / patchmaster"],
            ["Prometheus", "http://<server-ip>:9090", "No auth required"],
        ],
        [55, 75, 60],
    )

    # ── 3 ──
    pdf.section("3", "Accessing PatchMaster")
    pdf.numbered([
        "Open your web browser and navigate to http://<server-ip>:3000",
        "You will see the Login page with username and password fields",
        "Enter your credentials and click Login",
        "Upon successful login, you are redirected to the Dashboard",
    ])
    pdf.note("Replace <server-ip> with your PatchMaster server's IP address.")

    # ── 4 ──
    pdf.section("4", "First-Time Setup (Admin Registration)")
    pdf.body(
        "When PatchMaster is freshly deployed, no users exist. The first user registered "
        "becomes the admin automatically."
    )
    pdf.numbered([
        'On the Login page, click "Register" to open the registration form',
        "Enter a username, full name (optional), email, and password",
        'Click "Register" -- you are now the admin user',
        "Log in with your new credentials",
        "Navigate to Users page to create accounts for operators, viewers, and auditors",
    ])
    pdf.sub("User Roles")
    pdf.table(
        ["Role", "Permissions"],
        [
            ["Admin", "Full access: user management, delete operations, all settings"],
            ["Operator", "Create/update hosts, jobs, schedules, CVEs. Cannot manage users"],
            ["Viewer", "Read-only access to all dashboards and reports"],
            ["Auditor", "Read-only access, designed for compliance auditing"],
        ],
        [40, 150],
    )

    # ── 5 ──
    pdf.section("5", "Dashboard Overview")
    pdf.body(
        "The Dashboard is your central overview page showing the health of your Linux fleet."
    )
    pdf.sub("Dashboard Cards")
    pdf.bullet([
        "Total Hosts -- number of registered Linux hosts",
        "Online Hosts -- hosts that sent a heartbeat in the last 3 minutes",
        "Average Compliance Score -- fleet-wide compliance percentage",
        "Pending CVEs -- unpatched CVE count across all hosts",
        "Recent Jobs -- latest patch job results",
        "Compliance Distribution -- visual breakdown by group",
        "Quick Actions -- shortcuts to common tasks",
    ])

    # ── 6 ──
    pdf.add_page()
    pdf.section("6", "Onboarding Linux Hosts")
    pdf.body(
        "To manage a Linux host, you must install the PatchMaster agent on it. "
        "The agent registers itself and sends heartbeats every 60 seconds."
    )
    pdf.sub("Method 1: One-Command Install (Recommended)")
    pdf.body("Run this single command on the target Linux host as root:")
    pdf.code('curl -sS http://<server-ip>:3000/download/install.sh | sudo bash -s -- <server-ip>')
    pdf.body("This command will:")
    pdf.numbered([
        "Download the self-contained agent .deb package (no internet required on target)",
        "Install the package with dpkg (all Python dependencies are bundled)",
        "Configure the agent to connect to your PatchMaster server",
        "Start and enable two systemd services (heartbeat + API)",
        "The host appears in the Dashboard within 60 seconds",
    ])
    pdf.sub("Method 2: Manual Install")
    pdf.numbered([
        "Download agent-latest.deb from http://<server-ip>:3000/download/agent-latest.deb",
        "Copy the .deb to the target host via USB/SCP/etc.",
        "Run: sudo dpkg -i agent-latest.deb",
        "Create /etc/patch-agent/env with: CONTROLLER_URL=http://<server-ip>:8000",
        "Run: sudo systemctl enable --now patch-agent patch-agent-api",
    ])
    pdf.sub("Verifying Agent Registration")
    pdf.bullet([
        "Navigate to Hosts page in the UI",
        'The new host should appear with a green "Online" badge',
        "Click the host to view its details (OS, kernel, IP, packages)",
    ])

    # ── 7 ──
    pdf.section("7", "Managing Hosts")
    pdf.body("The Hosts page lists all registered Linux hosts with real-time status.")
    pdf.sub("Host Information Displayed")
    pdf.bullet([
        "Hostname, IP address, OS and version, kernel, architecture",
        "Online/Offline status (based on heartbeat)",
        "Compliance score (0-100%)",
        "Upgradable package count",
        "CVE count, Reboot required flag",
    ])
    pdf.sub("Host Actions")
    pdf.bullet([
        "Ping -- check if the agent is responding",
        "View Details -- full host information",
        "Delete -- remove a host (Admin only)",
        "Assign to Groups/Tags -- organize hosts",
    ])

    # ── 8 ──
    pdf.section("8", "Host Groups & Tags")
    pdf.body(
        "Groups and tags help you organize hosts for targeted patching and reporting."
    )
    pdf.sub("Creating a Group")
    pdf.numbered([
        "Navigate to Groups page from the sidebar",
        'Click "Create Group"',
        "Enter a group name and description",
        'Click "Save"',
        "Add hosts to the group using the Add Host button",
    ])
    pdf.sub("Using Tags")
    pdf.body(
        "Tags are lightweight labels (e.g., 'production', 'web-server', 'ubuntu-24'). "
        "Assign tags to hosts for flexible filtering across the UI."
    )

    # ── 9 ──
    pdf.add_page()
    pdf.section("9", "Patching Workflows")
    pdf.body(
        "PatchMaster supports multiple patching approaches depending on your environment."
    )
    pdf.sub("Standard Patch (Internet-Connected Hosts)")
    pdf.numbered([
        "Navigate to Patch Manager page",
        "Select a host from the dropdown",
        'Click "Check Updates" to scan for available updates',
        "Review the list of upgradable packages",
        "Select packages to patch (or select all)",
        "Enable Auto-Snapshot for safety (recommended)",
        'Click "Apply Patches"',
        "Monitor the job progress in real-time",
        "Job result shows success/failure with detailed log",
    ])
    pdf.sub("Server-Side Patch (Air-Gapped / Bandwidth-Optimized)")
    pdf.numbered([
        "Navigate to Patch Manager page and select a host",
        'Click "Check Updates" to see available packages',
        'Click "Server Download" -- PatchMaster downloads .deb files on the server',
        "Packages are automatically pushed to the agent",
        "Agent installs using dpkg (no internet needed on the host)",
        "Auto-snapshot and auto-rollback protect the host",
    ])
    pdf.note(
        "Server-side patching is ideal for air-gapped environments. The server "
        "downloads packages once and pushes them to agents over the internal network."
    )

    # ── 10 ──
    pdf.section("10", "Snapshots & Rollback")
    pdf.body(
        "Snapshots capture the current package state of a host, allowing you to "
        "rollback if a patch causes issues."
    )
    pdf.sub("Creating a Snapshot")
    pdf.numbered([
        "Navigate to Snapshots page",
        "Select a host",
        "Enter a snapshot name (e.g., 'pre-march-patch')",
        'Click "Create Snapshot"',
        "Snapshot captures: installed packages list, dpkg selections, apt sources",
    ])
    pdf.sub("Rolling Back")
    pdf.numbered([
        "Navigate to Snapshots page",
        "Select the snapshot to restore",
        'Click "Rollback"',
        "The agent restores dpkg selections and runs dselect-upgrade",
        "Verify the host state after rollback",
    ])
    pdf.note("Auto-rollback: When enabled during patching, if the patch job fails, "
             "the agent automatically restores the pre-patch snapshot.")

    # ── 11 ──
    pdf.section("11", "Offline / Air-Gapped Patching")
    pdf.numbered([
        "Navigate to Offline Patch page",
        "Select a target host",
        "Upload .deb package files from your local machine",
        "Enable 'Create pre-install snapshot' (recommended)",
        'Click "Install Packages"',
        "Agent installs via dpkg -i with automatic dependency resolution",
        "If installation fails and auto-rollback is enabled, snapshot is restored",
    ])

    # ── 12 ──
    pdf.add_page()
    pdf.section("12", "Patch Scheduling")
    pdf.body("Create schedules to automatically patch groups of hosts on a recurring basis.")
    pdf.numbered([
        "Navigate to Schedules page",
        'Click "Create Schedule"',
        "Enter schedule name, select a host group",
        "Set a cron expression (e.g., 0 2 * * 0 for every Sunday at 2 AM)",
        "Configure options: Auto-snapshot, Auto-rollback, Auto-reboot",
        "Optionally set blackout windows (times when patching is blocked)",
        'Click "Save"',
    ])
    pdf.sub("Cron Expression Examples")
    pdf.table(
        ["Expression", "Schedule"],
        [
            ["0 2 * * 0", "Every Sunday at 2:00 AM"],
            ["0 3 * * 1-5", "Weekdays at 3:00 AM"],
            ["0 0 1 * *", "First day of each month at midnight"],
            ["0 4 * * 6", "Every Saturday at 4:00 AM"],
        ],
        [60, 130],
    )

    # ── 13 ──
    pdf.section("13", "CVE Tracking")
    pdf.body("Track Common Vulnerabilities and Exposures across your fleet.")
    pdf.sub("Adding CVEs")
    pdf.numbered([
        "Navigate to CVE page",
        'Click "Add CVE"',
        "Enter CVE ID (e.g., CVE-2024-1234), severity, CVSS score",
        "Specify affected package and fixed-in version",
        'Click "Save"',
    ])
    pdf.sub("Mapping CVEs to Hosts")
    pdf.numbered([
        "Open a CVE entry",
        'Click "Map to Host" and select affected hosts',
        "Track patching progress per host",
        'Mark as patched when the fix is applied',
    ])
    pdf.sub("CVE Dashboard")
    pdf.bullet([
        "Severity distribution chart (Critical / High / Medium / Low)",
        "Total vs. Unpatched CVE counts",
        "Filter by severity, search by CVE ID",
    ])

    # ── 14 ──
    pdf.section("14", "Compliance Monitoring")
    pdf.body("The Compliance page provides a fleet-wide view of patch compliance.")
    pdf.sub("Three Views")
    pdf.bullet([
        "Overview -- aggregate stats, online/offline counts, compliance average",
        "By Group -- compliance score per host group",
        "By Host -- detailed per-host compliance with upgradable/CVE counts",
    ])
    pdf.body(
        "Compliance score is calculated based on: upgradable packages (lower is better), "
        "CVE count (lower is better), and reboot status."
    )

    # ── 15 ──
    pdf.section("15", "Jobs & Audit Logs")
    pdf.sub("Jobs Page")
    pdf.bullet([
        "View all patch job history with status badges (Success, Failed, Running, Pending)",
        "Filter by status, host, date range",
        "Click a job to see detailed execution log",
    ])
    pdf.sub("Audit Logs")
    pdf.bullet([
        "Tracks all user actions: who did what, when, and on which resource",
        "Filter by action type, resource, user, time period",
        "Essential for compliance auditing and change management",
    ])

    # ── 16 ──
    pdf.add_page()
    pdf.section("16", "Notifications")
    pdf.body("Configure notification channels to receive alerts on patch events.")
    pdf.sub("Supported Channels")
    pdf.table(
        ["Channel", "Config Required", "Use Case"],
        [
            ["Webhook", "URL", "Custom HTTP integrations"],
            ["Slack", "Webhook URL", "Team chat alerts"],
            ["Telegram", "Bot Token + Chat ID", "Mobile alerts"],
            ["Email", "SMTP server + recipient", "Email notifications"],
        ],
        [35, 75, 80],
    )
    pdf.sub("Setup Steps")
    pdf.numbered([
        "Navigate to Notifications page",
        'Click "Add Channel"',
        "Select channel type and enter configuration",
        "Select events to trigger notifications (e.g., patch_failed, cve_critical)",
        'Click "Save"',
        "Use 'Test' button to verify the channel works",
    ])

    # ── 17 ──
    pdf.section("17", "User Management (Admin Only)")
    pdf.numbered([
        "Navigate to Users page (visible only to admins)",
        "View all registered users with their roles",
        "Click a user to edit their role, email, or active status",
        "To add a new user: share the registration URL or create via API",
        "To deactivate a user: toggle 'Active' to off (they cannot login)",
        "To delete a user: click Delete (irreversible)",
    ])

    # ── 18 ──
    pdf.section("18", "Monitoring (Grafana & Prometheus)")
    pdf.sub("Grafana Dashboard")
    pdf.numbered([
        "Open http://<server-ip>:3001 in your browser",
        "Login with admin / patchmaster",
        "The PatchMaster Overview dashboard loads automatically (set as home)",
        "12 panels show: host stats, compliance, CVEs, job status, API metrics",
    ])
    pdf.sub("Dashboard Panels")
    pdf.bullet([
        "Total Hosts / Online Hosts / Reboot Required (stat panels)",
        "Average Compliance Score (gauge, 0-100%)",
        "Upgradable Packages count",
        "CVEs by Severity (pie chart)",
        "Unpatched CVEs (bar gauge)",
        "Jobs by Status (pie chart)",
        "API Request Rate & Latency P95 (time series)",
        "Hosts Online Over Time (time series)",
    ])
    pdf.sub("Prometheus")
    pdf.body(
        "Prometheus is available at http://<server-ip>:9090. It scrapes the backend "
        "every 15 seconds and retains data for 30 days. Use it for ad-hoc queries "
        "using PromQL."
    )

    # ── 19 ──
    pdf.section("19", "Settings & Password Change")
    pdf.bullet([
        "Navigate to Settings page from the sidebar",
        "View system information (version, Docker status)",
        "Change your password: enter current password + new password + confirm",
    ])

    # ── 20 ──
    pdf.add_page()
    pdf.section("20", "Troubleshooting")
    pdf.table(
        ["Problem", "Solution"],
        [
            ["Host shows Offline", "Check agent services: systemctl status patch-agent patch-agent-api"],
            ["Agent not registering", "Verify CONTROLLER_URL in /etc/patch-agent/env points to server"],
            ["Login fails", "Clear browser cache, verify username/password, check backend logs"],
            ["Patches fail", "Check agent logs: journalctl -u patch-agent-api, verify apt sources"],
            ["Grafana shows no data", "Verify Prometheus is scraping: check http://<ip>:9090/targets"],
            ["Blank page after login", "Clear localStorage in browser, hard refresh (Ctrl+Shift+R)"],
            ["Package download fails", "For air-gapped: use Server Download or Offline Patch workflow"],
            ["Rollback fails", "Ensure snapshot exists, check dpkg/apt state on the agent"],
        ],
        [55, 135],
    )
    pdf.sub("Useful Commands (on the agent host)")
    pdf.code(
        "# Check agent services\n"
        "systemctl status patch-agent\n"
        "systemctl status patch-agent-api\n"
        "\n"
        "# View agent logs\n"
        "journalctl -u patch-agent -f\n"
        "journalctl -u patch-agent-api -f\n"
        "\n"
        "# Restart agent\n"
        "sudo systemctl restart patch-agent patch-agent-api\n"
        "\n"
        "# Check connection to server\n"
        "curl -s http://<server-ip>:8000/api/health"
    )

    path = os.path.join(OUTPUT_DIR, "SOP_PatchMaster_User_Guide.pdf")
    pdf.output(path)
    print(f"Created: {path}")
    return path


# ═══════════════════════════════════════════
#  SOP 2 — DEVELOPER GUIDE
# ═══════════════════════════════════════════
def build_dev_sop():
    pdf = SopPDF("Developer SOP", "SOP-DEV-001")
    pdf.alias_nb_pages()

    # Cover
    pdf.cover_page(
        "Standard Operating Procedure",
        "Developer Guide -- Setup, Architecture, API & Maintenance",
    )

    # ── TOC ──
    pdf.add_page()
    pdf.section("", "Table of Contents")
    toc = [
        "1.  Purpose & Scope",
        "2.  Architecture Overview",
        "3.  Technology Stack",
        "4.  Prerequisites",
        "5.  Repository Structure",
        "6.  Local Development Setup",
        "7.  Docker Deployment",
        "8.  Database Schema",
        "9.  Backend API Reference",
        "10. Authentication & RBAC",
        "11. Agent Architecture",
        "12. Frontend Architecture",
        "13. Monitoring Stack",
        "14. Building the Agent .deb Package",
        "15. Configuration Reference",
        "16. Adding New Features",
        "17. Troubleshooting & Debugging",
        "18. Security Considerations",
    ]
    pdf.bullet(toc)

    # ── 1 ──
    pdf.add_page()
    pdf.section("1", "Purpose & Scope")
    pdf.body(
        "This SOP provides developers with complete technical documentation to set up, "
        "develop, extend, and maintain PatchMaster. It covers architecture, API reference, "
        "database schema, agent internals, deployment, and security guidelines."
    )

    # ── 2 ──
    pdf.section("2", "Architecture Overview")
    pdf.body(
        "PatchMaster follows a hub-and-spoke architecture with a central server and "
        "distributed agents on managed Linux hosts."
    )
    pdf.sub("Component Diagram")
    pdf.code(
        "[React SPA :3000] --> [FastAPI Backend :8000] --> [PostgreSQL :5432]\n"
        "                            |       ^\n"
        "                            v       |\n"
        "                    [Linux Agents :8080]\n"
        "                    [Heartbeat every 60s]\n"
        "\n"
        "[Prometheus :9090] --> [Grafana :3001]"
    )
    pdf.sub("Data Flow")
    pdf.numbered([
        "Agent registers with backend via POST /api/register",
        "Agent sends heartbeat every 60s with system inventory",
        "User triggers patch via UI -> backend proxies to agent API",
        "Server-side patch: backend downloads .debs -> pushes to agent",
        "Prometheus scrapes /metrics from backend every 15 seconds",
        "Grafana queries Prometheus for dashboard visualization",
    ])

    # ── 3 ──
    pdf.section("3", "Technology Stack")
    pdf.table(
        ["Component", "Technology", "Version"],
        [
            ["Backend", "FastAPI + Uvicorn", "Python 3.10"],
            ["Database", "PostgreSQL + SQLAlchemy (async) + asyncpg", "PG 15"],
            ["Auth", "python-jose (JWT) + passlib (bcrypt)", ""],
            ["Frontend", "React (CRA) + Nginx", "React 18"],
            ["Agent", "Flask", "Python 3.8+"],
            ["Monitoring", "Prometheus + Grafana", "Latest"],
            ["Containers", "Docker Compose", "v2"],
            ["Package", "Self-contained .deb", "dpkg"],
        ],
        [40, 100, 50],
    )

    # ── 4 ──
    pdf.section("4", "Prerequisites")
    pdf.sub("Development Machine")
    pdf.bullet([
        "Docker and Docker Compose v2",
        "Git",
        "Python 3.10+ (for local backend development)",
        "Node.js 18+ and npm (for local frontend development)",
        "WSL2 (if developing on Windows)",
    ])
    pdf.sub("Agent Build Machine")
    pdf.bullet([
        "Ubuntu 22.04 or 24.04 (for building .deb packages)",
        "Python 3.8+ with venv, pip, dpkg-deb",
    ])

    # ── 5 ──
    pdf.add_page()
    pdf.section("5", "Repository Structure")
    pdf.code(
        "Linux_tool/\n"
        "|\n"
        "+-- docker-compose.yml          # 6 services orchestration\n"
        "+-- backend/\n"
        "|   +-- main.py                 # FastAPI entry point\n"
        "|   +-- auth.py                 # JWT + RBAC logic\n"
        "|   +-- database.py             # Async SQLAlchemy engine\n"
        "|   +-- Dockerfile\n"
        "|   +-- requirements.txt\n"
        "|   +-- api/                    # 13 API modules\n"
        "|   |   +-- auth_api.py         # Login, register, user CRUD\n"
        "|   |   +-- register_v2.py      # Agent registration + heartbeat\n"
        "|   |   +-- hosts_v2.py         # Host CRUD\n"
        "|   |   +-- jobs_v2.py          # Patch jobs\n"
        "|   |   +-- agent_proxy.py      # Proxy to agent API\n"
        "|   |   +-- groups.py           # Groups + tags\n"
        "|   |   +-- schedules.py        # Cron scheduling\n"
        "|   |   +-- compliance.py       # Compliance dashboard\n"
        "|   |   +-- cve.py              # CVE tracking\n"
        "|   |   +-- audit.py            # Audit trail\n"
        "|   |   +-- notifications.py    # Alert channels\n"
        "|   |   +-- metrics.py          # Prometheus endpoint\n"
        "|   |   +-- zabbix.py           # Zabbix integration\n"
        "|   +-- models/db_models.py     # All ORM models\n"
        "|   +-- static/                 # .deb + install.sh\n"
        "+-- agent/\n"
        "|   +-- agent.py                # Flask API server\n"
        "|   +-- main.py                 # Heartbeat loop\n"
        "|   +-- build-deb.sh            # Self-contained .deb builder\n"
        "+-- frontend/\n"
        "|   +-- src/App.js              # Single-file React SPA (16 pages)\n"
        "|   +-- nginx.conf              # Reverse proxy config\n"
        "+-- monitoring/\n"
        "    +-- prometheus/prometheus.yml\n"
        "    +-- grafana/dashboards/     # Pre-built dashboard JSON\n"
        "    +-- grafana/provisioning/   # Auto-config datasource"
    )

    # ── 6 ──
    pdf.section("6", "Local Development Setup")
    pdf.sub("Clone Repository")
    pdf.code(
        "git clone https://github.com/yashkumardubey/Linux-tool-test.git\n"
        "cd Linux-tool-test"
    )
    pdf.sub("Backend (Local)")
    pdf.code(
        "cd backend\n"
        "python -m venv venv && source venv/bin/activate\n"
        "pip install -r requirements.txt\n"
        "export DATABASE_URL=postgresql+asyncpg://patchmaster:patchmaster@localhost:5432/patchmaster\n"
        "export JWT_SECRET=dev-secret-key\n"
        "uvicorn main:app --reload --port 8000"
    )
    pdf.sub("Frontend (Local)")
    pdf.code(
        "cd frontend\n"
        "npm install\n"
        "npm start    # Starts on port 3000 with hot reload"
    )
    pdf.sub("Quick Start (Docker)")
    pdf.code(
        "docker compose up -d --build\n"
        "# All 6 services start: db, backend, agent, frontend, prometheus, grafana"
    )

    # ── 7 ──
    pdf.add_page()
    pdf.section("7", "Docker Deployment")
    pdf.sub("Services")
    pdf.table(
        ["Service", "Image/Build", "Port", "Depends On"],
        [
            ["db", "postgres:15-alpine", "5432 (internal)", "-"],
            ["backend", "./backend (Dockerfile)", "8000:8000", "db (healthy)"],
            ["agent", "./agent (Dockerfile)", "internal", "backend"],
            ["frontend", "./frontend (Dockerfile)", "3000:80", "backend"],
            ["prometheus", "prom/prometheus:latest", "9090:9090", "backend"],
            ["grafana", "grafana/grafana:latest", "3001:3000", "prometheus"],
        ],
        [30, 65, 45, 50],
    )
    pdf.sub("Volumes")
    pdf.bullet([
        "pgdata -- PostgreSQL persistent data",
        "prometheus_data -- Prometheus time-series data (30-day retention)",
        "grafana_data -- Grafana settings and user data",
    ])
    pdf.sub("Common Commands")
    pdf.code(
        "# Full rebuild and deploy\n"
        "docker compose up -d --build\n"
        "\n"
        "# Rebuild single service\n"
        "docker compose up -d --build --force-recreate backend\n"
        "\n"
        "# View logs\n"
        "docker compose logs -f backend\n"
        "docker compose logs -f agent\n"
        "\n"
        "# Check health\n"
        "docker compose ps\n"
        "curl http://localhost:8000/api/health\n"
        "\n"
        "# Stop everything\n"
        "docker compose down\n"
        "\n"
        "# Stop and remove volumes (DESTRUCTIVE)\n"
        "docker compose down -v"
    )

    # ── 8 ──
    pdf.add_page()
    pdf.section("8", "Database Schema")
    pdf.body("PostgreSQL 15 with SQLAlchemy async ORM. 13 tables total.")
    pdf.table(
        ["Table", "Key Fields", "Purpose"],
        [
            ["users", "id, username, hashed_password, role, is_active", "User accounts + RBAC"],
            ["hosts", "id, hostname, ip, os, compliance_score, is_online", "Managed Linux hosts"],
            ["host_groups", "id, name, description", "Logical host grouping"],
            ["tags", "id, name", "Lightweight host labels"],
            ["host_group_assoc", "host_id, group_id", "M2M: hosts <-> groups"],
            ["host_tag_assoc", "host_id, tag_id", "M2M: hosts <-> tags"],
            ["patch_jobs", "id, host_id, action, status, packages", "Patch execution records"],
            ["patch_schedules", "id, group_id, cron_expression", "Cron-based scheduling"],
            ["snapshots", "id, host_id, name, packages_count", "Package state snapshots"],
            ["cves", "id, cve_id, severity, cvss_score", "CVE database"],
            ["host_cves", "id, host_id, cve_id, is_patched", "Host-CVE mapping"],
            ["audit_logs", "id, user_id, action, resource_type", "Audit trail"],
            ["notification_channels", "id, name, type, config, events", "Alert channels"],
        ],
        [45, 80, 65],
    )
    pdf.sub("Enums")
    pdf.table(
        ["Enum", "Values"],
        [
            ["Role", "admin, operator, viewer, auditor"],
            ["JobStatus", "pending, scheduled, running, success, failed, cancelled, rolled_back"],
            ["JobAction", "upgrade, install, remove, rollback, security_only"],
            ["Severity", "critical, high, medium, low, negligible"],
            ["ChannelType", "webhook, slack, telegram, email"],
        ],
        [40, 150],
    )

    # ── 9 ──
    pdf.add_page()
    pdf.section("9", "Backend API Reference")
    pdf.body(
        "All API endpoints are under /api/ (except /metrics). JWT required unless noted."
    )

    api_groups = [
        ("Auth  /api/auth", [
            ["POST", "/api/auth/login", "Public", "Returns JWT token"],
            ["POST", "/api/auth/register", "Public", "First user = admin"],
            ["GET", "/api/auth/me", "JWT", "Current user profile"],
            ["GET", "/api/auth/users", "Admin", "List all users"],
            ["PUT", "/api/auth/users/{id}", "Admin", "Update user"],
            ["DELETE", "/api/auth/users/{id}", "Admin", "Delete user"],
            ["POST", "/api/auth/change-password", "JWT", "Change password"],
        ]),
        ("Registration  /api", [
            ["POST", "/api/register", "Open", "Agent self-registers"],
            ["POST", "/api/heartbeat", "Token", "Agent heartbeat"],
        ]),
        ("Hosts  /api/hosts", [
            ["GET", "/api/hosts/", "JWT", "List hosts (filters: search, group, tag)"],
            ["GET", "/api/hosts/{id}", "JWT", "Get single host"],
            ["POST", "/api/hosts/", "Admin/Op", "Create host"],
            ["PUT", "/api/hosts/{id}", "Admin/Op", "Update host"],
            ["DELETE", "/api/hosts/{id}", "Admin", "Delete host"],
        ]),
        ("Jobs  /api/jobs", [
            ["GET", "/api/jobs/", "JWT", "List jobs"],
            ["GET", "/api/jobs/stats", "JWT", "Job statistics"],
            ["POST", "/api/jobs/", "Admin/Op", "Create job"],
            ["DELETE", "/api/jobs/{id}", "Admin", "Delete job"],
        ]),
        ("Agent Proxy  /api/agent", [
            ["GET", "/api/agent/{ip}/packages/installed", "JWT", "Installed packages"],
            ["GET", "/api/agent/{ip}/packages/upgradable", "JWT", "Upgradable packages"],
            ["POST", "/api/agent/{ip}/packages/refresh", "JWT", "apt-get update"],
            ["POST", "/api/agent/{ip}/patch/execute", "JWT", "Direct patch"],
            ["POST", "/api/agent/{ip}/patch/server-patch", "JWT", "Server-side patch"],
            ["POST", "/api/agent/{ip}/snapshot/create", "JWT", "Create snapshot"],
            ["POST", "/api/agent/{ip}/snapshot/rollback", "JWT", "Rollback snapshot"],
            ["POST", "/api/agent/{ip}/offline/install", "JWT", "Install .debs"],
        ]),
        ("Groups & Tags", [
            ["GET", "/api/groups/", "JWT", "List groups"],
            ["POST", "/api/groups/", "Admin/Op", "Create group"],
            ["POST", "/api/groups/{id}/hosts/{hid}", "Admin/Op", "Add host to group"],
            ["GET", "/api/tags/", "JWT", "List tags"],
        ]),
        ("Schedules  /api/schedules", [
            ["GET", "/api/schedules/", "JWT", "List schedules"],
            ["POST", "/api/schedules/", "Admin/Op", "Create schedule"],
            ["PUT", "/api/schedules/{id}", "Admin/Op", "Update schedule"],
            ["DELETE", "/api/schedules/{id}", "Admin", "Delete schedule"],
        ]),
        ("Compliance  /api/compliance", [
            ["GET", "/api/compliance/overview", "JWT", "Dashboard stats"],
            ["GET", "/api/compliance/by-group", "JWT", "Per-group compliance"],
            ["GET", "/api/compliance/hosts-detail", "JWT", "Per-host detail"],
        ]),
        ("CVE  /api/cve", [
            ["GET", "/api/cve/", "JWT", "List CVEs"],
            ["POST", "/api/cve/", "Admin/Op", "Create CVE"],
            ["POST", "/api/cve/map", "Admin/Op", "Map CVE to host"],
            ["POST", "/api/cve/map/{id}/mark-patched", "Admin/Op", "Mark patched"],
        ]),
        ("Monitoring", [
            ["GET", "/metrics", "Public", "Prometheus scrape endpoint"],
            ["GET", "/api/zabbix/discovery/hosts", "JWT", "Zabbix LLD hosts"],
            ["GET", "/api/zabbix/discovery/cves", "JWT", "Zabbix LLD CVEs"],
            ["GET", "/api/zabbix/items/overview", "JWT", "All metrics JSON"],
            ["GET", "/api/zabbix/export/trapper", "JWT", "zabbix_sender format"],
        ]),
    ]
    for group_name, endpoints in api_groups:
        pdf.sub(group_name)
        pdf.table(
            ["Method", "Endpoint", "Auth", "Description"],
            endpoints,
            [18, 75, 25, 72],
        )

    # ── 10 ──
    pdf.add_page()
    pdf.section("10", "Authentication & RBAC")
    pdf.sub("JWT Flow")
    pdf.numbered([
        "Client POSTs username/password to /api/auth/login",
        "Backend validates credentials against bcrypt hash in DB",
        "Returns JWT with claims: sub (username), role, exp (8h default)",
        "Client stores token in localStorage",
        "All subsequent requests include: Authorization: Bearer <token>",
        "Backend middleware validates token and extracts user",
        "RBAC decorators check user.role against required permissions",
    ])
    pdf.sub("Role Permissions Matrix")
    pdf.table(
        ["Operation", "Admin", "Operator", "Viewer", "Auditor"],
        [
            ["Read all dashboards", "Yes", "Yes", "Yes", "Yes"],
            ["Create/update hosts, jobs", "Yes", "Yes", "No", "No"],
            ["Delete resources", "Yes", "No", "No", "No"],
            ["Manage users", "Yes", "No", "No", "No"],
            ["Manage notifications", "Yes", "No", "No", "No"],
            ["Execute patches", "Yes", "Yes", "No", "No"],
        ],
        [50, 30, 30, 30, 30],
    )
    pdf.sub("Key Files")
    pdf.bullet([
        "backend/auth.py -- get_current_user(), require_role() dependency",
        "backend/api/auth_api.py -- login, register, user CRUD endpoints",
        "JWT_SECRET env var -- must be set in production",
    ])

    # ── 11 ──
    pdf.section("11", "Agent Architecture")
    pdf.sub("Two Processes per Host")
    pdf.table(
        ["Process", "File", "Systemd Service", "Port", "Function"],
        [
            ["Heartbeat", "agent/main.py", "patch-agent", "-", "Register + heartbeat loop (60s)"],
            ["API Server", "agent/agent.py", "patch-agent-api", "8080", "Flask REST API for patching"],
        ],
        [28, 32, 38, 20, 72],
    )
    pdf.sub("Agent API Endpoints (Flask on port 8080)")
    pdf.table(
        ["Method", "Path", "Function"],
        [
            ["GET", "/health", "Agent health check"],
            ["GET", "/packages/installed", "dpkg-query installed list"],
            ["GET", "/packages/upgradable", "apt list --upgradable"],
            ["POST", "/packages/refresh", "apt-get update"],
            ["POST", "/patch/execute", "Full patch with snapshot/rollback"],
            ["POST", "/snapshot/create", "dpkg snapshot"],
            ["POST", "/snapshot/rollback", "dpkg --set-selections restore"],
            ["POST", "/offline/upload", "Receive .deb files"],
            ["POST", "/offline/install", "dpkg -i install"],
        ],
        [20, 60, 110],
    )
    pdf.sub("Snapshot Mechanism (dpkg-based)")
    pdf.numbered([
        "Captures dpkg-query -W -> packages.txt",
        "Captures dpkg --get-selections -> selections.txt",
        "Copies /etc/apt/sources.list*",
        "Stores in /var/lib/patch-agent/snapshots/<name>/",
        "Rollback: dpkg --set-selections + apt-get dselect-upgrade -y --allow-downgrades",
    ])

    # ── 12 ──
    pdf.add_page()
    pdf.section("12", "Frontend Architecture")
    pdf.body(
        "The frontend is a single-file React SPA (src/App.js, ~837 lines) served by Nginx."
    )
    pdf.sub("16 Page Components")
    pdf.table(
        ["Page", "Nav Key", "Description"],
        [
            ["DashboardPage", "dashboard", "Stats cards, compliance, recent activity"],
            ["CompliancePage", "compliance", "Overview / By Group / By Host views"],
            ["HostsPage", "hosts", "Host list with agent status"],
            ["GroupsPage", "groups", "Host groups and tags CRUD"],
            ["PatchManagerPage", "patches", "Core patching workflow"],
            ["SnapshotsPage", "snapshots", "Create/list/rollback snapshots"],
            ["ComparePackagesPage", "compare", "Installed vs available diff"],
            ["OfflinePatchPage", "offline", "Air-gapped .deb install"],
            ["SchedulesPage", "schedules", "Cron-based patch schedules"],
            ["CVEPage", "cve", "CVE tracker with severity stats"],
            ["JobsPage", "jobs", "Job history with status badges"],
            ["AuditPage", "audit", "Audit log viewer"],
            ["NotificationsPage", "notifications", "Alert channel management"],
            ["UsersPage", "users", "User management (admin)"],
            ["OnboardingPage", "onboarding", "Agent install instructions"],
            ["SettingsPage", "settings", "System info, password change"],
        ],
        [50, 30, 110],
    )
    pdf.sub("Nginx Configuration (frontend/nginx.conf)")
    pdf.bullet([
        "/api/* -- proxied to backend:8000",
        "/download/* -- proxied to backend:8000/static/ (agent .deb + install.sh)",
        "/* -- served from /usr/share/nginx/html (React build)",
    ])
    pdf.sub("Build Pipeline")
    pdf.code(
        "# Dockerfile (multi-stage)\n"
        "Stage 1: node:18-alpine -> npm install -> npm run build\n"
        "Stage 2: nginx:alpine  -> copy build/ + nginx.conf -> serve"
    )

    # ── 13 ──
    pdf.add_page()
    pdf.section("13", "Monitoring Stack")
    pdf.sub("Prometheus Metrics Exposed")
    pdf.table(
        ["Metric", "Type", "Description"],
        [
            ["patchmaster_hosts_total", "Gauge", "Total registered hosts"],
            ["patchmaster_hosts_online", "Gauge", "Currently online hosts"],
            ["patchmaster_hosts_reboot_required", "Gauge", "Hosts needing reboot"],
            ["patchmaster_packages_upgradable_total", "Gauge", "Upgradable packages"],
            ["patchmaster_compliance_avg_score", "Gauge", "Avg compliance (0-100)"],
            ["patchmaster_cve_total{severity}", "Gauge", "CVEs by severity"],
            ["patchmaster_cve_unpatched_total{severity}", "Gauge", "Unpatched CVEs"],
            ["patchmaster_jobs_total{status}", "Counter", "Jobs by status"],
            ["patchmaster_api_requests_total", "Counter", "API requests (method,path,status)"],
            ["patchmaster_api_request_duration_seconds", "Histogram", "API latency"],
        ],
        [75, 25, 90],
    )
    pdf.sub("Prometheus Configuration")
    pdf.code(
        "# monitoring/prometheus/prometheus.yml\n"
        "scrape_configs:\n"
        "  - job_name: patchmaster-backend\n"
        "    static_configs:\n"
        "      - targets: ['backend:8000']\n"
        "    scrape_interval: 15s\n"
        "\n"
        "  - job_name: patchmaster-agents\n"
        "    static_configs:\n"
        "      - targets: ['agent:9100']\n"
        "\n"
        "Retention: 30 days"
    )
    pdf.sub("Grafana")
    pdf.bullet([
        "Auto-provisioned Prometheus datasource",
        "Pre-built PatchMaster Overview dashboard (12 panels)",
        "Set as home dashboard via GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH",
        "Login: admin / patchmaster",
    ])
    pdf.sub("Zabbix Integration")
    pdf.bullet([
        "LLD Discovery: /api/zabbix/discovery/hosts, /api/zabbix/discovery/cves",
        "HTTP Agent Items: /api/zabbix/items/overview, /api/zabbix/items/host/{id}",
        "Trapper Export: /api/zabbix/export/trapper (zabbix_sender format)",
    ])

    # ── 14 ──
    pdf.section("14", "Building the Agent .deb Package")
    pdf.body("The agent is packaged as a self-contained .deb with bundled Python venv.")
    pdf.sub("Build Steps")
    pdf.code(
        "# On Ubuntu 22.04/24.04:\n"
        "cd agent/\n"
        "chmod +x build-deb.sh\n"
        "sudo ./build-deb.sh\n"
        "\n"
        "# Output: backend/static/agent-latest.deb (~4.4 MB)\n"
        "# Contains: Python venv + all pip deps + systemd services"
    )
    pdf.sub("What build-deb.sh Does")
    pdf.numbered([
        "Creates a Python virtualenv",
        "pip installs flask, requests, prometheus-client into the venv",
        "Copies agent source code (agent.py, main.py)",
        "Creates wrapper scripts (run-heartbeat.sh, run-api.sh)",
        "Creates DEBIAN/control (depends only on python3)",
        "Creates DEBIAN/postinst (fixes venv paths, creates user/dirs)",
        "Creates DEBIAN/prerm (stops systemd services)",
        "Builds .deb with dpkg-deb --build",
    ])
    pdf.note("The .deb is fully self-contained. No internet/pip/apt needed on target hosts.")

    # ── 15 ──
    pdf.add_page()
    pdf.section("15", "Configuration Reference")
    pdf.table(
        ["Variable", "Service", "Default", "Description"],
        [
            ["DATABASE_URL", "backend", "postgresql+asyncpg://...", "Async DB connection string"],
            ["JWT_SECRET", "backend", "change-me-to-...", "JWT signing key (CHANGE IN PROD)"],
            ["TOKEN_EXPIRE_MINUTES", "backend", "480 (8 hours)", "JWT token expiry"],
            ["CONTROLLER_URL", "agent", "http://backend:8000", "Backend URL for agent"],
            ["GF_SECURITY_ADMIN_USER", "grafana", "admin", "Grafana admin username"],
            ["GF_SECURITY_ADMIN_PASSWORD", "grafana", "patchmaster", "Grafana admin password"],
            ["POSTGRES_USER", "db", "patchmaster", "PostgreSQL username"],
            ["POSTGRES_PASSWORD", "db", "patchmaster", "PostgreSQL password"],
            ["POSTGRES_DB", "db", "patchmaster", "PostgreSQL database name"],
        ],
        [52, 22, 52, 64],
    )

    # ── 16 ──
    pdf.section("16", "Adding New Features")
    pdf.sub("Adding a New API Module")
    pdf.numbered([
        "Create backend/api/new_feature.py with an APIRouter",
        "Define routes with appropriate auth dependencies",
        "Add ORM models to backend/models/db_models.py if needed",
        "Import and include_router() in backend/main.py",
        "Add frontend page component in src/App.js",
        "Add navigation entry in the sidebar menu array",
        "Rebuild: docker compose up -d --build backend frontend",
    ])
    pdf.sub("Adding a Grafana Panel")
    pdf.numbered([
        "Add a new Prometheus metric in backend/api/metrics.py",
        "Add the panel JSON to monitoring/grafana/dashboards/patchmaster-overview.json",
        "Rebuild Grafana: docker compose up -d --force-recreate grafana",
    ])

    # ── 17 ──
    pdf.section("17", "Troubleshooting & Debugging")
    pdf.sub("Useful Debug Commands")
    pdf.code(
        "# Backend logs\n"
        "docker compose logs -f backend\n"
        "\n"
        "# Database shell\n"
        "docker compose exec db psql -U patchmaster\n"
        "\n"
        "# Test API\n"
        "curl -s http://localhost:8000/api/health\n"
        "curl -s http://localhost:8000/metrics | grep patchmaster\n"
        "\n"
        "# Check Prometheus targets\n"
        "curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool\n"
        "\n"
        "# Rebuild single service\n"
        "docker compose up -d --build --force-recreate <service>\n"
        "\n"
        "# Agent logs (on host)\n"
        "journalctl -u patch-agent -f\n"
        "journalctl -u patch-agent-api -f"
    )
    pdf.sub("Common Issues")
    pdf.table(
        ["Issue", "Cause", "Fix"],
        [
            ["Port 5432 conflict", "Host PostgreSQL running", "Remove db host port mapping"],
            ["func.lower() on Enum", "PG Enum not text", "Compare directly: CVE.severity == Severity.x"],
            ["Agent not connecting", "Wrong CONTROLLER_URL", "Check /etc/patch-agent/env"],
            ["JWT invalid", "Wrong JWT_SECRET", "Ensure JWT_SECRET matches in docker-compose.yml"],
            ["Blank page after login", "Form-urlencoded vs JSON", "Frontend must POST JSON to /api/auth/login"],
            [".deb install fails", "Missing deps on target", "Use build-deb.sh for self-contained .deb"],
        ],
        [42, 50, 98],
    )

    # ── 18 ──
    pdf.add_page()
    pdf.section("18", "Security Considerations")
    pdf.sub("Production Checklist")
    pdf.bullet([
        "Change JWT_SECRET to a strong random value (min 32 chars)",
        "Change default Grafana password (admin/patchmaster)",
        "Change PostgreSQL credentials",
        "Enable HTTPS/TLS on Nginx (add certificates to frontend)",
        "Restrict CORS origins (currently allows all)",
        "Use network segmentation -- agents should only reach backend:8000",
        "Enable firewall rules: only expose ports 3000, 3001, 9090 to trusted networks",
        "Rotate JWT tokens -- current 8h expiry is reasonable",
        "Run agent as non-root where possible (patch operations need sudo)",
        "Audit logs capture all user actions -- review regularly",
    ])
    pdf.sub("SSRF Protection")
    pdf.body(
        "The agent proxy (backend/api/agent_proxy.py) validates target IP addresses "
        "before proxying requests. Private/loopback IPs are blocked to prevent SSRF attacks "
        "against internal services."
    )
    pdf.sub("Password Security")
    pdf.body(
        "Passwords are hashed with bcrypt (passlib). Minimum requirements should be "
        "enforced in production. The bcrypt version is pinned to 4.0.1 for compatibility."
    )

    path = os.path.join(OUTPUT_DIR, "SOP_PatchMaster_Developer_Guide.pdf")
    pdf.output(path)
    print(f"Created: {path}")
    return path


if __name__ == "__main__":
    build_user_sop()
    build_dev_sop()
    print("\nBoth SOP PDFs generated successfully!")
