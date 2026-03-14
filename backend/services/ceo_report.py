"""
CEO Control Tower — Daily Business Intelligence Report
=========================================================
Generates and sends a comprehensive daily email covering:
Sales Activity, Pipeline Health, Follow-Up Escalations, Meeting Summary,
Consulting Operations, SOW/Agreement Tracker, Payment/Finance, Revenue,
Team Productivity, and System Health.

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
        start_utc = start_ist.astimezone(pytz.utc).replace(tzinfo=None)
        end_utc = end_ist.astimezone(pytz.utc).replace(tzinfo=None)
        return start_utc, end_utc

    async def _count_today(self, collection, date_field="created_at"):
        start, end = self._today_range_utc()
        return await self.db[collection].count_documents({
            date_field: {"$gte": start, "$lt": end}
        })

    async def generate_report(self) -> Dict[str, Any]:
        """Generate all 10 sections of the report."""
        report = {}
        today_ist = self._today_ist()
        report["date"] = today_ist.strftime("%d %b %Y")
        report["generated_at"] = today_ist.isoformat()

        # Section 1: Sales Activity Snapshot
        report["sales_activity"] = await self._section_sales_activity()

        # Section 2: Sales Pipeline Health
        report["pipeline_health"] = await self._section_pipeline_health()

        # Section 3: Missed Follow-Up Escalations
        report["escalations"] = await self._section_escalations()

        # Section 4: Daily Meeting Summary
        report["meetings"] = await self._section_meetings()

        # Section 5: Consulting Project Operations
        report["consulting"] = await self._section_consulting()

        # Section 6: SOW and Agreement Tracker
        report["sow_agreements"] = await self._section_sow_agreements()

        # Section 7: Payment & Finance
        report["payments"] = await self._section_payments()

        # Section 8: Revenue Snapshot
        report["revenue"] = await self._section_revenue()

        # Section 9: Team Productivity
        report["team_productivity"] = await self._section_team_productivity()

        # Section 10: System Health
        report["system_health"] = await self._section_system_health()

        return report

    async def _section_sales_activity(self):
        start, end = self._today_range_utc()
        new_leads = await self._count_today("leads")
        meetings = await self._count_today("meetings")
        followups_done = await self.db.follow_ups.count_documents({
            "status": "closed",
            "closed_at": {"$gte": start.isoformat(), "$lt": end.isoformat()}
        })
        followups_missed = await self.db.follow_ups.count_documents({
            "status": "open",
            "due_date": {"$lt": datetime.utcnow()}
        })
        proposals = await self._count_today("quotations")
        sows = await self._count_today("sows")
        closed_won = await self.db.leads.count_documents({
            "status": "closed_won",
            "updated_at": {"$gte": start, "$lt": end}
        })
        closed_lost = await self.db.leads.count_documents({
            "status": "closed_lost",
            "updated_at": {"$gte": start, "$lt": end}
        })
        reassigned = await self.db.follow_ups.count_documents({
            "history.action": "reassigned",
            "updated_at": {"$gte": start.isoformat(), "$lt": end.isoformat()}
        })
        return {
            "new_leads": new_leads, "meetings": meetings,
            "followups_done": followups_done, "followups_missed": followups_missed,
            "proposals_sent": proposals, "sow_generated": sows,
            "closed_won": closed_won, "closed_lost": closed_lost,
            "leads_reassigned": reassigned
        }

    async def _section_pipeline_health(self):
        pipeline = []
        stages = [
            ("new", "New Lead"), ("contacted", "Contacted"),
            ("meeting_scheduled", "Meeting Scheduled"), ("proposal_sent", "Proposal Sent"),
            ("negotiation", "Negotiation"), ("sow_shared", "SOW Shared"),
            ("closed_won", "Closed Won"), ("closed_lost", "Closed Lost")
        ]
        total_value = 0
        total_leads = 0
        for status, label in stages:
            count = await self.db.leads.count_documents({"status": status})
            pipeline.append({"stage": label, "count": count, "value": 0})
            total_leads += count

        closed_won = await self.db.leads.count_documents({"status": "closed_won"})
        conversion_rate = round((closed_won / total_leads * 100), 1) if total_leads > 0 else 0

        return {
            "stages": pipeline,
            "total_pipeline_value": total_value,
            "total_leads": total_leads,
            "conversion_rate": conversion_rate
        }

    async def _section_escalations(self):
        cutoff = datetime.utcnow() - timedelta(days=2)
        escalated = await self.db.follow_ups.find(
            {"status": "open", "due_date": {"$lt": cutoff}},
            {"_id": 0, "client_name": 1, "entity_type": 1, "assigned_to_name": 1,
             "due_date": 1, "notes": 1}
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
            {"_id": 0, "title": 1, "client_name": 1, "meeting_type": 1,
             "date": 1, "summary": 1, "next_meeting_date": 1, "created_by_name": 1}
        ).to_list(50)
        return {"items": meetings, "count": len(meetings)}

    async def _section_consulting(self):
        active = await self.db.projects.count_documents({"status": {"$in": ["active", "in_progress"]}})
        at_risk = await self.db.projects.count_documents({"status": "at_risk"})
        completed = await self.db.projects.count_documents({"status": "completed"})
        projects = await self.db.projects.find(
            {"status": {"$in": ["active", "in_progress", "at_risk"]}},
            {"_id": 0, "name": 1, "client_name": 1, "status": 1, "assigned_to_name": 1}
        ).to_list(50)
        return {
            "active": active, "at_risk": at_risk, "completed": completed,
            "projects": projects
        }

    async def _section_sow_agreements(self):
        sows = await self.db.sows.find(
            {"status": {"$nin": ["completed", "signed"]}},
            {"_id": 0, "lead_id": 1, "status": 1, "created_at": 1}
        ).to_list(50)
        agreements = await self.db.agreements.find(
            {"status": {"$nin": ["signed", "completed"]}},
            {"_id": 0, "lead_id": 1, "status": 1, "created_at": 1}
        ).to_list(50)
        return {"pending_sows": len(sows), "pending_agreements": len(agreements)}

    async def _section_payments(self):
        outstanding = await self.db.consulting_payments.count_documents({"status": {"$ne": "paid"}})
        start, end = self._today_range_utc()
        received_today = await self.db.consulting_payments.count_documents({
            "status": "paid", "paid_date": {"$gte": start, "$lt": end}
        })
        overdue_15 = await self.db.consulting_payments.count_documents({
            "status": {"$ne": "paid"},
            "due_date": {"$lt": datetime.utcnow() - timedelta(days=15)}
        })
        return {
            "outstanding": outstanding,
            "received_today": received_today,
            "overdue_15_days": overdue_15
        }

    async def _section_revenue(self):
        now_ist = self._today_ist()
        month_start_ist = now_ist.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_start_utc = month_start_ist.astimezone(pytz.utc).replace(tzinfo=None)
        start, end = self._today_range_utc()

        # Count payments received this month
        month_payments = await self.db.consulting_payments.find(
            {"status": "paid", "paid_date": {"$gte": month_start_utc}},
            {"_id": 0, "amount": 1}
        ).to_list(1000)
        mtd_revenue = sum(p.get("amount", 0) for p in month_payments)

        today_payments = await self.db.consulting_payments.find(
            {"status": "paid", "paid_date": {"$gte": start, "$lt": end}},
            {"_id": 0, "amount": 1}
        ).to_list(100)
        today_revenue = sum(p.get("amount", 0) for p in today_payments)

        return {
            "today_revenue": today_revenue,
            "mtd_revenue": mtd_revenue,
        }

    async def _section_team_productivity(self):
        start, end = self._today_range_utc()
        users = await self.db.users.find(
            {"is_active": True},
            {"_id": 0, "id": 1, "full_name": 1, "role": 1, "employee_id": 1}
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

        meetings_today = await self.db.meetings.count_documents({
            "created_at": {"$gte": start, "$lt": end}
        })

        # Follow-ups scheduled tomorrow
        tomorrow_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        tomorrow_end = tomorrow_start + timedelta(days=1)
        followups_tomorrow = await self.db.follow_ups.count_documents({
            "status": "open",
            "due_date": {"$gte": tomorrow_start, "$lt": tomorrow_end}
        })

        # Anomalies: active leads with no follow-ups
        active_leads = await self.db.leads.count_documents({"status": {"$nin": ["closed_won", "closed_lost"]}})
        leads_with_followup = len(await self.db.follow_ups.distinct("entity_id", {"entity_type": "lead", "status": "open"}))
        leads_no_followup = max(0, active_leads - leads_with_followup)

        return {
            "active_users": active_users,
            "meetings_logged_today": meetings_today,
            "followups_tomorrow": followups_tomorrow,
            "anomalies": {
                "leads_without_followups": leads_no_followup
            }
        }

    def _render_html(self, report: Dict) -> str:
        """Render the report as HTML email."""
        date = report["date"]
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

        def kpi_cell(label, value, color="#1a1a2e"):
            return f'''<td style="padding:12px 16px;text-align:center;border:1px solid #e5e7eb;">
                <div style="font-size:28px;font-weight:700;color:{color};">{value}</div>
                <div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;">{label}</div>
            </td>'''

        def table_row(cells, bg="#ffffff"):
            return f'<tr style="background:{bg};">{"".join(f"<td style=&quot;padding:8px 12px;border:1px solid #e5e7eb;font-size:13px;&quot;>{c}</td>" for c in cells)}</tr>'

        html = f'''
        <html><body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f3f4f6;">
        <div style="max-width:800px;margin:20px auto;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

        <!-- Header -->
        <div style="background:#1a1a2e;padding:24px 32px;color:#ffffff;">
            <h1 style="margin:0;font-size:20px;font-weight:600;">DVBC ERP Daily Business Intelligence Report</h1>
            <p style="margin:6px 0 0;font-size:14px;color:#a0a0b0;">{date}</p>
        </div>

        <div style="padding:24px 32px;">

        <!-- Section 1: KPI Snapshot -->
        <h2 style="font-size:16px;color:#1a1a2e;border-bottom:2px solid #1a1a2e;padding-bottom:6px;margin-bottom:12px;">1. Sales Activity Snapshot</h2>
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
            <tr>
                {kpi_cell("New Leads", sa["new_leads"])}
                {kpi_cell("Meetings", sa["meetings"])}
                {kpi_cell("Follow-Ups Done", sa["followups_done"], "#059669")}
                {kpi_cell("Follow-Ups Missed", sa["followups_missed"], "#dc2626")}
            </tr>
            <tr>
                {kpi_cell("Proposals Sent", sa["proposals_sent"])}
                {kpi_cell("SOW Generated", sa["sow_generated"])}
                {kpi_cell("Closed Won", sa["closed_won"], "#059669")}
                {kpi_cell("Closed Lost", sa["closed_lost"], "#dc2626")}
            </tr>
        </table>

        <!-- Section 2: Pipeline -->
        <h2 style="font-size:16px;color:#1a1a2e;border-bottom:2px solid #1a1a2e;padding-bottom:6px;margin-bottom:12px;">2. Sales Pipeline Health</h2>
        <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
            <tr style="background:#f9fafb;"><th style="padding:8px 12px;text-align:left;border:1px solid #e5e7eb;font-size:12px;">Stage</th><th style="padding:8px 12px;text-align:center;border:1px solid #e5e7eb;font-size:12px;">Leads</th></tr>
            {"".join(f'<tr><td style="padding:6px 12px;border:1px solid #e5e7eb;font-size:13px;">{s["stage"]}</td><td style="padding:6px 12px;text-align:center;border:1px solid #e5e7eb;font-size:13px;font-weight:600;">{s["count"]}</td></tr>' for s in ph["stages"])}
        </table>
        <p style="font-size:12px;color:#6b7280;margin-bottom:24px;">Conversion Rate: <strong>{ph["conversion_rate"]}%</strong> | Total Leads: {ph["total_leads"]}</p>

        <!-- Section 3: Escalations -->
        <h2 style="font-size:16px;color:#dc2626;border-bottom:2px solid #dc2626;padding-bottom:6px;margin-bottom:12px;">3. Missed Follow-Up Escalations ({esc["count"]})</h2>
        {"".join(f'<div style="padding:10px 14px;margin-bottom:8px;border-left:4px solid #dc2626;background:#fef2f2;border-radius:4px;"><strong>{e.get("client_name","")}</strong> — {e.get("entity_type","").title()} stage | Assigned: {e.get("assigned_to_name","")} | <span style="color:#dc2626;font-weight:600;">{e.get("days_overdue",0)}d overdue</span></div>' for e in esc["items"][:10]) if esc["count"] > 0 else '<p style="color:#6b7280;font-size:13px;">No escalations today.</p>'}

        <!-- Section 4: Meetings -->
        <h2 style="font-size:16px;color:#1a1a2e;border-bottom:2px solid #1a1a2e;padding-bottom:6px;margin:24px 0 12px;">4. Daily Meeting Summary ({mtg["count"]})</h2>
        {f'<p style="color:#6b7280;font-size:13px;">No meetings recorded today.</p>' if mtg["count"] == 0 else "".join(f'<div style="padding:8px 14px;margin-bottom:6px;background:#f9fafb;border-radius:4px;border:1px solid #e5e7eb;font-size:13px;"><strong>{m.get("client_name","") or m.get("title","Meeting")}</strong> — {m.get("meeting_type","")}</div>' for m in mtg["items"][:10])}

        <!-- Section 5: Consulting -->
        <h2 style="font-size:16px;color:#1a1a2e;border-bottom:2px solid #1a1a2e;padding-bottom:6px;margin:24px 0 12px;">5. Consulting Operations</h2>
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
            <tr>{kpi_cell("Active Projects", con["active"])}{kpi_cell("At Risk", con["at_risk"], "#dc2626")}{kpi_cell("Completed", con["completed"], "#059669")}</tr>
        </table>

        <!-- Section 6: SOW/Agreements -->
        <h2 style="font-size:16px;color:#1a1a2e;border-bottom:2px solid #1a1a2e;padding-bottom:6px;margin-bottom:12px;">6. SOW & Agreement Tracker</h2>
        <p style="font-size:13px;">Pending SOWs: <strong>{sow["pending_sows"]}</strong> | Pending Agreements: <strong>{sow["pending_agreements"]}</strong></p>

        <!-- Section 7: Payments -->
        <h2 style="font-size:16px;color:#1a1a2e;border-bottom:2px solid #1a1a2e;padding-bottom:6px;margin:24px 0 12px;">7. Payment & Finance</h2>
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
            <tr>{kpi_cell("Outstanding", pay["outstanding"])}{kpi_cell("Received Today", pay["received_today"], "#059669")}{kpi_cell("Overdue 15d+", pay["overdue_15_days"], "#dc2626")}</tr>
        </table>

        <!-- Section 8: Revenue -->
        <h2 style="font-size:16px;color:#1a1a2e;border-bottom:2px solid #1a1a2e;padding-bottom:6px;margin-bottom:12px;">8. Revenue Snapshot</h2>
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
            <tr>{kpi_cell("Today Revenue", f"₹{rev['today_revenue']:,.0f}")}{kpi_cell("MTD Revenue", f"₹{rev['mtd_revenue']:,.0f}")}</tr>
        </table>

        <!-- Section 9: Team Productivity -->
        <h2 style="font-size:16px;color:#1a1a2e;border-bottom:2px solid #1a1a2e;padding-bottom:6px;margin:24px 0 12px;">9. Team Productivity Index</h2>
        {"".join(f'<div style="display:flex;justify-content:space-between;padding:6px 12px;margin-bottom:4px;background:{("#f0fdf4" if i == 0 else "#f9fafb")};border-radius:4px;font-size:13px;"><span><strong>#{i+1}</strong> {t["name"]} ({t["role"]})</span><span>Meetings: {t["meetings"]} | Follow-ups: {t["followups_done"]} | Score: {t["score"]}</span></div>' for i, t in enumerate(tp["team"][:5])) if tp["team"] else '<p style="color:#6b7280;font-size:13px;">No activity recorded today.</p>'}

        <!-- Section 10: System Health -->
        <h2 style="font-size:16px;color:#1a1a2e;border-bottom:2px solid #1a1a2e;padding-bottom:6px;margin:24px 0 12px;">10. System Health</h2>
        <table style="width:100%;border-collapse:collapse;margin-bottom:12px;">
            <tr>{kpi_cell("Active Users", sh["active_users"])}{kpi_cell("Meetings Today", sh["meetings_logged_today"])}{kpi_cell("Follow-ups Tomorrow", sh["followups_tomorrow"])}</tr>
        </table>
        {"<div style='padding:10px;background:#fef2f2;border-left:4px solid #dc2626;border-radius:4px;font-size:13px;'>⚠ <strong>" + str(sh["anomalies"]["leads_without_followups"]) + "</strong> active leads have no scheduled follow-ups.</div>" if sh["anomalies"]["leads_without_followups"] > 0 else ""}

        </div>

        <!-- Footer -->
        <div style="background:#f9fafb;padding:16px 32px;text-align:center;border-top:1px solid #e5e7eb;">
            <p style="margin:0;font-size:11px;color:#9ca3af;">Generated by NETRA ERP — DVBC Consulting | {report["generated_at"]}</p>
        </div>
        </div>
        </body></html>
        '''
        return html

    async def send_report(self) -> Dict[str, Any]:
        """Generate report, render HTML, send email with retry."""
        from services.email_service import send_email
        import os

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
            subject = f"DVBC ERP Daily Business Intelligence Report — {report['date']}"
            log_entry["records_included"] = sum([
                report["sales_activity"]["new_leads"],
                report["sales_activity"]["meetings"],
                report["escalations"]["count"],
                report["meetings"]["count"],
            ])

            # Send with retry (up to 3 attempts)
            last_error = None
            for attempt in range(3):
                try:
                    result = await send_email(
                        to_email=self.recipient,
                        subject=subject,
                        html_content=html,
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
                logger.error(f"CEO Daily Report failed after 3 retries: {last_error}")

        except Exception as e:
            log_entry["delivery_status"] = "error"
            log_entry["failure_message"] = str(e)
            logger.error(f"CEO Report generation error: {e}")

        # Store log
        await self.db.system_email_logs.insert_one(log_entry)
        log_entry.pop("_id", None)
        if hasattr(log_entry.get("date"), "isoformat"):
            log_entry["date"] = log_entry["date"].isoformat()

        return log_entry
