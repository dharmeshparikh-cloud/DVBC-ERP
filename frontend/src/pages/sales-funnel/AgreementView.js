import React, { useRef, useContext, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { ArrowLeft, Download, Printer, Mail, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { formatINR } from '../../utils/currency';
import FunnelStepperHeader from '../../components/FunnelStepperHeader';
import { saveAs } from 'file-saver';

const AgreementView = () => {
  const { agreementId } = useParams();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('leadId');
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [sending, setSending] = useState(false);
  const [showEmailDialog, setShowEmailDialog] = useState(false);
  const [recipientEmail, setRecipientEmail] = useState('');
  const [recipientName, setRecipientName] = useState('');

  const { data: fullData, isLoading } = useQuery({
    queryKey: ['agreement-full', agreementId],
    queryFn: () => axios.get(`${API}/agreements/${agreementId}/full`).then(r => r.data),
    enabled: !!agreementId
  });

  const agreement = fullData?.agreement || {};
  const lead = fullData?.lead || {};
  const inherited = fullData?.inherited || {};

  const teamDeployment = inherited.team_deployment || [];
  const sowScopes = inherited.sow_scopes || [];
  const paymentSchedule = inherited.payment_schedule || {};
  const totalValue = inherited.total_value || agreement.total_value || 0;
  const durationMonths = inherited.duration_months || 12;
  const startDate = inherited.start_date || agreement.start_date || '';
  const endDate = inherited.end_date || agreement.end_date || '';

  const today = new Date();
  const todayFormatted = today.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });

  const agreementCreatedDate = agreement.created_at ? new Date(agreement.created_at) : today;
  const ndaEndDate = new Date(agreementCreatedDate);
  ndaEndDate.setMonth(ndaEndDate.getMonth() + 24);
  const ndaEndFormatted = ndaEndDate.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });

  const clientCompany = agreement.client_name || lead.company || '';
  const clientAddress = agreement.client_address || lead.address || lead.company_address || '';
  const clientGSTIN = agreement.client_gstin || lead.gstin || lead.gst_number || '';
  const clientContactName = `${lead.first_name || ''} ${lead.last_name || ''}`.trim();
  const clientPhone = agreement.client_phone || lead.phone || '';
  const clientEmail = agreement.client_email || lead.email || '';

  const totalMeetings = useMemo(() => {
    return teamDeployment.reduce((sum, m) => sum + ((m.committed_meetings || m.total_meetings || m.meetings || 0) * (m.count || 1)), 0);
  }, [teamDeployment]);

  const logoUrl = window.location.origin + '/assets/dv-logo.png';

  const getAgreementHTML = () => {
    const schedule = paymentSchedule.installments || paymentSchedule.schedule_breakdown || [];
    const installmentsHTML = schedule.map((inst, idx) => {
      const amount = inst.amount || inst.net || inst.basic || 0;
      const label = inst.label || inst.frequency || `Installment ${idx + 1}`;
      const gst = inst.gst || 0;
      const basic = inst.basic || amount;
      return `
      <tr>
        <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">${idx + 1}</td>
        <td style="border:1px solid #d1d5db;padding:8px 12px;">${label}</td>
        <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:right;">${formatINR(basic)}</td>
        <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:right;">${gst ? formatINR(gst) : '-'}</td>
        <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:right;font-weight:600;">${formatINR(amount)}</td>
      </tr>`;
    }).join('');

    const teamDeploymentHTML = teamDeployment.map((m, idx) => `
      <tr>
        <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">${idx + 1}</td>
        <td style="border:1px solid #d1d5db;padding:8px 12px;">${m.role || m.role_name || '-'}</td>
        <td style="border:1px solid #d1d5db;padding:8px 12px;">${m.meeting_type || m.type || '-'}</td>
        <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">${m.count || m.quantity || 1}</td>
        <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">${(m.committed_meetings || m.total_meetings || m.meetings || 0) * (m.count || 1)}</td>
      </tr>
    `).join('');

    const scopeHTML = sowScopes.map((scope, idx) => {
      const items = scope.deliverables || scope.items || scope.scope_items || [];
      const itemsList = Array.isArray(items) ? items.map(i => typeof i === 'string' ? i : (i.name || i.title || i.description || '')).filter(Boolean) : [];
      return `
        <tr>
          <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">${idx + 1}</td>
          <td style="border:1px solid #d1d5db;padding:8px 12px;font-weight:600;">${scope.category || scope.name || '-'}</td>
          <td style="border:1px solid #d1d5db;padding:8px 12px;">${scope.name || scope.scope_name || scope.description || '-'}</td>
          <td style="border:1px solid #d1d5db;padding:8px 12px;">${itemsList.length > 0 ? '<ul style="margin:0;padding-left:16px;">' + itemsList.map(i => '<li>' + i + '</li>').join('') + '</ul>' : '-'}</td>
        </tr>`;
    }).join('');

    const sectionHeader = (num, title) => `<h2 style="font-size:14px;font-weight:700;margin:28px 0 10px;padding:8px 14px;background:#e5e7eb;color:#1a1a1a;text-transform:uppercase;letter-spacing:0.5px;">${num}. ${title}</h2>`;

    return `
      <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:800px;margin:0 auto;color:#1a1a1a;line-height:1.7;font-size:12.5px;">
        <div style="text-align:center;margin-bottom:24px;padding-top:16px;">
          <img src="${logoUrl}" alt="D&V Business Consulting" style="height:65px;max-width:260px;object-fit:contain;" />
        </div>
        
        <h1 style="text-align:center;font-size:20px;font-weight:700;margin:12px 0 4px;text-transform:uppercase;letter-spacing:2px;border-bottom:2px solid #9ca3af;padding-bottom:10px;">Service Agreement</h1>
        <p style="text-align:center;font-size:11px;color:#6b7280;margin:4px 0 16px;">Agreement No: <strong>${agreement.agreement_number || '-'}</strong></p>

        <div style="margin:12px 0;padding:12px 16px;background:#f3f4f6;border-left:4px solid #6b7280;font-size:12.5px;">
          <p style="margin:0;">This Service Agreement (<strong>"Agreement"</strong>) is made and entered into on <strong>${todayFormatted}</strong>, by and between:</p>
        </div>

        <table style="width:100%;border-collapse:collapse;margin:10px 0 18px;">
          <tr>
            <td style="width:47%;vertical-align:top;padding:12px 14px;border:1px solid #e5e7eb;background:#f9fafb;">
              <p style="font-weight:700;font-size:13px;margin:0 0 6px;color:#111;">Party A (Service Provider)</p>
              <p style="margin:2px 0;font-weight:600;">D&V Business Consulting</p>
              <p style="margin:2px 0;font-size:11.5px;color:#4b5563;">301, Business Hub, Prahlad Nagar,</p>
              <p style="margin:2px 0;font-size:11.5px;color:#4b5563;">Ahmedabad - 380015, Gujarat, India</p>
            </td>
            <td style="width:6%;text-align:center;vertical-align:middle;font-weight:700;font-size:14px;color:#6b7280;">AND</td>
            <td style="width:47%;vertical-align:top;padding:12px 14px;border:1px solid #e5e7eb;background:#f9fafb;">
              <p style="font-weight:700;font-size:13px;margin:0 0 6px;color:#111;">Party B (Client)</p>
              <p style="margin:2px 0;font-weight:600;">${clientCompany}</p>
              ${clientAddress ? `<p style="margin:2px 0;font-size:11.5px;color:#4b5563;">${clientAddress}</p>` : ''}
              ${clientGSTIN ? `<p style="margin:4px 0;font-size:11.5px;">GSTIN: <strong>${clientGSTIN}</strong></p>` : ''}
              ${clientContactName ? `<p style="margin:2px 0;font-size:11.5px;color:#4b5563;">Contact: ${clientContactName}</p>` : ''}
              ${clientEmail ? `<p style="margin:2px 0;font-size:11.5px;color:#4b5563;">Email: ${clientEmail}</p>` : ''}
              ${clientPhone ? `<p style="margin:2px 0;font-size:11.5px;color:#4b5563;">Phone: ${clientPhone}</p>` : ''}
            </td>
          </tr>
        </table>

        ${sectionHeader('1', 'Scope of Work')}
        <p style="margin:0 0 10px;text-align:justify;">The Service Provider shall deliver the following consulting services to the Client as outlined in the approved Scope of Work document. Both parties agree that the scope, deliverables, and timelines specified herein represent the mutually agreed-upon engagement parameters.</p>
        ${sowScopes.length > 0 ? `
          <table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:11.5px;">
            <thead>
              <tr style="background:#f3f4f6;">
                <th style="border:1px solid #d1d5db;padding:7px 10px;text-align:center;width:35px;">S.No</th>
                <th style="border:1px solid #d1d5db;padding:7px 10px;text-align:left;">Category</th>
                <th style="border:1px solid #d1d5db;padding:7px 10px;text-align:left;">Scope</th>
                <th style="border:1px solid #d1d5db;padding:7px 10px;text-align:left;">Deliverables</th>
              </tr>
            </thead>
            <tbody>${scopeHTML}</tbody>
          </table>` : '<p style="color:#777;font-style:italic;">Scope of Work as per the approved SOW document.</p>'}

        ${sectionHeader('2', 'Team Deployment & Meeting Schedule')}
        <p style="margin:0 0 10px;text-align:justify;">The Service Provider shall deploy the following consulting team members for the duration of this engagement. The meeting schedule, frequency, and mode of delivery are as specified below. Any changes to the team composition or meeting schedule shall require prior written intimation from the Service Provider.</p>
        ${teamDeployment.length > 0 ? `
          <table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:11.5px;">
            <thead>
              <tr style="background:#f3f4f6;">
                <th style="border:1px solid #d1d5db;padding:7px 10px;text-align:center;width:35px;">S.No</th>
                <th style="border:1px solid #d1d5db;padding:7px 10px;text-align:left;">Role</th>
                <th style="border:1px solid #d1d5db;padding:7px 10px;text-align:left;">Meeting Type</th>
                <th style="border:1px solid #d1d5db;padding:7px 10px;text-align:center;">Count</th>
                <th style="border:1px solid #d1d5db;padding:7px 10px;text-align:center;">Total Meetings</th>
              </tr>
            </thead>
            <tbody>${teamDeploymentHTML}</tbody>
            <tfoot>
              <tr style="background:#f3f4f6;font-weight:700;">
                <td colspan="4" style="border:1px solid #d1d5db;padding:7px 10px;text-align:right;">Total Committed Meetings</td>
                <td style="border:1px solid #d1d5db;padding:7px 10px;text-align:center;">${totalMeetings}</td>
              </tr>
            </tfoot>
          </table>` : ''}

        ${sectionHeader('3', 'Investment, Payment Terms & Schedule')}
        <table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:12px;">
          <tr><td style="border:1px solid #d1d5db;padding:10px 14px;font-weight:600;background:#f9fafb;width:35%;">Total Investment</td><td style="border:1px solid #d1d5db;padding:10px 14px;font-size:14px;font-weight:700;">${formatINR(totalValue)}</td></tr>
          <tr><td style="border:1px solid #d1d5db;padding:10px 14px;font-weight:600;background:#f9fafb;">Project Duration</td><td style="border:1px solid #d1d5db;padding:10px 14px;">${durationMonths} Months</td></tr>
          <tr><td style="border:1px solid #d1d5db;padding:10px 14px;font-weight:600;background:#f9fafb;">Commencement Date</td><td style="border:1px solid #d1d5db;padding:10px 14px;">${startDate || 'As mutually agreed'}</td></tr>
          <tr><td style="border:1px solid #d1d5db;padding:10px 14px;font-weight:600;background:#f9fafb;">Completion Date</td><td style="border:1px solid #d1d5db;padding:10px 14px;">${endDate || 'As per project duration'}</td></tr>
        </table>

        ${schedule.length > 0 ? `
          <h3 style="font-size:13px;font-weight:600;margin:16px 0 8px;">Payment Schedule</h3>
          <table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:11.5px;">
            <thead><tr style="background:#f3f4f6;">
              <th style="border:1px solid #d1d5db;padding:7px 10px;text-align:center;width:35px;">S.No</th>
              <th style="border:1px solid #d1d5db;padding:7px 10px;text-align:left;">Description</th>
              <th style="border:1px solid #d1d5db;padding:7px 10px;text-align:right;">Basic (INR)</th>
              <th style="border:1px solid #d1d5db;padding:7px 10px;text-align:right;">GST</th>
              <th style="border:1px solid #d1d5db;padding:7px 10px;text-align:right;">Net Amount</th>
            </tr></thead>
            <tbody>${installmentsHTML}</tbody>
            <tfoot><tr style="background:#f3f4f6;font-weight:700;">
              <td colspan="4" style="border:1px solid #d1d5db;padding:7px 10px;text-align:right;">Grand Total</td>
              <td style="border:1px solid #d1d5db;padding:7px 10px;text-align:right;">${formatINR(schedule.reduce((s,i) => s + (i.amount || i.net || 0), 0))}</td>
            </tr></tfoot>
          </table>` : ''}

        <h3 style="font-size:13px;font-weight:600;margin:16px 0 8px;">Payment Terms &amp; Conditions</h3>
        <p style="margin:0 0 6px;text-align:justify;">3.1. All invoices shall be raised on the first working day of the applicable quarter and are payable within fifteen (15) business days from the date of receipt of the invoice. The Client shall make payment via NEFT, RTGS, or cheque drawn in favour of "D&V Business Consulting".</p>
        <p style="margin:0 0 6px;text-align:justify;">3.2. All amounts stated herein are exclusive of applicable Goods and Services Tax (GST) unless explicitly stated otherwise. GST shall be charged at the prevailing rate (currently ${paymentSchedule.gst_percentage || 18}%) and shall be borne by the Client in addition to the consulting fees.</p>
        <p style="margin:0 0 6px;text-align:justify;">3.3. In the event of delayed payment beyond the stipulated due date, a late payment interest of 1.5% per month (18% per annum) shall be applicable on the outstanding amount from the due date until the date of actual receipt of payment. The Service Provider reserves the right to suspend services if payment remains overdue for more than thirty (30) days.</p>
        <p style="margin:0 0 6px;text-align:justify;">3.4. The first installment constitutes the advance payment and is non-refundable. It must be received and verified prior to the commencement of services and deployment of the consulting team. Subsequent installments shall be payable as per the schedule above.</p>
        <p style="margin:0 0 6px;text-align:justify;">3.5. The Service Provider shall provide a valid GST-compliant tax invoice for each installment. The Client may request a proforma invoice prior to any payment for their internal processing requirements. Any tax withholding (TDS) obligations shall be handled by the Client as per applicable tax laws, and the corresponding TDS certificate shall be provided to the Service Provider within the statutory timelines.</p>

        ${sectionHeader('4', 'Confidentiality & Non-Disclosure Agreement (NDA)')}
        <p style="margin:0 0 6px;text-align:justify;">4.1. Both parties acknowledge and agree that in the course of performing their respective obligations under this Agreement, each party may have access to and become acquainted with confidential and proprietary information belonging to the other party. "Confidential Information" shall include, but not be limited to, all business plans, strategies, financial data, client lists, customer databases, marketing plans, operational methodologies, trade secrets, technical know-how, software, algorithms, pricing structures, employee information, vendor arrangements, intellectual property, and any other information that is not generally available to the public, whether disclosed orally, in writing, electronically, or by any other means.</p>
        <p style="margin:0 0 6px;text-align:justify;">4.2. Each party agrees to hold all Confidential Information of the other party in strict confidence and shall not, without the prior written consent of the disclosing party, disclose, publish, communicate, or otherwise make available any Confidential Information to any third party, or use such Confidential Information for any purpose other than the performance of obligations under this Agreement. Each party shall take all reasonable measures to protect the confidentiality of the other party's Confidential Information, including but not limited to implementing appropriate physical, electronic, and administrative safeguards.</p>
        <p style="margin:0 0 6px;text-align:justify;">4.3. The obligations of confidentiality under this clause shall survive the expiration or termination of this Agreement and shall remain in full force and effect until <strong>${ndaEndFormatted}</strong>, being a period of twenty-four (24) months from the date of execution of this Agreement. Any breach of this clause shall entitle the aggrieved party to seek immediate injunctive relief in addition to any other remedies available at law or in equity, including but not limited to monetary damages and legal costs incurred in enforcing this provision.</p>

        ${sectionHeader('5', 'Non-Compete Agreement (NCA)')}
        <p style="margin:0 0 6px;text-align:justify;">5.1. During the term of this Agreement and for a period of twenty-four (24) months following its expiration or termination (i.e., until <strong>${ndaEndFormatted}</strong>), neither party shall, directly or indirectly, whether individually or through any affiliate, subsidiary, agent, partner, or representative, engage in, establish, carry on, or participate in any business activity, venture, or enterprise that directly competes with the core consulting services, advisory services, or business solutions provided under this Agreement within the same geographic market, industry vertical, or client segment served by the other party during the term of this Agreement.</p>
        <p style="margin:0 0 6px;text-align:justify;">5.2. This restriction specifically includes, but is not limited to: (a) soliciting or attempting to solicit business from any client, prospect, lead, or entity that has been engaged, serviced, or pursued by either party during the term of this Agreement; (b) offering substantially similar consulting, training, or advisory services to the same set of clients; (c) engaging any former or current employees or contractors of the other party to provide competing services. Both parties acknowledge that this restriction is reasonable and necessary to protect the legitimate business interests and goodwill of both organizations.</p>
        <p style="margin:0 0 6px;text-align:justify;">5.3. In the event of a breach of this non-compete clause, the breaching party shall be liable to pay liquidated damages equivalent to the total contract value of this Agreement (${formatINR(totalValue)}) in addition to any actual damages suffered by the non-breaching party, including lost revenue, client acquisition costs, and legal expenses.</p>

        ${sectionHeader('6', 'Anti-Poaching')}
        <p style="margin:0 0 6px;text-align:justify;">6.1. Both parties hereby mutually agree and undertake that during the entire tenure of this Agreement and for a period of twenty-four (24) months from the date of its expiration or termination, neither party shall, directly or indirectly, through itself, its affiliates, subsidiaries, or through any third-party intermediary, solicit, recruit, hire, engage, retain, or attempt to solicit, recruit, hire, engage, or retain any employee, consultant, contractor, freelancer, or any other personnel currently employed or engaged by the other party, without obtaining prior written consent from the affected party.</p>
        <p style="margin:0 0 6px;text-align:justify;">6.2. This restriction applies to all categories of personnel, including but not limited to full-time employees, part-time employees, contractual staff, interns, consultants, and any individual who has been associated with the other party within the twelve (12) months immediately preceding the date of solicitation or recruitment attempt. The parties acknowledge that their respective human resources represent significant investments in training, development, and institutional knowledge, and that the loss of such personnel would cause substantial harm to the affected party.</p>
        <p style="margin:0 0 6px;text-align:justify;">6.3. Any breach of this anti-poaching clause shall entitle the aggrieved party to seek compensation equivalent to twenty-four (24) months of the concerned individual's last drawn gross compensation (including all fixed and variable components), in addition to any other legal remedies available under applicable law, including injunctive relief and recovery of all costs incurred in replacing the affected personnel.</p>

        ${sectionHeader('7', 'Early Termination & Closure')}
        <p style="margin:0 0 6px;text-align:justify;">7.1. Either party may terminate this Agreement prior to the completion of the agreed engagement period by mutual written consent of both parties. Both parties agree to enter into good-faith discussions regarding the terms and conditions of such early termination, including the settlement of any outstanding fees, deliverables, and transition requirements.</p>
        <p style="margin:0 0 6px;text-align:justify;">7.2. In the event that either party wishes to terminate this Agreement unilaterally, the terminating party shall provide a minimum of thirty (30) calendar days prior written notice to the other party, clearly stating the reasons for termination and the proposed effective date. During the notice period, both parties shall continue to fulfill their respective obligations under this Agreement in good faith.</p>
        <p style="margin:0 0 6px;text-align:justify;">7.3. Upon early termination: (a) the Client shall pay for all services rendered and deliverables completed up to the effective date of termination, calculated on a pro-rata basis; (b) any advance payments for services not yet rendered shall be refunded within thirty (30) business days of the termination date, after deducting any amounts due for services already provided or expenses incurred; (c) the Service Provider shall transfer all completed and in-progress deliverables to the Client within fifteen (15) business days; (d) both parties shall return or destroy all Confidential Information belonging to the other party.</p>
        <p style="margin:0 0 6px;text-align:justify;">7.4. The Service Provider reserves the right to terminate this Agreement immediately without notice in the event of: (a) non-payment of dues exceeding sixty (60) days; (b) breach of confidentiality or non-compete obligations by the Client; (c) insolvency or bankruptcy proceedings initiated against the Client. In such cases, all outstanding amounts shall become immediately due and payable.</p>

        ${sectionHeader('8', 'General Terms & Conditions')}
        <p style="margin:0 0 6px;text-align:justify;">8.1. <strong>Intellectual Property:</strong> All intellectual property, frameworks, methodologies, templates, proprietary tools, training materials, and analytical models used or developed by the Service Provider in the course of delivering services under this Agreement shall remain the exclusive property of the Service Provider. The Client is granted a non-exclusive, non-transferable, royalty-free license to use the specific deliverables produced under this Agreement solely for its internal business purposes.</p>
        <p style="margin:0 0 6px;text-align:justify;">8.2. <strong>Limitation of Liability:</strong> In no event shall either party be liable for any indirect, incidental, special, consequential, or punitive damages arising out of or relating to this Agreement. The aggregate liability of the Service Provider shall not exceed the total fees actually paid by the Client under this Agreement.</p>
        <p style="margin:0 0 6px;text-align:justify;">8.3. <strong>Dispute Resolution:</strong> Any dispute arising out of or in connection with this Agreement shall first be attempted to be resolved through good-faith negotiation between senior representatives of both parties within thirty (30) days. If unresolved, the dispute shall be referred to binding arbitration in accordance with the Arbitration and Conciliation Act, 1996, with the seat of arbitration being Mumbai, Maharashtra, India. The arbitral tribunal shall consist of a sole arbitrator mutually appointed by both parties.</p>
        <p style="margin:0 0 6px;text-align:justify;">8.4. <strong>Governing Law:</strong> This Agreement shall be governed by and construed in accordance with the laws of the Republic of India. The courts of Mumbai, Maharashtra shall have exclusive jurisdiction over any proceedings arising out of this Agreement.</p>
        <p style="margin:0 0 6px;text-align:justify;">8.5. <strong>Force Majeure:</strong> Neither party shall be held liable for any failure or delay in performing its obligations under this Agreement if such failure or delay results from circumstances beyond the reasonable control of that party, including but not limited to acts of God, natural disasters, epidemics, pandemics, acts of government or regulatory authorities, civil unrest, strikes, lockouts, fire, flood, or interruption of telecommunications or utility services.</p>
        <p style="margin:0 0 6px;text-align:justify;">8.6. <strong>Entire Agreement:</strong> This Agreement, together with its annexures, schedules, and the referenced Scope of Work and Pricing Plan, constitutes the entire agreement between the parties with respect to the subject matter hereof and supersedes all prior negotiations, representations, warranties, commitments, offers, contracts, and agreements, whether written or oral. No amendment or modification of this Agreement shall be valid or binding unless made in writing and signed by authorized representatives of both parties.</p>

        ${sectionHeader('9', 'Execution & Signatures')}
        <p style="margin:0 0 16px;">IN WITNESS WHEREOF, the parties hereto have executed this Agreement as of the date first written above, acknowledging that they have read, understood, and agree to be bound by all the terms and conditions set forth herein.</p>

        <table style="width:100%;border-collapse:collapse;">
          <tr>
            <td style="width:47%;vertical-align:top;padding:16px;border:1px solid #e5e7eb;">
              <p style="font-weight:700;font-size:13px;margin:0 0 24px;color:#111;">For D&V Business Consulting</p>
              <div style="height:60px;border-bottom:1px solid #999;margin-bottom:8px;"></div>
              <p style="margin:4px 0;font-size:11.5px;">Authorized Signatory</p>
              <p style="margin:4px 0;font-size:11.5px;">Name: ____________________________</p>
              <p style="margin:4px 0;font-size:11.5px;">Designation: _______________________</p>
              <p style="margin:4px 0;font-size:11.5px;">Date: _____________________________</p>
              <p style="margin:4px 0;font-size:11.5px;">Place: Ahmedabad</p>
            </td>
            <td style="width:6%;"></td>
            <td style="width:47%;vertical-align:top;padding:16px;border:1px solid #e5e7eb;">
              <p style="font-weight:700;font-size:13px;margin:0 0 24px;color:#111;">For ${clientCompany}</p>
              <div style="height:60px;border-bottom:1px solid #999;margin-bottom:8px;"></div>
              <p style="margin:4px 0;font-size:11.5px;">Authorized Signatory</p>
              <p style="margin:4px 0;font-size:11.5px;">Name: ____________________________</p>
              <p style="margin:4px 0;font-size:11.5px;">Designation: _______________________</p>
              <p style="margin:4px 0;font-size:11.5px;">Date: _____________________________</p>
              <p style="margin:4px 0;font-size:11.5px;">Place: ____________________________</p>
            </td>
          </tr>
        </table>
        <p style="text-align:center;font-size:10px;color:#9ca3af;margin-top:20px;">Agreement No: ${agreement.agreement_number || '-'} | Generated on ${todayFormatted}</p>
      </div>`;
  };

  const handlePrint = () => {
    const html = getAgreementHTML();
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <html><head><title>Agreement - ${agreement.agreement_number || ''}</title>
      <style>@media print{body{margin:0;padding:20px 40px;}@page{margin:15mm 12mm;}}body{font-family:'Segoe UI',Arial,sans-serif;}</style>
      </head><body>${html}</body></html>`);
    printWindow.document.close();
    printWindow.onload = () => { printWindow.print(); };
  };

  const handleDownloadDocx = () => {
    try {
      const html = getAgreementHTML();
      const docContent = `<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">
        <head><meta charset="utf-8"><title>Agreement</title>
        <!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->
        <style>@page{size:A4;margin:20mm 15mm;}body{font-family:'Segoe UI',Arial,sans-serif;font-size:12.5px;}table{border-collapse:collapse;}</style>
        </head><body>${html}</body></html>`;
      const blob = new Blob(['\ufeff', docContent], { type: 'application/msword' });
      saveAs(blob, `Agreement_${agreement.agreement_number || agreementId}.docx`);
      toast.success('Agreement downloaded as .docx');
    } catch (err) {
      toast.error('Failed to generate document');
    }
  };

  const handleSendEmail = async () => {
    if (!recipientEmail || !recipientEmail.includes('@')) {
      toast.error('Please enter a valid email address');
      return;
    }
    setSending(true);
    try {
      const res = await axios.post(`${API}/agreements/${agreementId}/send-email`, {
        recipient_email: recipientEmail,
        recipient_name: recipientName || 'Sir/Madam'
      });
      toast.success(res.data?.message || 'Agreement sent via email');
      setShowEmailDialog(false);
      setRecipientEmail('');
      setRecipientName('');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send email');
    } finally {
      setSending(false);
    }
  };

  const openEmailDialog = () => {
    // Pre-fill with client email if available
    setRecipientEmail(clientEmail || '');
    setRecipientName(clientContactName || '');
    setShowEmailDialog(true);
  };

  if (isLoading) {
    return (<div className="flex items-center justify-center h-96" data-testid="agreement-loading"><div className="text-zinc-500">Loading agreement...</div></div>);
  }

  return (
    <div className="max-w-[900px] mx-auto px-4 py-6" data-testid="agreement-view">
      {leadId && <FunnelStepperHeader leadId={leadId} currentStep="agreement" />}
      <div className="flex items-center justify-between mb-6 no-print">
        <Button variant="ghost" onClick={() => navigate(-1)} data-testid="agreement-back-btn">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handlePrint} data-testid="agreement-print-btn">
            <Printer className="w-4 h-4 mr-2" /> Print / PDF
          </Button>
          <Button variant="outline" onClick={handleDownloadDocx} data-testid="agreement-download-docx-btn">
            <Download className="w-4 h-4 mr-2" /> Download .docx
          </Button>
          <Button onClick={openEmailDialog} data-testid="agreement-send-email-btn">
            <Mail className="w-4 h-4 mr-2" /> Send via Email
          </Button>
        </div>
      </div>
      <div className="bg-white border border-zinc-200 rounded-lg shadow-sm p-8" data-testid="agreement-document" dangerouslySetInnerHTML={{ __html: getAgreementHTML() }} />
      
      {/* Email Recipient Dialog */}
      <Dialog open={showEmailDialog} onOpenChange={setShowEmailDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Send Agreement via Email</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="recipient-email">Recipient Email *</Label>
              <Input
                id="recipient-email"
                type="email"
                placeholder="Enter email address"
                value={recipientEmail}
                onChange={(e) => setRecipientEmail(e.target.value)}
                data-testid="email-recipient-input"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="recipient-name">Recipient Name (Optional)</Label>
              <Input
                id="recipient-name"
                type="text"
                placeholder="Enter recipient name"
                value={recipientName}
                onChange={(e) => setRecipientName(e.target.value)}
                data-testid="email-recipient-name-input"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEmailDialog(false)}>Cancel</Button>
            <Button onClick={handleSendEmail} disabled={sending || !recipientEmail} data-testid="email-send-confirm-btn">
              {sending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Mail className="w-4 h-4 mr-2" />}
              {sending ? 'Sending...' : 'Send Email'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AgreementView;
