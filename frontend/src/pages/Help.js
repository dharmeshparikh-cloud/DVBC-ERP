import React, { useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { 
  HelpCircle, Mail, Phone, BookOpen, ExternalLink, FileText,
  ChevronDown, ChevronRight, Users, BarChart3, Calendar,
  Briefcase, Shield, Receipt, ClipboardCheck, UserCog, Building2
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { useNavigate } from 'react-router-dom';

const MODULE_GUIDES = [
  {
    title: 'Sales Module',
    icon: BarChart3,
    color: 'bg-emerald-50 text-emerald-600',
    items: [
      { q: 'How do I create a new lead?', a: 'Go to Sales > Leads, click "Add Lead". Fill in company name, contact person, email, phone, and source. The lead enters the 9-step funnel automatically.' },
      { q: 'What is the Sales Funnel flow?', a: 'Lead > Meeting > Pricing Plan > SOW > Proforma Invoice > Agreement > Payment Verification > Kickoff > Project. Each step is accessed from within the lead\'s funnel view.' },
      { q: 'How do I record a meeting?', a: 'Open a lead, click "Record Meeting" in the funnel step 2. Fill meeting details, attendees, and notes. MOM is auto-generated.' },
      { q: 'How do I send an agreement to a client?', a: 'In the lead funnel step 6, create the agreement. Then use "Send via Email" button to email the PDF + DOCX to the client.' },
      { q: 'Where do I see follow-ups?', a: 'Sales > Lead Follow-ups shows all pending follow-ups. You can also see them on the dashboard.' },
    ]
  },
  {
    title: 'HR Module',
    icon: Users,
    color: 'bg-purple-50 text-purple-600',
    items: [
      { q: 'How do I onboard a new employee?', a: 'HR > Onboarding > Send invite link to candidate. They fill the form online. HR reviews, completes onboarding, assigns Employee ID, and triggers Go-Live.' },
      { q: 'How do I process payroll?', a: 'HR > Payroll Engine. Select the month, verify attendance data, review CTC components, and generate payslips. Admin approval is required.' },
      { q: 'How do I manage leave requests?', a: 'HR > Leave Management shows all pending leave applications. Approve or reject with comments. Leave balances auto-update.' },
      { q: 'How do I design CTC for an employee?', a: 'HR > CTC Designer. Select the employee, set annual CTC, and the system auto-calculates Basic, HRA, PF, ESI, etc. Requires Admin approval.' },
      { q: 'How do I handle employee exit?', a: 'HR > Exit Management. Initiate exit request, set last working day, and track notice period. Final settlement is calculated automatically.' },
    ]
  },
  {
    title: 'Consulting Module',
    icon: Briefcase,
    color: 'bg-teal-50 text-teal-600',
    items: [
      { q: 'How do I log consulting meetings?', a: 'Consulting > Consulting Meetings. Click "Log Meeting", select project, fill details. MOM auto-generates and can be sent to client.' },
      { q: 'How do I view my assigned projects?', a: 'Consulting > My Projects shows all projects you\'re assigned to, with deliverables, timelines, and meeting counts.' },
      { q: 'How do I submit consulting expenses?', a: 'Consulting > Expenses. Click "New Expense", attach receipts, select project, and submit for approval.' },
      { q: 'How do I request additional meetings?', a: 'Consulting > Meeting Requests. Submit a request specifying the reason, and your manager will approve/reject it.' },
      { q: 'Where do I see effort tracking?', a: 'Consulting > Efforts Summary shows hours logged per project, meeting counts, and utilization metrics.' },
    ]
  },
  {
    title: 'Self-Service (My Workspace)',
    icon: UserCog,
    color: 'bg-blue-50 text-blue-600',
    items: [
      { q: 'How do I check in/check out?', a: 'Use the "Quick Attendance" bar on your dashboard, or go to My Workspace > My Attendance. The mobile app also supports check-in.' },
      { q: 'How do I apply for leave?', a: 'My Workspace > My Leaves > "Apply Leave". Select leave type, dates, and reason. Your manager gets notified automatically.' },
      { q: 'How do I view my salary slips?', a: 'My Workspace > My Salary Slips shows all generated payslips by month. Click any to view/download PDF.' },
      { q: 'How do I update my bank details?', a: 'My Workspace > My Details > Bank Details section. Changes require HR verification before taking effect.' },
      { q: 'How do I submit expenses?', a: 'My Workspace > My Expenses > "New Expense". Attach receipt, select category, enter amount. Goes to manager for approval.' },
    ]
  },
  {
    title: 'Admin & Settings',
    icon: Shield,
    color: 'bg-zinc-100 text-zinc-600',
    items: [
      { q: 'How do I manage user access?', a: 'Admin > Access & Roles. Three tabs: Roles & Groups (create/edit roles), People Access (per-employee permissions), Department View (bulk access).' },
      { q: 'How do I add office locations?', a: 'Admin > Admin Masters > Office Locations. Add address with GPS coordinates for geo-fenced attendance.' },
      { q: 'How do I configure email templates?', a: 'Admin > Email Templates. Edit templates for onboarding invites, meeting notifications, agreement emails, etc.' },
      { q: 'How do I view the security audit log?', a: 'Admin > Security Audit. Shows all login attempts, permission changes, and sensitive data access with timestamps.' },
      { q: 'How do I see business reports?', a: 'Admin > CEO Report for executive dashboard. Sales > Reports and Consulting > Reports for module-specific analytics.' },
    ]
  },
];

const GENERAL_FAQS = [
  { q: 'How do I reset my password?', a: 'Click your profile icon (bottom-left of sidebar) > Settings > Change Password. Enter current password and new password.' },
  { q: 'How do I switch between dark and light mode?', a: 'Click the moon/sun icon in the top-right corner of the header bar.' },
  { q: 'How do I use the mobile app?', a: 'Go to My Workspace > Mobile App for download instructions. The mobile app supports check-in/out, leave applications, and expense submissions.' },
  { q: 'How do I use the AI Assistant?', a: 'Click "AI Assistant" in the sidebar. Ask questions about your ERP data like "How many leads this month?" or "Show my attendance summary".' },
  { q: 'How do I contact support?', a: 'Email support@dvconsulting.co.in or call the number below. You can also use Team Chat for internal queries.' },
];

function FAQItem({ q, a }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-zinc-100 last:border-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between py-3 px-1 text-left hover:bg-zinc-50 rounded-sm transition-colors"
        data-testid={`faq-${q.slice(0, 20).replace(/\s/g, '-').toLowerCase()}`}
      >
        <span className="text-sm font-medium text-zinc-800 pr-4">{q}</span>
        {open ? <ChevronDown className="w-4 h-4 text-zinc-400 flex-shrink-0" /> : <ChevronRight className="w-4 h-4 text-zinc-400 flex-shrink-0" />}
      </button>
      {open && (
        <div className="pb-3 px-1 text-sm text-zinc-500 leading-relaxed">{a}</div>
      )}
    </div>
  );
}

export default function Help() {
  const navigate = useNavigate();
  const [activeModule, setActiveModule] = useState(null);

  return (
    <div className="space-y-8 max-w-5xl" data-testid="help-page">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-950 mb-2">Help & Support</h1>
        <p className="text-zinc-500">Guides, FAQs, and support for NETRA ERP</p>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-zinc-200 hover:border-emerald-300 transition-colors cursor-pointer" onClick={() => navigate('/tutorials')}>
          <CardContent className="p-5 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <div className="font-medium text-sm text-zinc-900">Interactive Tutorials</div>
              <div className="text-xs text-zinc-500">Step-by-step guided tours</div>
            </div>
            <ExternalLink className="w-4 h-4 text-zinc-300 ml-auto" />
          </CardContent>
        </Card>
        <Card className="border-zinc-200 hover:border-blue-300 transition-colors cursor-pointer" onClick={() => window.location.href = 'mailto:support@dvconsulting.co.in'}>
          <CardContent className="p-5 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
              <Mail className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <div className="font-medium text-sm text-zinc-900">Email Support</div>
              <div className="text-xs text-zinc-500">support@dvconsulting.co.in</div>
            </div>
            <ExternalLink className="w-4 h-4 text-zinc-300 ml-auto" />
          </CardContent>
        </Card>
        <Card className="border-zinc-200 hover:border-purple-300 transition-colors cursor-pointer" onClick={() => navigate('/workflow')}>
          <CardContent className="p-5 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center">
              <ClipboardCheck className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <div className="font-medium text-sm text-zinc-900">ERP Workflow</div>
              <div className="text-xs text-zinc-500">Visual process flow diagram</div>
            </div>
            <ExternalLink className="w-4 h-4 text-zinc-300 ml-auto" />
          </CardContent>
        </Card>
      </div>

      {/* Module Guides */}
      <div>
        <h2 className="text-lg font-semibold text-zinc-900 mb-4">Module Guides</h2>
        <div className="space-y-3">
          {MODULE_GUIDES.map((mod, idx) => {
            const Icon = mod.icon;
            const isActive = activeModule === idx;
            return (
              <Card key={mod.title} className={`border-zinc-200 transition-all ${isActive ? 'ring-1 ring-zinc-300' : ''}`}>
                <button
                  className="w-full p-4 flex items-center gap-3 text-left"
                  onClick={() => setActiveModule(isActive ? null : idx)}
                  data-testid={`module-guide-${mod.title.toLowerCase().replace(/\s/g, '-')}`}
                >
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${mod.color}`}>
                    <Icon className="w-4.5 h-4.5" />
                  </div>
                  <div className="flex-1">
                    <div className="font-medium text-sm text-zinc-900">{mod.title}</div>
                    <div className="text-xs text-zinc-400">{mod.items.length} topics</div>
                  </div>
                  {isActive ? <ChevronDown className="w-4 h-4 text-zinc-400" /> : <ChevronRight className="w-4 h-4 text-zinc-400" />}
                </button>
                {isActive && (
                  <CardContent className="pt-0 px-4 pb-4">
                    <div className="border-t border-zinc-100 pt-2">
                      {mod.items.map((item) => (
                        <FAQItem key={item.q} q={item.q} a={item.a} />
                      ))}
                    </div>
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      </div>

      {/* General FAQs */}
      <div>
        <h2 className="text-lg font-semibold text-zinc-900 mb-4">General FAQs</h2>
        <Card className="border-zinc-200">
          <CardContent className="p-4">
            {GENERAL_FAQS.map((faq) => (
              <FAQItem key={faq.q} q={faq.q} a={faq.a} />
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Contact Info */}
      <Card className="border-zinc-200 bg-zinc-50">
        <CardContent className="p-5">
          <h3 className="font-semibold text-zinc-900 mb-3 text-sm">Need More Help?</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center gap-3">
              <Mail className="w-4 h-4 text-zinc-400" />
              <div>
                <p className="text-xs text-zinc-500">Email</p>
                <p className="text-sm font-medium text-zinc-900">support@dvconsulting.co.in</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Phone className="w-4 h-4 text-zinc-400" />
              <div>
                <p className="text-xs text-zinc-500">Phone</p>
                <p className="text-sm font-medium text-zinc-900">+91 98240 09829</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
