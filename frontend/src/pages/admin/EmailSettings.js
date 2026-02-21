import React, { useState, useEffect } from 'react';
import { Mail, Settings, Save, Eye, Send, Check, X, Clock, RefreshCw, FileText } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const EmailSettings = () => {
  const [config, setConfig] = useState({
    header_html: '',
    footer_html: ''
  });
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('templates');
  const [previewHtml, setPreviewHtml] = useState('');
  const [showPreview, setShowPreview] = useState(false);
  const [testEmail, setTestEmail] = useState('');

  useEffect(() => {
    fetchConfig();
    fetchLogs();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await fetch(`${API_URL}/api/email-actions/config`);
      const data = await res.json();
      setConfig({
        header_html: data.header_html || '',
        footer_html: data.footer_html || ''
      });
    } catch (error) {
      console.error('Error fetching config:', error);
    }
  };

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${API_URL}/api/email-actions/logs?limit=50`);
      const data = await res.json();
      setLogs(data);
    } catch (error) {
      console.error('Error fetching logs:', error);
    }
  };

  const saveConfig = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/email-actions/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      
      if (res.ok) {
        toast.success('Email template configuration saved!');
      } else {
        toast.error('Failed to save configuration');
      }
    } catch (error) {
      console.error('Error saving config:', error);
      toast.error('Error saving configuration');
    }
    setLoading(false);
  };

  const generatePreview = () => {
    const preview = `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body { font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #f5f5f5; }
          .email-container { max-width: 600px; margin: 0 auto; background: white; }
          .content { padding: 30px; }
          .details-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
          .details-table td { padding: 12px; border-bottom: 1px solid #eee; }
          .action-buttons { text-align: center; padding: 25px 0; }
          .btn { display: inline-block; padding: 14px 32px; margin: 0 10px; text-decoration: none; border-radius: 6px; font-weight: 600; }
          .btn-approve { background: #22c55e; color: white; }
          .btn-reject { background: #ef4444; color: white; }
        </style>
      </head>
      <body>
        <div class="email-container">
          ${config.header_html || getDefaultHeader()}
          
          <div class="content">
            <h2>📅 Leave Request Approval</h2>
            <p>Hi <strong>Manager Name</strong>,</p>
            <p><span style="color: #f97316; font-weight: 600;">John Doe</span> has submitted a leave request that requires your approval.</p>
            
            <table class="details-table">
              <tr><td style="color: #666; width: 40%;">Leave Type</td><td style="font-weight: 500;">Casual Leave</td></tr>
              <tr><td style="color: #666;">Duration</td><td style="font-weight: 500;">Feb 25 - Feb 27, 2026</td></tr>
              <tr><td style="color: #666;">Days</td><td style="font-weight: 500;">3 days</td></tr>
              <tr><td style="color: #666;">Reason</td><td style="font-weight: 500;">Personal work</td></tr>
            </table>
            
            <div class="action-buttons">
              <a href="#" class="btn btn-approve">✓ Approve</a>
              <a href="#" class="btn btn-reject">✗ Reject</a>
            </div>
            
            <p style="text-align: center; color: #999; font-size: 12px;">⏰ These action links will expire in 24 hours for security reasons.</p>
          </div>
          
          ${config.footer_html || getDefaultFooter()}
        </div>
      </body>
      </html>
    `;
    
    setPreviewHtml(preview);
    setShowPreview(true);
  };

  const getDefaultHeader = () => `
    <div style="background: linear-gradient(135deg, #1f2937 0%, #374151 100%); padding: 30px; text-align: center;">
      <img src="https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png" alt="DVBC" style="height: 50px; margin-bottom: 10px;">
      <h1 style="color: white; margin: 0; font-size: 24px;">DVBC - NETRA</h1>
      <p style="color: #9ca3af; margin: 5px 0 0 0; font-size: 14px;">Business Management Platform</p>
    </div>
  `;

  const getDefaultFooter = () => `
    <div style="background: #f8fafc; padding: 25px; text-align: center; border-top: 1px solid #e5e7eb;">
      <p style="color: #666; margin: 0 0 10px 0; font-size: 14px;">This is an automated message from NETRA ERP</p>
      <p style="color: #999; margin: 0; font-size: 12px;">© 2026 DVBC Consulting. All rights reserved.</p>
    </div>
  `;

  const sendTestEmail = async () => {
    if (!testEmail) {
      toast.error('Please enter an email address');
      return;
    }
    
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/email-actions/send-approval`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          record_type: 'leave_request',
          record_id: 'test-123',
          recipient_email: testEmail,
          recipient_name: 'Test User',
          requester_name: 'NETRA System',
          details: {
            leave_type: 'Casual Leave',
            start_date: 'Feb 25, 2026',
            end_date: 'Feb 27, 2026',
            days: '3 days',
            reason: 'Test email from NETRA'
          }
        })
      });
      
      if (res.ok) {
        toast.success('Test email sent successfully!');
        fetchLogs();
      } else {
        toast.error('Failed to send test email');
      }
    } catch (error) {
      console.error('Error sending test email:', error);
      toast.error('Error sending test email');
    }
    setLoading(false);
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="p-6" data-testid="email-settings-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Email Action Settings</h1>
          <p className="text-gray-500">Configure email templates for approval notifications</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 mb-6 border-b">
        <button
          onClick={() => setActiveTab('templates')}
          className={`pb-3 px-1 font-medium transition ${
            activeTab === 'templates' 
              ? 'text-orange-600 border-b-2 border-orange-600' 
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Settings className="w-4 h-4 inline mr-2" />
          Templates
        </button>
        <button
          onClick={() => setActiveTab('logs')}
          className={`pb-3 px-1 font-medium transition ${
            activeTab === 'logs' 
              ? 'text-orange-600 border-b-2 border-orange-600' 
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <FileText className="w-4 h-4 inline mr-2" />
          Email Logs
        </button>
        <button
          onClick={() => setActiveTab('test')}
          className={`pb-3 px-1 font-medium transition ${
            activeTab === 'test' 
              ? 'text-orange-600 border-b-2 border-orange-600' 
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Send className="w-4 h-4 inline mr-2" />
          Test
        </button>
      </div>

      {/* Templates Tab */}
      {activeTab === 'templates' && (
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-6">
            {/* Header HTML */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="font-semibold text-gray-800 mb-4">Email Header HTML</h3>
              <p className="text-sm text-gray-500 mb-4">
                Customize the header that appears at the top of all approval emails. Leave empty to use default.
              </p>
              <textarea
                value={config.header_html}
                onChange={(e) => setConfig({ ...config, header_html: e.target.value })}
                placeholder="<div>Your custom header HTML...</div>"
                className="w-full h-48 p-3 font-mono text-sm bg-gray-50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
              />
            </div>

            {/* Footer HTML */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="font-semibold text-gray-800 mb-4">Email Footer HTML</h3>
              <p className="text-sm text-gray-500 mb-4">
                Customize the footer that appears at the bottom of all approval emails. Leave empty to use default.
              </p>
              <textarea
                value={config.footer_html}
                onChange={(e) => setConfig({ ...config, footer_html: e.target.value })}
                placeholder="<div>Your custom footer HTML...</div>"
                className="w-full h-48 p-3 font-mono text-sm bg-gray-50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={saveConfig}
                disabled={loading}
                className="flex items-center gap-2 px-6 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 transition"
              >
                <Save className="w-4 h-4" />
                {loading ? 'Saving...' : 'Save Configuration'}
              </button>
              <button
                onClick={generatePreview}
                className="flex items-center gap-2 px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition"
              >
                <Eye className="w-4 h-4" />
                Preview Email
              </button>
            </div>
          </div>

          {/* Info Panel */}
          <div className="space-y-6">
            <div className="bg-gradient-to-br from-orange-50 to-pink-50 rounded-xl p-6">
              <h3 className="font-semibold text-gray-800 mb-4">📧 How Email Actions Work</h3>
              <ul className="space-y-3 text-sm text-gray-600">
                <li className="flex items-start gap-2">
                  <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                  <span>When approval is needed, an email is sent with Approve/Reject buttons</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                  <span>One-click actions - no login required</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                  <span>Links expire after 24 hours for security</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                  <span>Single-use tokens prevent reuse</span>
                </li>
              </ul>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="font-semibold text-gray-800 mb-4">Supported Record Types</h3>
              <div className="space-y-3">
                {[
                  { type: 'Leave Requests', desc: 'Employee leave applications' },
                  { type: 'Expenses', desc: 'Expense reimbursement claims' },
                  { type: 'Kickoff Requests', desc: 'Project kickoff approvals' },
                  { type: 'Go-Live', desc: 'Employee activation approvals' }
                ].map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-800">{item.type}</p>
                      <p className="text-sm text-gray-500">{item.desc}</p>
                    </div>
                    <Mail className="w-5 h-5 text-orange-500" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Logs Tab */}
      {activeTab === 'logs' && (
        <div className="bg-white rounded-xl shadow-lg overflow-hidden">
          <div className="p-4 border-b flex items-center justify-between">
            <h3 className="font-semibold text-gray-800">Email Send Logs</h3>
            <button onClick={fetchLogs} className="p-2 hover:bg-gray-100 rounded-lg transition">
              <RefreshCw className="w-4 h-4 text-gray-500" />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Type</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Recipient</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Requester</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Subject</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Sent At</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {logs.map((log, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium capitalize">
                        {log.record_type?.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-gray-800">{log.recipient_name}</p>
                        <p className="text-sm text-gray-500">{log.recipient_email}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{log.requester_name}</td>
                    <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{log.subject}</td>
                    <td className="px-4 py-3 text-gray-500 text-sm">{formatDate(log.sent_at)}</td>
                    <td className="px-4 py-3">
                      {log.status === 'sent' ? (
                        <span className="inline-flex items-center gap-1 text-green-600">
                          <Check className="w-4 h-4" /> Sent
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-red-600">
                          <X className="w-4 h-4" /> Failed
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
                {logs.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      No emails sent yet
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Test Tab */}
      {activeTab === 'test' && (
        <div className="max-w-lg">
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h3 className="font-semibold text-gray-800 mb-4">Send Test Email</h3>
            <p className="text-sm text-gray-500 mb-4">
              Send a test approval email to verify your configuration.
            </p>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Recipient Email
                </label>
                <input
                  type="email"
                  value={testEmail}
                  onChange={(e) => setTestEmail(e.target.value)}
                  placeholder="test@example.com"
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
                />
              </div>
              
              <button
                onClick={sendTestEmail}
                disabled={loading || !testEmail}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 transition"
              >
                <Send className="w-4 h-4" />
                {loading ? 'Sending...' : 'Send Test Email'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {showPreview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="font-semibold text-gray-800">Email Preview</h3>
              <button onClick={() => setShowPreview(false)} className="p-1 hover:bg-gray-100 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="overflow-y-auto max-h-[70vh]">
              <iframe
                srcDoc={previewHtml}
                className="w-full h-[600px] border-0"
                title="Email Preview"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EmailSettings;
