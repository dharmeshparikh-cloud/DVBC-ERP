"""
Generate Site Tree Excel with page-wise interconnectivity graph.
Scans all React routes and page files to map which pages link to which.
Emails the result to dharmesh.parikh@dvconsulting.co.in
"""

import re
import os
import glob
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

PAGES_DIR = "/app/frontend/src/pages"
APP_JS = "/app/frontend/src/App.js"
LAYOUT_JS = "/app/frontend/src/components/Layout.js"
OUTPUT_PATH = "/tmp/DVBC_Site_Tree.xlsx"

# ── 1. Extract all routes from App.js ──
def extract_routes():
    with open(APP_JS, "r") as f:
        content = f.read()

    routes = []
    # Match <Route path="..." element={...} />
    route_pattern = re.compile(
        r'<Route\s+path=["\']([^"\']+)["\']\s+element=\{([^}]+)\}',
        re.DOTALL
    )
    for match in route_pattern.finditer(content):
        path = match.group(1)
        element_raw = match.group(2).strip()

        # Determine component name
        comp_match = re.search(r'<(\w+)', element_raw)
        component = comp_match.group(1) if comp_match else element_raw

        # Check if Navigate (redirect)
        is_redirect = "Navigate" in element_raw

        # Check for RoleGuard
        has_guard = "RoleGuard" in element_raw
        roles = []
        depts = []
        if has_guard:
            roles_match = re.search(r"allowedRoles=\{\[([^\]]*)\]", element_raw)
            depts_match = re.search(r"allowedDepts=\{\[([^\]]*)\]", element_raw)
            if roles_match:
                roles = [r.strip().strip("'\"") for r in roles_match.group(1).split(",") if r.strip()]
            if depts_match:
                depts = [d.strip().strip("'\"") for d in depts_match.group(1).split(",") if d.strip()]

        routes.append({
            "path": "/" + path.lstrip("/") if path != "/" else "/",
            "component": component,
            "is_redirect": is_redirect,
            "has_guard": has_guard,
            "allowed_roles": roles,
            "allowed_depts": depts,
        })

    return routes

# ── 2. Extract sidebar sections from Layout.js ──
def extract_sidebar_sections():
    with open(LAYOUT_JS, "r") as f:
        content = f.read()

    sections = {}
    # Find href patterns with their names
    item_pattern = re.compile(r"\{\s*name:\s*['\"]([^'\"]+)['\"],\s*href:\s*['\"]([^'\"]+)['\"]")
    
    # Determine which section each item belongs to
    # We'll do a simple scan: find section markers and associate items
    lines = content.split("\n")
    current_section = "Unknown"
    for line in lines:
        if "guidedSalesItems" in line or "fullSalesFlowItems" in line:
            current_section = "Sales"
        elif "consultingItems" in line:
            current_section = "Consulting"
        elif "adminItems" in line:
            current_section = "Admin"
        elif "workspaceItems" in line:
            current_section = "Workspace (Self-Service)"
        elif "hrItems" in line or "hrCoreItems" in line:
            current_section = "HR"

        match = item_pattern.search(line)
        if match:
            name, href = match.group(1), match.group(2)
            if href not in sections:
                sections[href] = {"name": name, "section": current_section}
            elif current_section != "Unknown":
                # Prefer non-Unknown section
                sections[href] = {"name": name, "section": current_section}

    return sections

# ── 3. Scan page files for cross-page navigation links ──
def scan_page_links():
    """Scan all page .js files for navigate(), Link to=, and href patterns pointing to other pages."""
    page_links = {}  # component_file -> [linked_paths]
    
    all_files = glob.glob(os.path.join(PAGES_DIR, "**/*.js"), recursive=True)
    
    nav_patterns = [
        re.compile(r'navigate\s*\(\s*[`"\']([^`"\']+)[`"\']'),        # navigate('/path')
        re.compile(r'navigate\s*\(\s*`([^`]+)`'),                      # navigate(`/path`)
        re.compile(r'<Link\s+to=["\']([^"\']+)["\']'),                 # <Link to="/path"
        re.compile(r'<Link\s+to=\{[`"\']([^`"\']+)[`"\']\}'),         # <Link to={"/path"}
        re.compile(r'href=["\']([^"\']+)["\']'),                        # href="/path"
        re.compile(r'window\.location\.href\s*=\s*[`"\']([^`"\']+)'),  # window.location.href
        re.compile(r'history\.push\s*\(\s*[`"\']([^`"\']+)'),          # history.push('/path')
    ]
    
    for filepath in all_files:
        rel_path = os.path.relpath(filepath, PAGES_DIR)
        try:
            with open(filepath, "r") as f:
                content = f.read()
        except Exception:
            continue
        
        links = set()
        for pattern in nav_patterns:
            for match in pattern.finditer(content):
                target = match.group(1)
                # Only internal routes (starts with /)
                if target.startswith("/") and not target.startswith("//"):
                    # Clean template literals: /path/${id} -> /path/:id
                    clean = re.sub(r'\$\{[^}]+\}', ':param', target)
                    # Remove query strings for grouping
                    clean_base = clean.split("?")[0]
                    links.add(clean_base)
        
        if links:
            page_links[rel_path] = sorted(links)
    
    return page_links

# ── 4. Map component to file ──
def map_component_to_file():
    """Map component names to their file paths."""
    comp_map = {}
    all_files = glob.glob(os.path.join(PAGES_DIR, "**/*.js"), recursive=True)
    
    for filepath in all_files:
        rel_path = os.path.relpath(filepath, PAGES_DIR)
        basename = os.path.splitext(os.path.basename(filepath))[0]
        comp_map[basename] = rel_path
    
    return comp_map

# ── 5. Generate Excel ──
def generate_excel(routes, sidebar, page_links, comp_file_map):
    wb = Workbook()
    
    # Colors
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    redirect_fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
    unguarded_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    guarded_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    public_fill = PatternFill(start_color="FFFFCC", end_color="FFFFCC", fill_type="solid")
    section_fills = {
        "Sales": PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid"),
        "Consulting": PatternFill(start_color="D6DCE4", end_color="D6DCE4", fill_type="solid"),
        "HR": PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid"),
        "Admin": PatternFill(start_color="EDEDED", end_color="EDEDED", fill_type="solid"),
        "Workspace (Self-Service)": PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid"),
    }
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    # ── Sheet 1: All Routes ──
    ws1 = wb.active
    ws1.title = "All Routes"
    headers1 = ["#", "Route Path", "Component", "Type", "RoleGuard?", "Allowed Roles", "Allowed Depts", "Sidebar Section", "Security Status"]
    for col, h in enumerate(headers1, 1):
        cell = ws1.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
        cell.border = thin_border
    
    # Public routes that don't need guards
    public_paths = {"/login", "/client-login", "/client-portal", "/client-portal/change-password",
                    "/client-approval/:token", "/accept-offer/:token", "/onboarding/candidate/:token",
                    "/consent/:token", "/meeting-response", "/mobile", "/sales/login", "/hr/login"}
    redirect_paths = set()
    
    row = 2
    for i, r in enumerate(routes, 1):
        section = sidebar.get(r["path"], {}).get("section", "—")
        
        if r["is_redirect"]:
            rtype = "Redirect"
            security = "Redirect"
            redirect_paths.add(r["path"])
        elif r["path"] in public_paths:
            rtype = "Public"
            security = "Public (OK)"
        elif r["has_guard"]:
            rtype = "Protected"
            security = "GUARDED"
        else:
            rtype = "Unprotected"
            security = "UNGUARDED"
        
        values = [
            i,
            r["path"],
            r["component"],
            rtype,
            "Yes" if r["has_guard"] else ("N/A" if r["is_redirect"] or r["path"] in public_paths else "NO"),
            ", ".join(r["allowed_roles"]) if r["allowed_roles"] else "—",
            ", ".join(r["allowed_depts"]) if r["allowed_depts"] else "—",
            section,
            security,
        ]
        for col, val in enumerate(values, 1):
            cell = ws1.cell(row=row, column=col, value=val)
            cell.border = thin_border
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if r["is_redirect"]:
                cell.fill = redirect_fill
            elif r["path"] in public_paths:
                cell.fill = public_fill
            elif not r["has_guard"] and not r["is_redirect"]:
                cell.fill = unguarded_fill
            elif r["has_guard"]:
                cell.fill = guarded_fill
            if section in section_fills and col == 8:
                cell.fill = section_fills[section]
        row += 1
    
    # Auto-width
    for col in range(1, len(headers1) + 1):
        max_len = max(len(str(ws1.cell(row=r, column=col).value or "")) for r in range(1, row))
        ws1.column_dimensions[get_column_letter(col)].width = min(max_len + 4, 40)
    
    # Freeze header
    ws1.freeze_panes = "A2"
    
    # ── Sheet 2: Page Interconnectivity ──
    ws2 = wb.create_sheet("Page Connections")
    headers2 = ["#", "Source Page (File)", "Source Route", "Links To (Routes)", "# Outgoing Links"]
    for col, h in enumerate(headers2, 1):
        cell = ws2.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
        cell.border = thin_border
    
    # Build reverse map: file -> route
    file_to_route = {}
    for r in routes:
        if not r["is_redirect"]:
            fname = comp_file_map.get(r["component"])
            if fname:
                file_to_route[fname] = r["path"]
    
    row = 2
    for i, (page_file, targets) in enumerate(sorted(page_links.items()), 1):
        source_route = file_to_route.get(page_file, "—")
        targets_str = "\n".join(targets)
        values = [i, page_file, source_route, targets_str, len(targets)]
        for col, val in enumerate(values, 1):
            cell = ws2.cell(row=row, column=col, value=val)
            cell.border = thin_border
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        row += 1
    
    for col in range(1, len(headers2) + 1):
        max_len = max((len(str(ws2.cell(row=r, column=col).value or "").split("\n")[0]) for r in range(1, row)), default=10)
        ws2.column_dimensions[get_column_letter(col)].width = min(max_len + 4, 50)
    ws2.freeze_panes = "A2"
    
    # ── Sheet 3: Security Summary ──
    ws3 = wb.create_sheet("Security Summary")
    headers3 = ["Category", "Count", "Details"]
    for col, h in enumerate(headers3, 1):
        cell = ws3.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin_border
    
    total = len(routes)
    guarded = sum(1 for r in routes if r["has_guard"])
    unguarded = sum(1 for r in routes if not r["has_guard"] and not r["is_redirect"] and r["path"] not in public_paths)
    redirects = sum(1 for r in routes if r["is_redirect"])
    public = sum(1 for r in routes if r["path"] in public_paths)
    
    summary_data = [
        ("Total Routes", total, "All routes in App.js"),
        ("RoleGuard Protected", guarded, "Routes with <RoleGuard> wrapper"),
        ("UNGUARDED (Action Needed)", unguarded, "Routes accessible to any logged-in user"),
        ("Redirects", redirects, "Routes that redirect to other pages"),
        ("Public (No Auth)", public, "Login, onboarding, client portal"),
        ("", "", ""),
        ("Unguarded Route List:", "", ""),
    ]
    
    row = 2
    for cat, count, detail in summary_data:
        ws3.cell(row=row, column=1, value=cat).border = thin_border
        ws3.cell(row=row, column=2, value=count).border = thin_border
        ws3.cell(row=row, column=3, value=detail).border = thin_border
        if cat == "UNGUARDED (Action Needed)":
            for c in range(1, 4):
                ws3.cell(row=row, column=c).fill = unguarded_fill
                ws3.cell(row=row, column=c).font = Font(bold=True, color="FF0000")
        row += 1
    
    # List unguarded routes
    for r in routes:
        if not r["has_guard"] and not r["is_redirect"] and r["path"] not in public_paths:
            ws3.cell(row=row, column=1, value=r["path"]).border = thin_border
            ws3.cell(row=row, column=2, value=r["component"]).border = thin_border
            section = sidebar.get(r["path"], {}).get("section", "—")
            ws3.cell(row=row, column=3, value=f"Section: {section}").border = thin_border
            for c in range(1, 4):
                ws3.cell(row=row, column=c).fill = unguarded_fill
            row += 1
    
    for col in range(1, 4):
        ws3.column_dimensions[get_column_letter(col)].width = 40
    ws3.freeze_panes = "A2"
    
    # ── Sheet 4: Sidebar Navigation Map ──
    ws4 = wb.create_sheet("Sidebar Map")
    headers4 = ["#", "Section", "Menu Item Name", "Route Path", "Has Matching Route?"]
    for col, h in enumerate(headers4, 1):
        cell = ws4.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin_border
    
    route_paths = {r["path"] for r in routes}
    row = 2
    for i, (href, info) in enumerate(sorted(sidebar.items(), key=lambda x: x[1]["section"]), 1):
        has_route = href in route_paths or any(href.rstrip("/") == rp.rstrip("/") for rp in route_paths)
        values = [i, info["section"], info["name"], href, "Yes" if has_route else "NO — ORPHAN"]
        for col, val in enumerate(values, 1):
            cell = ws4.cell(row=row, column=col, value=val)
            cell.border = thin_border
            if not has_route:
                cell.fill = unguarded_fill
            elif info["section"] in section_fills:
                cell.fill = section_fills[info["section"]]
        row += 1
    
    for col in range(1, len(headers4) + 1):
        ws4.column_dimensions[get_column_letter(col)].width = 30
    ws4.freeze_panes = "A2"
    
    wb.save(OUTPUT_PATH)
    print(f"Excel saved to {OUTPUT_PATH}")
    return OUTPUT_PATH

# ── 6. Email ──
def send_email(filepath):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication
    
    smtp_user = os.environ.get("SMTP_USER", "dharmesh.parikh@dvconsulting.co.in")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    to_email = "dharmesh.parikh@dvconsulting.co.in"
    
    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = "DVBC ERP - Site Tree & Page Interconnectivity Map"
    
    body = """
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #1F4E79;">DVBC ERP - Complete Site Tree</h2>
        <p>Please find attached the comprehensive Site Tree Excel with 4 sheets:</p>
        <ol>
            <li><strong>All Routes</strong> — Every page in the ERP with route path, component, RoleGuard status, allowed roles/departments, and sidebar section</li>
            <li><strong>Page Connections</strong> — Interconnectivity graph showing which pages link to which other pages (navigate, Link, href)</li>
            <li><strong>Security Summary</strong> — Overview of guarded vs unguarded routes with full list of unprotected pages</li>
            <li><strong>Sidebar Map</strong> — All sidebar menu items mapped to their routes, with orphan detection</li>
        </ol>
        <p><strong>Color Legend:</strong></p>
        <ul>
            <li style="background:#C6EFCE;padding:3px;">Green = RoleGuard Protected</li>
            <li style="background:#FFC7CE;padding:3px;">Red = UNGUARDED (Needs Action)</li>
            <li style="background:#D9E2F3;padding:3px;">Blue = Redirect</li>
            <li style="background:#FFFFCC;padding:3px;">Yellow = Public (No Auth Required)</li>
        </ul>
        <p>Best regards,<br>DVBC ERP System</p>
    </body>
    </html>
    """
    msg.attach(MIMEText(body, "html"))
    
    with open(filepath, "rb") as f:
        attachment = MIMEApplication(f.read(), _subtype="xlsx")
        attachment.add_header("Content-Disposition", "attachment", filename="DVBC_Site_Tree.xlsx")
        msg.attach(attachment)
    
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())
    
    print(f"Email sent to {to_email}")

# ── Main ──
if __name__ == "__main__":
    print("Extracting routes from App.js...")
    routes = extract_routes()
    print(f"  Found {len(routes)} routes")
    
    print("Extracting sidebar sections from Layout.js...")
    sidebar = extract_sidebar_sections()
    print(f"  Found {len(sidebar)} sidebar items")
    
    print("Scanning page files for cross-page links...")
    page_links = scan_page_links()
    print(f"  Found links in {len(page_links)} pages")
    
    print("Mapping components to files...")
    comp_file_map = map_component_to_file()
    print(f"  Mapped {len(comp_file_map)} components")
    
    print("Generating Excel...")
    filepath = generate_excel(routes, sidebar, page_links, comp_file_map)
    
    print("Sending email...")
    send_email(filepath)
    
    print("Done!")
