import React, { useRef, useContext, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { ArrowLeft, Download, FileText, Printer } from 'lucide-react';
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
  const printRef = useRef(null);

  const { data: fullData, isLoading } = useQuery({
    queryKey: ['agreement-full', agreementId],
    queryFn: () => axios.get(`${API}/agreements/${agreementId}/full`).then(r => r.data),
    enabled: !!agreementId
  });

  const agreement = fullData?.agreement || {};
  const lead = fullData?.lead || {};
  const inherited = fullData?.inherited || {};
  const pricingPlan = fullData?.pricing_plan || {};
  const sowData = fullData?.sow || {};

  const teamDeployment = inherited.team_deployment || [];
  const sowScopes = inherited.sow_scopes || [];
  const paymentSchedule = inherited.payment_schedule || {};
  const totalValue = inherited.total_value || agreement.total_value || 0;
  const durationMonths = inherited.duration_months || 12;
  const startDate = inherited.start_date || agreement.start_date || '';
  const endDate = inherited.end_date || agreement.end_date || '';

  const today = new Date();
  const todayFormatted = today.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });

  // NDA/NCA enforcement date: 24 months from agreement creation
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

  // Compute total meetings
  const totalMeetings = useMemo(() => {
    return teamDeployment.reduce((sum, m) => sum + ((m.committed_meetings || m.total_meetings || m.meetings || 0) * (m.count || 1)), 0);
  }, [teamDeployment]);

  const logoUrl = window.location.origin + '/assets/dv-logo.png';

  const getAgreementHTML = () => {
    const schedule = paymentSchedule.installments || paymentSchedule.schedule_breakdown || [];
    const installmentsHTML = schedule.map((inst, idx) => {
      const amount = inst.amount || inst.net || inst.basic || 0;
      const label = inst.label || inst.frequency || `Installment ${idx + 1}`;
      const dueDate = inst.due_date ? new Date(inst.due_date).toLocaleDateString('en-IN') : '-';
      const gst = inst.gst || 0;
      const basic = inst.basic || amount;
      return `
      <tr>
        <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">${idx + 1}</td>
        <td style="border:1px solid #d1d5db;padding:8px 12px;">${label}</td>
        <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:right;">${formatINR(basic)}</td>
        <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:right;">${gst ? formatINR(gst) : '-'}</td>
        <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:right;font-weight:600;">${formatINR(amount)}</td>
        <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">${dueDate}</td>
      </tr>
    `;
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
      const items = scope.items || scope.deliverables || scope.scope_items || [];
      const itemsList = Array.isArray(items) ? items.map(i => typeof i === 'string' ? i : (i.name || i.title || i.description || '')).filter(Boolean) : [];
      return `
        <tr>
          <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">${idx + 1}</td>
          <td style="border:1px solid #d1d5db;padding:8px 12px;font-weight:600;">${scope.category || scope.name || scope.title || '-'}</td>
          <td style="border:1px solid #d1d5db;padding:8px 12px;">${scope.scope_name || scope.description || '-'}</td>
          <td style="border:1px solid #d1d5db;padding:8px 12px;">${itemsList.length > 0 ? '<ul style="margin:0;padding-left:16px;">' + itemsList.map(i => `<li>${i}</li>`).join('') + '</ul>' : '-'}</td>
        </tr>
      `;
    }).join('');

    return `
      <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:800px;margin:0 auto;color:#1a1a1a;line-height:1.6;font-size:13px;">
        <!-- Logo -->
        <div style="text-align:center;margin-bottom:24px;padding-top:20px;">
          <img src="${logoUrl}" alt="D&V Business Consulting" style="height:70px;max-width:280px;object-fit:contain;" />
        </div>
        
        <!-- Title -->
        <h1 style="text-align:center;font-size:22px;font-weight:700;margin:16px 0 6px;text-transform:uppercase;letter-spacing:1.5px;border-bottom:3px solid #1a1a1a;padding-bottom:10px;">
          Service Agreement
        </h1>
        <p style="text-align:center;font-size:12px;color:#555;margin:4px 0 20px;">
          Agreement No: <strong>${agreement.agreement_number || '-'}</strong>
        </p>

        <!-- Made Between -->
        <div style="margin:16px 0;padding:14px 18px;background:#f9fafb;border-left:4px solid #1a1a1a;font-size:13px;">
          <p style="margin:0;">This Service Agreement (<strong>"Agreement"</strong>) is made and entered into on <strong>${todayFormatted}</strong>, by and between:</p>
        </div>

        <!-- Parties -->
        <table style="width:100%;border-collapse:collapse;margin:12px 0 20px;">
          <tr>
            <td style="width:48%;vertical-align:top;padding:12px 16px;border:1px solid #e5e7eb;background:#f9fafb;">
              <p style="font-weight:700;font-size:14px;margin:0 0 6px;color:#111;">Party A (Service Provider)</p>
              <p style="margin:2px 0;"><strong>D&V Business Consulting LLP</strong></p>
              <p style="margin:2px 0;font-size:12px;color:#555;">Mumbai, Maharashtra, India</p>
            </td>
            <td style="width:4%;text-align:center;vertical-align:middle;font-weight:700;font-size:16px;">AND</td>
            <td style="width:48%;vertical-align:top;padding:12px 16px;border:1px solid #e5e7eb;background:#f9fafb;">
              <p style="font-weight:700;font-size:14px;margin:0 0 6px;color:#111;">Party B (Client)</p>
              <p style="margin:2px 0;"><strong>${clientCompany}</strong></p>
              ${clientAddress ? `<p style="margin:2px 0;font-size:12px;color:#555;">${clientAddress}</p>` : ''}
              ${clientGSTIN ? `<p style="margin:2px 0;font-size:12px;">GSTIN: <strong>${clientGSTIN}</strong></p>` : ''}
            </td>
          </tr>
        </table>

        <!-- Section 1: Scope of Work -->
        <h2 style="font-size:15px;font-weight:700;margin:24px 0 10px;padding:6px 12px;background:#1a1a1a;color:#fff;text-transform:uppercase;letter-spacing:0.5px;">1. Scope of Work</h2>
        <p style="margin:0 0 10px;">The Service Provider shall deliver the following consulting services to the Client as defined in the approved Scope of Work:</p>
        ${sowScopes.length > 0 ? `
          <table style="width:100%;border-collapse:collapse;margin:8px 0;">
            <thead>
              <tr style="background:#f3f4f6;">
                <th style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;width:40px;">S.No</th>
                <th style="border:1px solid #d1d5db;padding:8px 12px;text-align:left;">Category</th>
                <th style="border:1px solid #d1d5db;padding:8px 12px;text-align:left;">Scope</th>
                <th style="border:1px solid #d1d5db;padding:8px 12px;text-align:left;">Deliverables</th>
              </tr>
            </thead>
            <tbody>${scopeHTML}</tbody>
          </table>
        ` : '<p style="color:#777;font-style:italic;">Scope of Work details to be defined as per the agreed Statement of Work.</p>'}

        <!-- Section 2: Team Deployment -->
        <h2 style="font-size:15px;font-weight:700;margin:24px 0 10px;padding:6px 12px;background:#1a1a1a;color:#fff;text-transform:uppercase;letter-spacing:0.5px;">2. Team Deployment &amp; Meeting Schedule</h2>
        <p style="margin:0 0 10px;">The following consulting team shall be deployed for the engagement:</p>
        ${teamDeployment.length > 0 ? `
          <table style="width:100%;border-collapse:collapse;margin:8px 0;">
            <thead>
              <tr style="background:#f3f4f6;">
                <th style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;width:40px;">S.No</th>
                <th style="border:1px solid #d1d5db;padding:8px 12px;text-align:left;">Role</th>
                <th style="border:1px solid #d1d5db;padding:8px 12px;text-align:left;">Meeting Type</th>
                <th style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">Count</th>
                <th style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">Total Meetings</th>
              </tr>
            </thead>
            <tbody>${teamDeploymentHTML}</tbody>
            <tfoot>
              <tr style="background:#f3f4f6;font-weight:700;">
                <td colspan="4" style="border:1px solid #d1d5db;padding:8px 12px;text-align:right;">Total Meetings</td>
                <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">${totalMeetings}</td>
              </tr>
            </tfoot>
          </table>
        ` : '<p style="color:#777;font-style:italic;">Team deployment details as per the approved Pricing Plan.</p>'}

        <!-- Section 3: Investment & Payment -->
        <h2 style="font-size:15px;font-weight:700;margin:24px 0 10px;padding:6px 12px;background:#1a1a1a;color:#fff;text-transform:uppercase;letter-spacing:0.5px;">3. Investment, Payment Terms &amp; Schedule</h2>
        
        <table style="width:100%;border-collapse:collapse;margin:8px 0;">
          <tr>
            <td style="border:1px solid #d1d5db;padding:10px 14px;font-weight:600;background:#f9fafb;width:35%;">Total Investment</td>
            <td style="border:1px solid #d1d5db;padding:10px 14px;font-size:15px;font-weight:700;">${formatINR(totalValue)}</td>
          </tr>
          <tr>
            <td style="border:1px solid #d1d5db;padding:10px 14px;font-weight:600;background:#f9fafb;">Project Duration</td>
            <td style="border:1px solid #d1d5db;padding:10px 14px;">${durationMonths} Months</td>
          </tr>
          <tr>
            <td style="border:1px solid #d1d5db;padding:10px 14px;font-weight:600;background:#f9fafb;">Start Date</td>
            <td style="border:1px solid #d1d5db;padding:10px 14px;">${startDate || 'As mutually agreed'}</td>
          </tr>
          <tr>
            <td style="border:1px solid #d1d5db;padding:10px 14px;font-weight:600;background:#f9fafb;">End Date</td>
            <td style="border:1px solid #d1d5db;padding:10px 14px;">${endDate || 'As per project duration'}</td>
          </tr>
        </table>

        ${schedule.length > 0 ? `
          <h3 style="font-size:14px;font-weight:600;margin:16px 0 8px;">Payment Schedule</h3>
          <table style="width:100%;border-collapse:collapse;margin:8px 0;">
            <thead>
              <tr style="background:#f3f4f6;">
                <th style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;width:40px;">S.No</th>
                <th style="border:1px solid #d1d5db;padding:8px 12px;text-align:left;">Description</th>
                <th style="border:1px solid #d1d5db;padding:8px 12px;text-align:right;">Basic</th>
                <th style="border:1px solid #d1d5db;padding:8px 12px;text-align:right;">GST</th>
                <th style="border:1px solid #d1d5db;padding:8px 12px;text-align:right;">Net Amount</th>
                <th style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">Due Date</th>
              </tr>
            </thead>
            <tbody>${installmentsHTML}</tbody>
            <tfoot>
              <tr style="background:#f3f4f6;font-weight:700;">
                <td colspan="4" style="border:1px solid #d1d5db;padding:8px 12px;text-align:right;">Total</td>
                <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:right;">${formatINR(totalValue)}</td>
                <td style="border:1px solid #d1d5db;padding:8px 12px;"></td>
              </tr>
            </tfoot>
          </table>
        ` : ''}

        <!-- Section 4: Legal Clauses -->
        <h2 style="font-size:15px;font-weight:700;margin:24px 0 10px;padding:6px 12px;background:#1a1a1a;color:#fff;text-transform:uppercase;letter-spacing:0.5px;">4. Terms &amp; Conditions</h2>

        <h3 style="font-size:13px;font-weight:700;margin:14px 0 6px;">4.1 Confidentiality &amp; Non-Disclosure Agreement (NDA)</h3>
        <p style="margin:0 0 8px;text-align:justify;">Both parties agree to maintain strict confidentiality regarding all proprietary information, trade secrets, business strategies, client data, financial records, and any other confidential material shared during the term of this Agreement. Neither party shall disclose, publish, or otherwise reveal any confidential information to any third party without the prior written consent of the disclosing party. This obligation of confidentiality shall survive the termination of this Agreement and remain in full force and effect until <strong>${ndaEndFormatted}</strong> (24 months from the date of this Agreement).</p>

        <h3 style="font-size:13px;font-weight:700;margin:14px 0 6px;">4.2 Non-Compete Agreement (NCA)</h3>
        <p style="margin:0 0 8px;text-align:justify;">During the term of this Agreement and for a period of twenty-four (24) months following its termination (i.e., until <strong>${ndaEndFormatted}</strong>), neither party shall, directly or indirectly, engage in any business activity that competes with the core consulting services provided under this Agreement within the same geographic market or industry vertical. This includes soliciting or attempting to solicit business from any client, prospect, or entity that has been serviced or engaged by either party during the term of this Agreement.</p>

        <h3 style="font-size:13px;font-weight:700;margin:14px 0 6px;">4.3 Anti-Poaching</h3>
        <p style="margin:0 0 8px;text-align:justify;">Both parties mutually agree that during the tenure of this Agreement and for a period of twenty-four (24) months from the date of its termination, neither party shall directly or indirectly solicit, recruit, hire, or engage any employee, consultant, or contractor of the other party without prior written consent. Any breach of this clause shall entitle the aggrieved party to seek compensation equivalent to twelve (12) months of the concerned individual's last drawn compensation, in addition to any other legal remedies available.</p>

        <h3 style="font-size:13px;font-weight:700;margin:14px 0 6px;">4.4 Intellectual Property</h3>
        <p style="margin:0 0 8px;text-align:justify;">All intellectual property, frameworks, methodologies, templates, and proprietary tools used or developed by the Service Provider in the course of delivering services under this Agreement shall remain the exclusive property of the Service Provider. The Client shall have a non-exclusive, non-transferable license to use the deliverables produced under this Agreement for its internal business purposes only.</p>

        <h3 style="font-size:13px;font-weight:700;margin:14px 0 6px;">4.5 Limitation of Liability</h3>
        <p style="margin:0 0 8px;text-align:justify;">In no event shall either party be liable for any indirect, incidental, special, consequential, or punitive damages arising out of or relating to this Agreement, regardless of the cause of action or theory of liability. The aggregate liability of the Service Provider under this Agreement shall not exceed the total fees paid by the Client under this Agreement.</p>

        <h3 style="font-size:13px;font-weight:700;margin:14px 0 6px;">4.6 Termination</h3>
        <p style="margin:0 0 8px;text-align:justify;">Either party may terminate this Agreement by providing thirty (30) days written notice to the other party. In the event of termination, the Client shall pay for all services rendered up to the effective date of termination. Any advance payments for services not yet rendered shall be refunded on a pro-rata basis within thirty (30) days of termination.</p>

        <h3 style="font-size:13px;font-weight:700;margin:14px 0 6px;">4.7 Dispute Resolution</h3>
        <p style="margin:0 0 8px;text-align:justify;">Any dispute arising out of or in connection with this Agreement shall first be attempted to be resolved through good-faith negotiation. If the dispute cannot be resolved within thirty (30) days, it shall be referred to arbitration in accordance with the Arbitration and Conciliation Act, 1996, and the seat of arbitration shall be Mumbai, Maharashtra, India.</p>

        <h3 style="font-size:13px;font-weight:700;margin:14px 0 6px;">4.8 Governing Law</h3>
        <p style="margin:0 0 8px;text-align:justify;">This Agreement shall be governed by and construed in accordance with the laws of India. The courts of Mumbai, Maharashtra shall have exclusive jurisdiction over any proceedings arising out of this Agreement.</p>

        <h3 style="font-size:13px;font-weight:700;margin:14px 0 6px;">4.9 Force Majeure</h3>
        <p style="margin:0 0 8px;text-align:justify;">Neither party shall be held liable for any failure or delay in performing its obligations under this Agreement if such failure or delay results from circumstances beyond the reasonable control of that party, including but not limited to natural disasters, acts of government, pandemic, or other force majeure events.</p>

        <h3 style="font-size:13px;font-weight:700;margin:14px 0 6px;">4.10 Entire Agreement</h3>
        <p style="margin:0 0 8px;text-align:justify;">This Agreement, together with its annexures and schedules, constitutes the entire agreement between the parties with respect to the subject matter hereof and supersedes all prior negotiations, representations, warranties, commitments, offers, and agreements, whether written or oral.</p>

        <!-- Signature Block -->
        <h2 style="font-size:15px;font-weight:700;margin:30px 0 10px;padding:6px 12px;background:#1a1a1a;color:#fff;text-transform:uppercase;letter-spacing:0.5px;">5. Signatures</h2>
        <p style="margin:0 0 16px;">IN WITNESS WHEREOF, the parties hereto have executed this Agreement as of the date first written above.</p>

        <table style="width:100%;border-collapse:collapse;">
          <tr>
            <td style="width:48%;vertical-align:top;padding:16px;border:1px solid #e5e7eb;">
              <p style="font-weight:700;font-size:14px;margin:0 0 24px;color:#111;">For D&V Business Consulting LLP</p>
              <div style="height:60px;border-bottom:1px solid #999;margin-bottom:8px;"></div>
              <p style="margin:4px 0;font-size:12px;">Authorized Signatory</p>
              <p style="margin:4px 0;font-size:12px;">Name: ____________________________</p>
              <p style="margin:4px 0;font-size:12px;">Designation: _______________________</p>
              <p style="margin:4px 0;font-size:12px;">Date: _____________________________</p>
            </td>
            <td style="width:4%;"></td>
            <td style="width:48%;vertical-align:top;padding:16px;border:1px solid #e5e7eb;">
              <p style="font-weight:700;font-size:14px;margin:0 0 24px;color:#111;">For ${clientCompany}</p>
              <div style="height:60px;border-bottom:1px solid #999;margin-bottom:8px;"></div>
              <p style="margin:4px 0;font-size:12px;">Authorized Signatory</p>
              <p style="margin:4px 0;font-size:12px;">Name: ____________________________</p>
              <p style="margin:4px 0;font-size:12px;">Designation: _______________________</p>
              <p style="margin:4px 0;font-size:12px;">Date: _____________________________</p>
            </td>
          </tr>
        </table>

        <p style="text-align:center;font-size:11px;color:#888;margin-top:24px;">
          This is a computer-generated document. Agreement No: ${agreement.agreement_number || '-'}
        </p>
      </div>
    `;
  };

  const handlePrint = () => {
    const html = getAgreementHTML();
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <html><head><title>Agreement - ${agreement.agreement_number || ''}</title>
      <style>
        @media print {
          body { margin: 0; padding: 20px 40px; }
          @page { margin: 20mm 15mm; }
        }
        body { font-family: 'Segoe UI', Arial, sans-serif; }
      </style>
      </head><body>${html}</body></html>
    `);
    printWindow.document.close();
    printWindow.onload = () => { printWindow.print(); };
  };

  const handleDownloadDocx = () => {
    try {
      const html = getAgreementHTML();
      const docContent = `
        <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">
        <head><meta charset="utf-8"><title>Agreement</title>
        <!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->
        <style>
          @page { size: A4; margin: 20mm 15mm; }
          body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }
          table { border-collapse: collapse; }
        </style>
        </head><body>${html}</body></html>
      `;
      const blob = new Blob(['\ufeff', docContent], { type: 'application/msword' });
      saveAs(blob, `Agreement_${agreement.agreement_number || agreementId}.docx`);
      toast.success('Agreement downloaded as .docx');
    } catch (err) {
      console.error('DOCX download error:', err);
      toast.error('Failed to generate document');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96" data-testid="agreement-loading">
        <div className="text-zinc-500">Loading agreement...</div>
      </div>
    );
  }

  return (
    <div className="max-w-[900px] mx-auto px-4 py-6" data-testid="agreement-view">
      {leadId && (
        <FunnelStepperHeader leadId={leadId} currentStep="agreement" />
      )}

      {/* Action Bar */}
      <div className="flex items-center justify-between mb-6 no-print">
        <Button variant="ghost" onClick={() => navigate(-1)} data-testid="agreement-back-btn">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handlePrint} data-testid="agreement-print-btn">
            <Printer className="w-4 h-4 mr-2" /> Print / PDF
          </Button>
          <Button onClick={handleDownloadDocx} data-testid="agreement-download-docx-btn">
            <Download className="w-4 h-4 mr-2" /> Download .docx
          </Button>
        </div>
      </div>

      {/* Agreement Document */}
      <div 
        ref={printRef}
        className="bg-white border border-zinc-200 rounded-lg shadow-sm p-8"
        data-testid="agreement-document"
        dangerouslySetInnerHTML={{ __html: getAgreementHTML() }}
      />
    </div>
  );
};

export default AgreementView;
