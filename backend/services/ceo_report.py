"""
CEO Control Tower — Daily Business Intelligence Report
=========================================================
13-section comprehensive daily email covering:
Sales, Pipeline, Escalations, Meetings, Consulting, SOW/Agreements,
Payment/Finance, Revenue (MTD/QTD/YTD), Team Productivity, System Health,
HR Metrics, Consulting Team Performance, Finance & Expenses.

Scheduled at 23:59 IST (Asia/Kolkata) daily.
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
import pytz

logger = logging.getLogger(__name__)

IST = pytz.timezone('Asia/Kolkata')


class CEOReportGenerator:
    """Generates and sends the daily CEO intelligence report."""

    def __init__(self, db):
        self.db = db
        self.recipient = "dharmesh.parikh@dvconsulting.co.in"

    def _today_ist(self):
        return datetime.now(IST)

    def _today_range_utc(self):
        """Get UTC start/end for today IST."""
        now_ist = self._today_ist()
        start_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
        end_ist = start_ist + timedelta(days=1)
        return self._to_utc(start_ist), self._to_utc(end_ist)

    def _to_utc(self, dt_ist):
        return dt_ist.astimezone(pytz.utc).replace(tzinfo=None)

    def _period_ranges_utc(self):
        """Return (mtd_start, qtd_start, ytd_start, now) in UTC naive."""
        now_ist = self._today_ist()
        mtd = now_ist.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        q_month = ((now_ist.month - 1) // 3) * 3 + 1
        qtd = now_ist.replace(month=q_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        ytd = now_ist.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        now_utc = self._to_utc(now_ist)
        return self._to_utc(mtd), self._to_utc(qtd), self._to_utc(ytd), now_utc

    async def _count_today(self, collection, date_field="created_at"):
        start, end = self._today_range_utc()
        return await self.db[collection].count_documents({
            date_field: {"$gte": start, "$lt": end}
        })

    async def _count_period(self, collection, date_field, start_utc, end_utc, extra_filter=None):
        q = {date_field: {"$gte": start_utc, "$lt": end_utc}}
        if extra_filter:
            q.update(extra_filter)
        return await self.db[collection].count_documents(q)

    async def _sum_period(self, collection, amount_field, date_field, start_utc, end_utc, extra_filter=None):
        q = {date_field: {"$gte": start_utc, "$lt": end_utc}}
        if extra_filter:
            q.update(extra_filter)
        docs = await self.db[collection].find(q, {"_id": 0, amount_field: 1}).to_list(10000)
        return sum(d.get(amount_field, 0) or 0 for d in docs)

    # ======================== GENERATE REPORT ========================

    async def generate_report(self) -> Dict[str, Any]:
        """Generate all 13 sections of the report."""
        report = {}
        today_ist = self._today_ist()
        report["date"] = today_ist.strftime("%d %b %Y")
        report["generated_at"] = today_ist.isoformat()

        report["sales_activity"] = await self._section_sales_activity()
        report["pipeline_health"] = await self._section_pipeline_health()
        report["escalations"] = await self._section_escalations()
        report["meetings"] = await self._section_meetings()
        report["consulting"] = await self._section_consulting()
        report["sow_agreements"] = await self._section_sow_agreements()
        report["payments"] = await self._section_payments()
        report["revenue"] = await self._section_revenue()
        report["team_productivity"] = await self._section_team_productivity()
        report["system_health"] = await self._section_system_health()
        report["hr_metrics"] = await self._section_hr_metrics()
        report["consulting_team"] = await self._section_consulting_team()
        report["finance_expenses"] = await self._section_finance_expenses()

        return report

    # ======================== EXISTING SECTIONS ========================

    async def _section_sales_activity(self):
        start, end = self._today_range_utc()
        mtd_s, qtd_s, ytd_s, now_utc = self._period_ranges_utc()
        new_leads = await self._count_today("leads")
        meetings = await self._count_today("meetings")
        followups_done = await self.db.follow_ups.count_documents({
            "status": "closed",
            "closed_at": {"$gte": start.isoformat(), "$lt": end.isoformat()}
        })
        followups_missed = await self.db.follow_ups.count_documents({
            "status": "open", "due_date": {"$lt": datetime.utcnow()}
        })
        proposals = await self._count_today("quotations")
        sows = await self._count_today("sows")
        closed_won = await self.db.leads.count_documents({
            "status": "closed_won", "updated_at": {"$gte": start, "$lt": end}
        })
        closed_lost = await self.db.leads.count_documents({
            "status": "closed_lost", "updated_at": {"$gte": start, "$lt": end}
        })
        # MTD/QTD/YTD leads
        mtd_leads = await self._count_period("leads", "created_at", mtd_s, now_utc)
        qtd_leads = await self._count_period("leads", "created_at", qtd_s, now_utc)
        ytd_leads = await self._count_period("leads", "created_at", ytd_s, now_utc)

        return {
            "new_leads": new_leads, "meetings": meetings,
            "followups_done": followups_done, "followups_missed": followups_missed,
            "proposals_sent": proposals, "sow_generated": sows,
            "closed_won": closed_won, "closed_lost": closed_lost,
            "leads_reassigned": 0,
            "mtd_leads": mtd_leads, "qtd_leads": qtd_leads, "ytd_leads": ytd_leads,
        }

    async def _section_pipeline_health(self):
        pipeline = []
        stages = [
            ("new", "New Lead"), ("contacted", "Contacted"),
            ("meeting_scheduled", "Meeting Scheduled"), ("meeting", "Meeting Scheduled"),
            ("proposal_sent", "Proposal Sent"),
            ("negotiation", "Negotiation"), ("sow_shared", "SOW Shared"),
            ("closed_won", "Closed Won"), ("closed_lost", "Closed Lost")
        ]
        total_leads = 0
        for status, label in stages:
            count = await self.db.leads.count_documents({"status": status})
            pipeline.append({"stage": label, "count": count})
            total_leads += count
        closed_won = await self.db.leads.count_documents({"status": "closed_won"})
        conversion_rate = round((closed_won / total_leads * 100), 1) if total_leads > 0 else 0
        return {"stages": pipeline, "total_leads": total_leads, "conversion_rate": conversion_rate}

    async def _section_escalations(self):
        cutoff = datetime.utcnow() - timedelta(days=2)
        escalated = await self.db.follow_ups.find(
            {"status": "open", "due_date": {"$lt": cutoff}},
            {"_id": 0, "client_name": 1, "entity_type": 1, "assigned_to_name": 1, "due_date": 1}
        ).sort("due_date", 1).to_list(50)
        for e in escalated:
            due = e.get("due_date")
            if isinstance(due, datetime):
                e["days_overdue"] = max(0, (datetime.utcnow() - due).days)
                e["due_date"] = due.isoformat()
            else:
                e["days_overdue"] = 0
        return {"items": escalated, "count": len(escalated)}

    async def _section_meetings(self):
        start, end = self._today_range_utc()
        meetings = await self.db.meetings.find(
            {"created_at": {"$gte": start, "$lt": end}},
            {"_id": 0, "title": 1, "client_name": 1, "meeting_type": 1, "created_by_name": 1}
        ).to_list(50)
        mtd_s, _, _, now = self._period_ranges_utc()
        mtd_meetings = await self._count_period("meetings", "created_at", mtd_s, now)
        return {"items": meetings, "count": len(meetings), "mtd_count": mtd_meetings}

    async def _section_consulting(self):
        active = await self.db.projects.count_documents({"status": {"$in": ["active", "in_progress"]}})
        at_risk = await self.db.projects.count_documents({"status": "at_risk"})
        completed = await self.db.projects.count_documents({"status": "completed"})
        projects = await self.db.projects.find(
            {"status": {"$in": ["active", "in_progress", "at_risk"]}},
            {"_id": 0, "name": 1, "client_name": 1, "status": 1, "assigned_to_name": 1}
        ).to_list(50)
        return {"active": active, "at_risk": at_risk, "completed": completed, "projects": projects}

    async def _section_sow_agreements(self):
        pending_sows = await self.db.sows.count_documents({"status": {"$nin": ["completed", "signed"]}})
        pending_agr = await self.db.agreements.count_documents({"status": {"$nin": ["signed", "completed"]}})
        return {"pending_sows": pending_sows, "pending_agreements": pending_agr}

    async def _section_payments(self):
        outstanding = await self.db.consulting_payments.count_documents({"status": {"$ne": "paid"}})
        start, end = self._today_range_utc()
        received_today = await self.db.consulting_payments.count_documents({
            "status": "paid", "paid_date": {"$gte": start, "$lt": end}
        })
        overdue_15 = await self.db.consulting_payments.count_documents({
            "status": {"$ne": "paid"}, "due_date": {"$lt": datetime.utcnow() - timedelta(days=15)}
        })
        return {"outstanding": outstanding, "received_today": received_today, "overdue_15_days": overdue_15}

    async def _section_revenue(self):
        start, end = self._today_range_utc()
        mtd_s, qtd_s, ytd_s, now_utc = self._period_ranges_utc()

        today_rev = await self._sum_period("consulting_payments", "amount", "paid_date", start, end, {"status": "paid"})
        mtd_rev = await self._sum_period("consulting_payments", "amount", "paid_date", mtd_s, now_utc, {"status": "paid"})
        qtd_rev = await self._sum_period("consulting_payments", "amount", "paid_date", qtd_s, now_utc, {"status": "paid"})
        ytd_rev = await self._sum_period("consulting_payments", "amount", "paid_date", ytd_s, now_utc, {"status": "paid"})

        return {
            "today_revenue": today_rev, "mtd_revenue": mtd_rev,
            "qtd_revenue": qtd_rev, "ytd_revenue": ytd_rev,
        }

    async def _section_team_productivity(self):
        start, end = self._today_range_utc()
        users = await self.db.users.find(
            {"is_active": True}, {"_id": 0, "id": 1, "full_name": 1, "role": 1}
        ).to_list(200)
        productivity = []
        for u in users:
            uid = u["id"]
            meetings = await self.db.meetings.count_documents({
                "created_by": uid, "created_at": {"$gte": start, "$lt": end}
            })
            followups = await self.db.follow_ups.count_documents({
                "assigned_to": uid, "status": "closed",
                "closed_at": {"$gte": start.isoformat(), "$lt": end.isoformat()}
            })
            score = meetings * 2 + followups
            if score > 0:
                productivity.append({
                    "name": u["full_name"], "role": u.get("role", ""),
                    "meetings": meetings, "followups_done": followups, "score": score
                })
        productivity.sort(key=lambda x: x["score"], reverse=True)
        return {"team": productivity[:10]}

    async def _section_system_health(self):
        active_users = await self.db.users.count_documents({"is_active": True})
        start, end = self._today_range_utc()
        meetings_today = await self.db.meetings.count_documents({"created_at": {"$gte": start, "$lt": end}})
        tomorrow_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        tomorrow_end = tomorrow_start + timedelta(days=1)
        followups_tomorrow = await self.db.follow_ups.count_documents({
            "status": "open", "due_date": {"$gte": tomorrow_start, "$lt": tomorrow_end}
        })
        active_leads = await self.db.leads.count_documents({"status": {"$nin": ["closed_won", "closed_lost"]}})
        leads_with_followup = len(await self.db.follow_ups.distinct("entity_id", {"entity_type": "lead", "status": "open"}))
        leads_no_followup = max(0, active_leads - leads_with_followup)
        return {
            "active_users": active_users, "meetings_logged_today": meetings_today,
            "followups_tomorrow": followups_tomorrow,
            "anomalies": {"leads_without_followups": leads_no_followup}
        }

    # ======================== NEW SECTIONS ========================

    async def _section_hr_metrics(self):
        """Section 11: HR Metrics — Attendance, Leaves, Headcount, Onboarding."""
        start, end = self._today_range_utc()
        mtd_s, qtd_s, ytd_s, now_utc = self._period_ranges_utc()

        total_employees = await self.db.employees.count_documents({"status": {"$ne": "inactive"}})
        active_users = await self.db.users.count_documents({"is_active": True})

        # Attendance today
        att_present = await self.db.attendance.count_documents({"date": {"$gte": start, "$lt": end}, "status": "present"})
        att_absent = await self.db.attendance.count_documents({"date": {"$gte": start, "$lt": end}, "status": "absent"})
        att_wfh = await self.db.attendance.count_documents({"date": {"$gte": start, "$lt": end}, "status": {"$in": ["wfh", "work_from_home"]}})
        att_leave = await self.db.attendance.count_documents({"date": {"$gte": start, "$lt": end}, "status": "leave"})

        # Leave requests
        leaves_pending = await self.db.leave_requests.count_documents({"status": "pending"})
        leaves_approved_mtd = await self._count_period("leave_requests", "created_at", mtd_s, now_utc, {"status": "approved"})
        leaves_approved_qtd = await self._count_period("leave_requests", "created_at", qtd_s, now_utc, {"status": "approved"})
        leaves_approved_ytd = await self._count_period("leave_requests", "created_at", ytd_s, now_utc, {"status": "approved"})

        # New joiners
        new_joiners_mtd = await self._count_period("employees", "created_at", mtd_s, now_utc)
        new_joiners_qtd = await self._count_period("employees", "created_at", qtd_s, now_utc)
        new_joiners_ytd = await self._count_period("employees", "created_at", ytd_s, now_utc)

        # Onboarding pipeline
        onboarding_pending = await self.db.onboarding_submissions.count_documents({"status": {"$in": ["submitted", "draft", "invited"]}})

        return {
            "total_employees": total_employees, "active_users": active_users,
            "attendance_today": {"present": att_present, "absent": att_absent, "wfh": att_wfh, "leave": att_leave},
            "leaves_pending": leaves_pending,
            "leaves_approved": {"mtd": leaves_approved_mtd, "qtd": leaves_approved_qtd, "ytd": leaves_approved_ytd},
            "new_joiners": {"mtd": new_joiners_mtd, "qtd": new_joiners_qtd, "ytd": new_joiners_ytd},
            "onboarding_pending": onboarding_pending,
        }

    async def _section_consulting_team(self):
        """Section 12: Consulting Team Performance — Tasks, Utilization, Projects (MTD/QTD/YTD)."""
        mtd_s, qtd_s, ytd_s, now_utc = self._period_ranges_utc()

        total_consultants = await self.db.consultants.count_documents({"status": {"$ne": "inactive"}})

        # Tasks
        tasks_total = await self.db.tasks.count_documents({})
        tasks_completed = await self.db.tasks.count_documents({"status": "completed"})
        tasks_in_progress = await self.db.tasks.count_documents({"status": {"$in": ["in_progress", "active"]}})
        tasks_overdue = await self.db.tasks.count_documents({
            "status": {"$ne": "completed"}, "due_date": {"$lt": datetime.utcnow()}
        })

        # Tasks completed MTD/QTD/YTD
        tasks_done_mtd = await self._count_period("tasks", "completed_at", mtd_s, now_utc, {"status": "completed"})
        tasks_done_qtd = await self._count_period("tasks", "completed_at", qtd_s, now_utc, {"status": "completed"})
        tasks_done_ytd = await self._count_period("tasks", "completed_at", ytd_s, now_utc, {"status": "completed"})

        # Projects completed MTD/QTD/YTD
        proj_done_mtd = await self._count_period("projects", "completed_at", mtd_s, now_utc, {"status": "completed"})
        proj_done_qtd = await self._count_period("projects", "completed_at", qtd_s, now_utc, {"status": "completed"})
        proj_done_ytd = await self._count_period("projects", "completed_at", ytd_s, now_utc, {"status": "completed"})

        # Timesheet hours MTD
        ts_docs = await self.db.timesheets.find(
            {"week_start": {"$gte": mtd_s.isoformat()}, "status": {"$in": ["submitted", "approved"]}},
            {"_id": 0, "total_hours": 1}
        ).to_list(500)
        mtd_hours = sum(t.get("total_hours", 0) or 0 for t in ts_docs)

        return {
            "total_consultants": total_consultants,
            "tasks": {"total": tasks_total, "completed": tasks_completed, "in_progress": tasks_in_progress, "overdue": tasks_overdue},
            "tasks_completed": {"mtd": tasks_done_mtd, "qtd": tasks_done_qtd, "ytd": tasks_done_ytd},
            "projects_completed": {"mtd": proj_done_mtd, "qtd": proj_done_qtd, "ytd": proj_done_ytd},
            "mtd_logged_hours": mtd_hours,
        }

    async def _section_finance_expenses(self):
        """Section 13: Finance & Expenses — Claims, Travel, Approvals (MTD/QTD/YTD)."""
        start, end = self._today_range_utc()
        mtd_s, qtd_s, ytd_s, now_utc = self._period_ranges_utc()

        # Expense claims
        exp_pending = await self.db.expenses.count_documents({"status": "pending"})
        exp_approved_mtd = await self._count_period("expenses", "created_at", mtd_s, now_utc, {"status": "approved"})
        exp_approved_qtd = await self._count_period("expenses", "created_at", qtd_s, now_utc, {"status": "approved"})
        exp_approved_ytd = await self._count_period("expenses", "created_at", ytd_s, now_utc, {"status": "approved"})

        # Expense amounts
        exp_amt_mtd = await self._sum_period("expenses", "total_amount", "created_at", mtd_s, now_utc, {"status": "approved"})
        exp_amt_qtd = await self._sum_period("expenses", "total_amount", "created_at", qtd_s, now_utc, {"status": "approved"})
        exp_amt_ytd = await self._sum_period("expenses", "total_amount", "created_at", ytd_s, now_utc, {"status": "approved"})

        # Travel reimbursements
        travel_pending = await self.db.travel_reimbursements.count_documents({"status": "pending"})
        travel_amt_mtd = await self._sum_period("travel_reimbursements", "amount", "created_at", mtd_s, now_utc, {"status": "approved"})
        travel_amt_qtd = await self._sum_period("travel_reimbursements", "amount", "created_at", qtd_s, now_utc, {"status": "approved"})
        travel_amt_ytd = await self._sum_period("travel_reimbursements", "amount", "created_at", ytd_s, now_utc, {"status": "approved"})

        # Payroll (latest run)
        latest_payroll = await self.db.payroll_runs.find_one({}, {"_id": 0, "month": 1, "status": 1, "total_net_pay": 1}, sort=[("created_at", -1)])

        return {
            "expenses_pending": exp_pending,
            "expenses_approved": {"mtd": exp_approved_mtd, "qtd": exp_approved_qtd, "ytd": exp_approved_ytd},
            "expense_amount": {"mtd": exp_amt_mtd, "qtd": exp_amt_qtd, "ytd": exp_amt_ytd},
            "travel_pending": travel_pending,
            "travel_amount": {"mtd": travel_amt_mtd, "qtd": travel_amt_qtd, "ytd": travel_amt_ytd},
            "latest_payroll": latest_payroll,
        }

    # ======================== HTML RENDERER ========================

    def _render_html(self, report: Dict) -> str:
        sa = report["sales_activity"]
        ph = report["pipeline_health"]
        esc = report["escalations"]
        mtg = report["meetings"]
        con = report["consulting"]
        sow = report["sow_agreements"]
        pay = report["payments"]
        rev = report["revenue"]
        tp = report["team_productivity"]
        sh = report["system_health"]
        hr = report.get("hr_metrics", {})
        ct = report.get("consulting_team", {})
        fe = report.get("finance_expenses", {})
        date = report["date"]

        def kpi(label, value, color="#1a1a2e"):
            return f'<td style="padding:12px 16px;text-align:center;border:1px solid #e5e7eb;"><div style="font-size:28px;font-weight:700;color:{color};">{value}</div><div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;">{label}</div></td>'

        def period_row(label, mtd, qtd, ytd):
            return f'<tr><td style="padding:6px 12px;border:1px solid #e5e7eb;font-size:13px;">{label}</td><td style="padding:6px 12px;text-align:center;border:1px solid #e5e7eb;font-size:13px;font-weight:600;">{mtd}</td><td style="padding:6px 12px;text-align:center;border:1px solid #e5e7eb;font-size:13px;font-weight:600;">{qtd}</td><td style="padding:6px 12px;text-align:center;border:1px solid #e5e7eb;font-size:13px;font-weight:600;">{ytd}</td></tr>'

        def period_header():
            return '<tr style="background:#f9fafb;"><th style="padding:8px 12px;text-align:left;border:1px solid #e5e7eb;font-size:12px;">Metric</th><th style="padding:8px 12px;text-align:center;border:1px solid #e5e7eb;font-size:12px;">MTD</th><th style="padding:8px 12px;text-align:center;border:1px solid #e5e7eb;font-size:12px;">QTD</th><th style="padding:8px 12px;text-align:center;border:1px solid #e5e7eb;font-size:12px;">YTD</th></tr>'

        def section_title(num, title, color="#1a1a2e"):
            return f'<h2 style="font-size:16px;color:{color};border-bottom:2px solid {color};padding-bottom:6px;margin:24px 0 12px;">{num}. {title}</h2>'

        def inr(v):
            return f"₹{v:,.0f}"

        att = hr.get("attendance_today", {})
        tasks = ct.get("tasks", {})
        tc = ct.get("tasks_completed", {})
        pc = ct.get("projects_completed", {})
        ea = fe.get("expenses_approved", {})
        eamt = fe.get("expense_amount", {})
        ta = fe.get("travel_amount", {})
        la = hr.get("leaves_approved", {})
        nj = hr.get("new_joiners", {})

        html = f'''<html><body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f3f4f6;">
        <div style="max-width:800px;margin:20px auto;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

        <div style="background:#1a1a2e;padding:24px 32px;color:#ffffff;">
            <h1 style="margin:0;font-size:20px;font-weight:600;">DVBC ERP — CEO Daily Intelligence Report</h1>
            <p style="margin:6px 0 0;font-size:14px;color:#a0a0b0;">{date} | 13-Section Control Tower</p>
        </div>

        <div style="padding:24px 32px;">

        {section_title(1, "Sales Activity Snapshot")}
        <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
            <tr>{kpi("New Leads", sa["new_leads"])}{kpi("Meetings", sa["meetings"])}{kpi("Follow-Ups Done", sa["followups_done"], "#059669")}{kpi("Follow-Ups Missed", sa["followups_missed"], "#dc2626")}</tr>
            <tr>{kpi("Proposals Sent", sa["proposals_sent"])}{kpi("SOW Generated", sa["sow_generated"])}{kpi("Closed Won", sa["closed_won"], "#059669")}{kpi("Closed Lost", sa["closed_lost"], "#dc2626")}</tr>
        </table>
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
            {period_header()}
            {period_row("New Leads", sa.get("mtd_leads",0), sa.get("qtd_leads",0), sa.get("ytd_leads",0))}
        </table>

        {section_title(2, "Sales Pipeline Health")}
        <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
            <tr style="background:#f9fafb;"><th style="padding:8px 12px;text-align:left;border:1px solid #e5e7eb;font-size:12px;">Stage</th><th style="padding:8px 12px;text-align:center;border:1px solid #e5e7eb;font-size:12px;">Leads</th></tr>
            {"".join(f'<tr><td style="padding:6px 12px;border:1px solid #e5e7eb;font-size:13px;">{s["stage"]}</td><td style="padding:6px 12px;text-align:center;border:1px solid #e5e7eb;font-size:13px;font-weight:600;">{s["count"]}</td></tr>' for s in ph["stages"])}
        </table>
        <p style="font-size:12px;color:#6b7280;margin-bottom:24px;">Conversion Rate: <strong>{ph["conversion_rate"]}%</strong> | Total: {ph["total_leads"]}</p>

        {section_title(3, f'Missed Follow-Up Escalations ({esc["count"]})', "#dc2626")}
        {"".join(f'<div style="padding:10px 14px;margin-bottom:8px;border-left:4px solid #dc2626;background:#fef2f2;border-radius:4px;"><strong>{e.get("client_name","")}</strong> — {e.get("entity_type","").title()} | {e.get("assigned_to_name","")} | <span style="color:#dc2626;font-weight:600;">{e.get("days_overdue",0)}d overdue</span></div>' for e in esc["items"][:10]) if esc["count"] > 0 else '<p style="color:#6b7280;font-size:13px;">No escalations.</p>'}

        {section_title(4, f'Meeting Summary (Today: {mtg["count"]} | MTD: {mtg.get("mtd_count",0)})')}
        {f'<p style="color:#6b7280;font-size:13px;">No meetings today.</p>' if mtg["count"] == 0 else "".join(f'<div style="padding:8px 14px;margin-bottom:6px;background:#f9fafb;border-radius:4px;border:1px solid #e5e7eb;font-size:13px;"><strong>{m.get("client_name","") or m.get("title","")}</strong> — {m.get("meeting_type","")}</div>' for m in mtg["items"][:10])}

        {section_title(5, "Consulting Operations")}
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
            <tr>{kpi("Active Projects", con["active"])}{kpi("At Risk", con["at_risk"], "#dc2626")}{kpi("Completed", con["completed"], "#059669")}</tr>
        </table>

        {section_title(6, "SOW & Agreement Tracker")}
        <p style="font-size:13px;">Pending SOWs: <strong>{sow["pending_sows"]}</strong> | Pending Agreements: <strong>{sow["pending_agreements"]}</strong></p>

        {section_title(7, "Payment & Finance")}
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
            <tr>{kpi("Outstanding", pay["outstanding"])}{kpi("Received Today", pay["received_today"], "#059669")}{kpi("Overdue 15d+", pay["overdue_15_days"], "#dc2626")}</tr>
        </table>

        {section_title(8, "Revenue Snapshot (MTD / QTD / YTD)")}
        <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
            <tr>{kpi("Today", inr(rev["today_revenue"]))}{kpi("MTD", inr(rev["mtd_revenue"]), "#059669")}{kpi("QTD", inr(rev["qtd_revenue"]), "#2563eb")}{kpi("YTD", inr(rev["ytd_revenue"]), "#7c3aed")}</tr>
        </table>

        {section_title(9, "Team Productivity Index")}
        {"".join(f'<div style="display:flex;justify-content:space-between;padding:6px 12px;margin-bottom:4px;background:{("#f0fdf4" if i==0 else "#f9fafb")};border-radius:4px;font-size:13px;"><span><strong>#{i+1}</strong> {t["name"]} ({t["role"]})</span><span>M:{t["meetings"]} F:{t["followups_done"]} Score:{t["score"]}</span></div>' for i, t in enumerate(tp["team"][:5])) if tp["team"] else '<p style="color:#6b7280;font-size:13px;">No activity today.</p>'}

        {section_title(10, "System Health")}
        <table style="width:100%;border-collapse:collapse;margin-bottom:12px;">
            <tr>{kpi("Active Users", sh["active_users"])}{kpi("Meetings Today", sh["meetings_logged_today"])}{kpi("Follow-ups Tomorrow", sh["followups_tomorrow"])}</tr>
        </table>
        {"<div style='padding:10px;background:#fef2f2;border-left:4px solid #dc2626;border-radius:4px;font-size:13px;'>Warning: <strong>" + str(sh["anomalies"]["leads_without_followups"]) + "</strong> active leads have no scheduled follow-ups.</div>" if sh["anomalies"]["leads_without_followups"] > 0 else ""}

        {section_title(11, "HR Metrics", "#7c3aed")}
        <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
            <tr>{kpi("Total Employees", hr.get("total_employees",0))}{kpi("Present Today", att.get("present",0), "#059669")}{kpi("Absent", att.get("absent",0), "#dc2626")}{kpi("WFH", att.get("wfh",0), "#2563eb")}</tr>
        </table>
        <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
            <tr>{kpi("Leave Today", att.get("leave",0))}{kpi("Leaves Pending", hr.get("leaves_pending",0), "#f59e0b")}{kpi("Onboarding Queue", hr.get("onboarding_pending",0))}</tr>
        </table>
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
            {period_header()}
            {period_row("Leaves Approved", la.get("mtd",0), la.get("qtd",0), la.get("ytd",0))}
            {period_row("New Joiners", nj.get("mtd",0), nj.get("qtd",0), nj.get("ytd",0))}
        </table>

        {section_title(12, "Consulting Team Performance", "#0891b2")}
        <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
            <tr>{kpi("Consultants", ct.get("total_consultants",0))}{kpi("Tasks Active", tasks.get("in_progress",0))}{kpi("Tasks Done", tasks.get("completed",0), "#059669")}{kpi("Tasks Overdue", tasks.get("overdue",0), "#dc2626")}</tr>
        </table>
        <p style="font-size:12px;color:#6b7280;margin-bottom:8px;">MTD Logged Hours: <strong>{ct.get("mtd_logged_hours",0):.1f}h</strong></p>
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
            {period_header()}
            {period_row("Tasks Completed", tc.get("mtd",0), tc.get("qtd",0), tc.get("ytd",0))}
            {period_row("Projects Completed", pc.get("mtd",0), pc.get("qtd",0), pc.get("ytd",0))}
        </table>

        {section_title(13, "Finance & Expenses", "#d97706")}
        <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
            <tr>{kpi("Expenses Pending", fe.get("expenses_pending",0), "#f59e0b")}{kpi("Travel Pending", fe.get("travel_pending",0), "#f59e0b")}</tr>
        </table>
        <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
            {period_header()}
            {period_row("Expenses Approved", ea.get("mtd",0), ea.get("qtd",0), ea.get("ytd",0))}
            {period_row("Expense Amount", inr(eamt.get("mtd",0)), inr(eamt.get("qtd",0)), inr(eamt.get("ytd",0)))}
            {period_row("Travel Reimbursed", inr(ta.get("mtd",0)), inr(ta.get("qtd",0)), inr(ta.get("ytd",0)))}
        </table>
        {"<p style='font-size:12px;color:#6b7280;'>Latest Payroll: <strong>" + str((fe.get("latest_payroll") or {}).get("month","N/A")) + "</strong> — Status: " + str((fe.get("latest_payroll") or {}).get("status","N/A")) + "</p>" if fe.get("latest_payroll") else ""}

        </div>

        <div style="background:#f9fafb;padding:16px 32px;text-align:center;border-top:1px solid #e5e7eb;">
            <p style="margin:0;font-size:11px;color:#9ca3af;">Generated by NETRA ERP — DVBC Consulting | {report["generated_at"]}</p>
        </div>
        </div></body></html>'''
        return html

    # ======================== SEND REPORT ========================

    async def send_report(self) -> Dict[str, Any]:
        """Generate report, render HTML, send email with retry."""
        from services.email_service import send_email

        log_entry = {
            "date": datetime.utcnow(),
            "email_type": "ceo_daily_report",
            "records_included": 0,
            "delivery_status": "pending",
            "failure_message": None,
        }

        try:
            report = await self.generate_report()
            html = self._render_html(report)
            subject = f"DVBC ERP Daily Intelligence Report — {report['date']}"
            log_entry["records_included"] = sum([
                report["sales_activity"]["new_leads"],
                report["sales_activity"]["meetings"],
                report["escalations"]["count"],
                report["meetings"]["count"],
            ])

            last_error = None
            for attempt in range(3):
                try:
                    result = await send_email(
                        to_email=self.recipient, subject=subject, html_content=html,
                    )
                    if result.get("status") == "sent":
                        log_entry["delivery_status"] = "sent"
                        log_entry["failure_message"] = None
                        logger.info(f"CEO Daily Report sent to {self.recipient}")
                        break
                    elif result.get("status") == "skipped":
                        last_error = result.get("message", "SMTP not configured")
                        logger.warning(f"Email skipped: {last_error}")
                        break
                    else:
                        last_error = result.get("message", "Unknown error")
                        logger.warning(f"Email attempt {attempt+1} failed: {last_error}")
                        if attempt < 2:
                            await asyncio.sleep(5)
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Email attempt {attempt+1} failed: {e}")
                    if attempt < 2:
                        await asyncio.sleep(5)

            if log_entry["delivery_status"] != "sent":
                log_entry["delivery_status"] = "failed"
                log_entry["failure_message"] = last_error
                logger.error(f"CEO Daily Report failed after retries: {last_error}")

        except Exception as e:
            log_entry["delivery_status"] = "error"
            log_entry["failure_message"] = str(e)
            logger.error(f"CEO Report generation error: {e}")

        await self.db.system_email_logs.insert_one(log_entry)
        log_entry.pop("_id", None)
        if hasattr(log_entry.get("date"), "isoformat"):
            log_entry["date"] = log_entry["date"].isoformat()

        return log_entry
