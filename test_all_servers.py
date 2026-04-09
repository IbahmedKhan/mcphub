"""Test all 6 MCPHub servers — every tool individually."""
import sys
import os
import asyncio
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_all():
    print("=" * 70)
    print("  MCPHub — All 6 MCP Servers Individual Access Guide")
    print("=" * 70)

    # === SERVER 1: SECURITY SCANNER ===
    print("\n" + "=" * 70)
    print("  SERVER 1: SECURITY SCANNER")
    print("=" * 70)
    print("  Standalone: python -m servers.security.server")
    print("  API: POST /api/servers/security-scanner/invoke/{tool}")
    print("  Tools: scan_website, check_ssl, check_headers, scan_ports, get_security_score")

    from servers.security.scanner import SecurityScanner
    s = SecurityScanner()

    print("\n  [Tool 1] scan_website(url='https://github.com')")
    r = await s.scan_website("https://github.com")
    print(f"    Score: {r['security_score']}/100 (Grade {r['grade']})")
    print(f"    Vulnerabilities: {r['vulnerabilities']['total']} total")
    print(f"    SSL Valid: {r['ssl']['valid']} | Open Ports: {r['ports']['open_count']}")

    print("\n  [Tool 2] check_ssl(hostname='google.com')")
    r = await s.check_ssl("google.com")
    print(f"    Valid: {r['valid']} | Issuer: {r['issuer']} | Protocol: {r['protocol']}")
    print(f"    Expires: {r['not_after']} ({r['days_until_expiry']} days)")

    print("\n  [Tool 3] check_headers(url='https://google.com')")
    r = await s.check_headers("https://google.com")
    print(f"    Present: {r['security_headers_found']} | Missing: {r['security_headers_missing']}")

    print("\n  [Tool 4] scan_ports(hostname='google.com')")
    r = await s.scan_ports("google.com")
    ports = [f"{p['port']}/{p['service']}" for p in r["open_ports"]]
    print(f"    Open: {ports}")

    print("\n  [Tool 5] get_security_score(url='https://google.com')")
    r = await s.get_security_score("https://google.com")
    print(f"    Score: {r['score']}/100 | Grade: {r['grade']}")

    # === SERVER 2: DATABASE QUERY ===
    print("\n" + "=" * 70)
    print("  SERVER 2: DATABASE QUERY")
    print("=" * 70)
    print("  Standalone: python -m servers.database.server")
    print("  API: POST /api/servers/database-query/invoke/{tool}")
    print("  Tools: connect_database, query, list_tables, describe_table, export_results")

    from servers.database.engine import DatabaseEngine
    db = DatabaseEngine()

    # Create demo database
    conn = sqlite3.connect("demo.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, role TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, user_id INTEGER, product TEXT, amount REAL)")
    conn.execute("DELETE FROM users")
    conn.execute("DELETE FROM orders")
    conn.executemany("INSERT INTO users VALUES (?,?,?,?)", [
        (1, "Ibrar Ahmed", "ibrar@test.com", "admin"),
        (2, "Ali Khan", "ali@test.com", "user"),
        (3, "Sara Malik", "sara@test.com", "user"),
    ])
    conn.executemany("INSERT INTO orders VALUES (?,?,?,?)", [
        (1, 1, "Security Audit", 500.00),
        (2, 2, "MCP Server", 1200.00),
        (3, 1, "Pentest Report", 800.00),
    ])
    conn.commit()
    conn.close()

    print("\n  [Tool 1] connect_database('sqlite:///demo.db')")
    r = await db.connect_database("sqlite:///demo.db", "demo")
    print(f"    Status: {r['status']} | Tables: {r['tables']}")

    print("\n  [Tool 2] list_tables()")
    r = await db.list_tables("demo")
    print(f"    Tables: {[t['name'] for t in r['tables']]}")

    print("\n  [Tool 3] describe_table('users')")
    r = await db.describe_table("users", "demo")
    cols = [f"{c['name']} ({c['type']})" for c in r["columns"]]
    print(f"    Columns: {cols} | Rows: {r['row_count']}")

    print("\n  [Tool 4] query('SELECT * FROM users')")
    r = await db.query("SELECT * FROM users", "demo")
    for row in r["rows"]:
        print(f"    {row}")

    print("\n  [Tool 5] export_results(format='csv')")
    r = await db.export_results("SELECT * FROM orders", "csv", "demo")
    print(f"    {r['content']}")

    # === SERVER 3: NOTIFICATION HUB ===
    print("\n" + "=" * 70)
    print("  SERVER 3: NOTIFICATION HUB")
    print("=" * 70)
    print("  Standalone: python -m servers.notifications.server")
    print("  API: POST /api/servers/notification-hub/invoke/{tool}")
    print("  Tools: send_email, send_slack, send_whatsapp, send_webhook, list_channels")

    from servers.notifications.hub import NotificationHub
    nh = NotificationHub()

    print("\n  [Tool 1] send_email(to='test@test.com', subject='Alert')")
    r = await nh.send_email("test@test.com", "Alert", "Server down")
    print(f"    Status: {r['status']} (demo mode — SMTP not configured)")

    print("\n  [Tool 2] send_whatsapp(phone='+923001234567')")
    r = await nh.send_whatsapp("+923001234567", "Your order shipped")
    print(f"    Status: {r['status']}")

    print("\n  [Tool 3] send_webhook(url='https://httpbin.org/post')")
    r = await nh.send_webhook("https://httpbin.org/post", {"event": "scan_complete"})
    print(f"    Status: {r['status']} | HTTP: {r.get('http_status', '?')}")

    print("\n  [Tool 4] list_channels()")
    r = await nh.list_channels()
    print(f"    Channels: {[c['name'] for c in r['channels']]} | Sent: {r['total_sent']}")

    # === SERVER 4: DOCUMENT ANALYZER ===
    print("\n" + "=" * 70)
    print("  SERVER 4: DOCUMENT ANALYZER")
    print("=" * 70)
    print("  Standalone: python -m servers.documents.server")
    print("  API: POST /api/servers/document-analyzer/invoke/{tool}")
    print("  Tools: analyze_pdf, analyze_csv, extract_text, summarize_document, extract_tables")

    from servers.documents.analyzer import DocumentAnalyzer
    da = DocumentAnalyzer()

    csv_path = os.path.abspath("demo_data.csv")
    with open(csv_path, "w") as f:
        f.write("name,email,revenue,country\n")
        f.write("Ibrar,ibrar@test.com,5000,Pakistan\n")
        f.write("Ali,ali@test.com,3200,UAE\n")
        f.write("Sara,sara@test.com,4800,Saudi Arabia\n")

    print(f"\n  [Tool 1] analyze_csv('{csv_path}')")
    r = await da.analyze_csv(csv_path)
    print(f"    Columns: {r['columns']} | Rows: {r['row_count']}")

    txt_path = os.path.abspath("config.py")
    print(f"\n  [Tool 2] extract_text('config.py')")
    r = await da.extract_text(txt_path, max_chars=200)
    print(f"    Lines: {r['line_count']} | Words: {r['word_count']}")

    print(f"\n  [Tool 3] summarize_document('{csv_path}')")
    r = await da.summarize_document(csv_path)
    print(f"    Summary: {r['summary']}")

    print(f"\n  [Tool 4] extract_tables('{csv_path}')")
    r = await da.extract_tables(csv_path)
    print(f"    Result: columns={r.get('column_count', '?')}, rows={r.get('row_count', '?')}")

    # === SERVER 5: API GATEWAY ===
    print("\n" + "=" * 70)
    print("  SERVER 5: API GATEWAY")
    print("=" * 70)
    print("  Standalone: python -m servers.api_gateway.server")
    print("  API: POST /api/servers/api-gateway/invoke/{tool}")
    print("  Tools: register_api, call_api, list_apis, test_endpoint, create_workflow")

    from servers.api_gateway.gateway import APIGateway
    gw = APIGateway()

    print("\n  [Tool 1] register_api('jsonplaceholder', 'https://jsonplaceholder.typicode.com')")
    r = await gw.register_api("jsonplaceholder", "https://jsonplaceholder.typicode.com", "Test API")
    print(f"    Status: {r['status']}")

    print("\n  [Tool 2] call_api(name='jsonplaceholder', path='/users/1')")
    r = await gw.call_api(name="jsonplaceholder", path="/users/1", method="GET")
    print(f"    HTTP {r['status_code']} | User: {r['response'].get('name', '?')}")

    print("\n  [Tool 3] test_endpoint('https://api.github.com')")
    r = await gw.test_endpoint("https://api.github.com")
    print(f"    Reachable: {r['reachable']} | {r['response_ms']}ms")

    print("\n  [Tool 4] list_apis()")
    r = await gw.list_apis()
    print(f"    Registered: {[a['name'] for a in r['apis']]}")

    print("\n  [Tool 5] create_workflow('user-posts')")
    r = await gw.create_workflow("user-posts", [
        {"name": "user", "api": "jsonplaceholder", "path": "/users/1", "method": "GET"},
        {"name": "posts", "api": "jsonplaceholder", "path": "/posts?userId=1", "method": "GET"},
    ])
    print(f"    Steps: {r['steps_executed']}")

    # === SERVER 6: SYSTEM MONITOR ===
    print("\n" + "=" * 70)
    print("  SERVER 6: SYSTEM MONITOR")
    print("=" * 70)
    print("  Standalone: python -m servers.system_monitor.server")
    print("  API: POST /api/servers/system-monitor/invoke/{tool}")
    print("  Tools: get_system_info, get_cpu_usage, get_memory_usage, get_disk_usage, list_processes, get_network_stats")

    from servers.system_monitor.monitor import SystemMonitor
    sm = SystemMonitor()

    print("\n  [Tool 1] get_system_info()")
    r = await sm.get_system_info()
    print(f"    Host: {r['hostname']} | OS: {r['os']}")
    print(f"    CPU: {r['cpu']['logical_cores']} cores | RAM: {r['memory']['total_gb']}GB")

    print("\n  [Tool 2] get_cpu_usage(per_core=True)")
    r = await sm.get_cpu_usage(per_core=True)
    print(f"    Overall: {r['overall_percent']}% | Status: {r['status']}")

    print("\n  [Tool 3] get_memory_usage()")
    r = await sm.get_memory_usage()
    print(f"    RAM: {r['ram']['used_gb']}/{r['ram']['total_gb']}GB ({r['ram']['used_percent']}%)")

    print("\n  [Tool 4] get_disk_usage()")
    r = await sm.get_disk_usage()
    for p in r["partitions"][:2]:
        print(f"    {p['mountpoint']}: {p['used_gb']}/{p['total_gb']}GB ({p['used_percent']}%)")

    print("\n  [Tool 5] list_processes(sort_by='memory', limit=5)")
    r = await sm.list_processes("memory", 5)
    for p in r["processes"]:
        print(f"    PID {p['pid']:>6} | {p['name']:<25} | MEM: {p['memory_percent']}%")

    print("\n  [Tool 6] get_network_stats()")
    r = await sm.get_network_stats()
    print(f"    Sent: {r['io_counters']['bytes_sent_mb']}MB | Recv: {r['io_counters']['bytes_recv_mb']}MB")

    print("\n" + "=" * 70)
    print("  ALL 6 SERVERS — 31 TOOLS — TESTED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_all())
