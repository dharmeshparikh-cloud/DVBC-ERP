import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Plus, Mail, Copy } from 'lucide-react';
import { toast } from 'sonner';

const EmailTemplates = () => {
  const { user } = useContext(AuthContext);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    subject: '',
    body: '',
    template_type: 'proposal',
    variables: [],
  });

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const response = await axios.get(`${API}/email-templates`);
      setTemplates(response.data);
    } catch (error) {
      toast.error('Failed to fetch email templates');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/email-templates`, formData);
      toast.success('Email template created successfully');
      setDialogOpen(false);
      setFormData({
        name: '',
        subject: '',
        body: '',
        template_type: 'proposal',
        variables: [],
      });
      fetchTemplates();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create email template');
    }
  };

  const copyTemplate = (template) => {
    const text = `Subject: ${template.subject}\n\n${template.body}`;
    navigator.clipboard.writeText(text);
    toast.success('Template copied to clipboard');
  };

  const canEdit = user?.role !== 'manager';

  const defaultTemplates = [
    {
      name: 'High-Value Proposal',
      type: 'proposal',
      subject: 'Partnership Opportunity with {company}',
      body: 'Hi {first_name},\n\nI hope this message finds you well. As {job_title} at {company}, I wanted to reach out about a partnership opportunity that could significantly benefit your organization.\n\nWe specialize in consulting services that have helped similar companies achieve [specific results]. I\'d love to schedule a brief call to discuss how we can help {company} achieve similar success.\n\nWould you be available for a 15-minute call this week?\n\nBest regards,',
    },
    {
      name: 'Demo Request Follow-Up',
      type: 'demo_request',
      subject: 'Quick Question About Our Demo for {company}',
      body: 'Hi {first_name},\n\nI wanted to follow up on your interest in seeing a demo of our consulting services. \n\nI have a few time slots available this week that would work great for a personalized walkthrough tailored specifically to {company}\'s needs.\n\nWould Thursday at 2 PM or Friday at 10 AM work for you?\n\nLooking forward to connecting!',
    },
    {
      name: 'Warm Follow-Up',
      type: 'follow_up',
      subject: 'Following Up - {company} Consulting Services',
      body: 'Hi {first_name},\n\nI wanted to circle back on our previous conversation about consulting opportunities for {company}.\n\nI understand you\'re busy, so I\'ll keep this brief. Would it be helpful if I sent over a quick one-pager showing how we\'ve helped companies similar to yours?\n\nLet me know what works best for you.\n\nBest,',
    },
  ];

  return (
    <div data-testid="email-templates-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
            Email Templates
          </h1>
          <p className="text-zinc-500">Manage your outreach templates for high-value leads</p>
        </div>
        {canEdit && (
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button
                data-testid="add-template-button"
                className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Create Template
              </Button>
            </DialogTrigger>
            <DialogContent className="border-zinc-200 rounded-sm max-w-3xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
                  Create Email Template
                </DialogTitle>
                <DialogDescription className="text-zinc-500">
                  Create reusable email templates for your sales outreach
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name" className="text-sm font-medium text-zinc-950">
                    Template Name *
                  </Label>
                  <Input
                    id="name"
                    data-testid="template-name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    className="rounded-sm border-zinc-200"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="template_type" className="text-sm font-medium text-zinc-950">
                    Template Type *
                  </Label>
                  <select
                    id="template_type"
                    data-testid="template-type"
                    value={formData.template_type}
                    onChange={(e) => setFormData({ ...formData, template_type: e.target.value })}
                    required
                    className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                  >
                    <option value="proposal">Proposal</option>
                    <option value="demo_request">Demo Request</option>
                    <option value="follow_up">Follow Up</option>
                    <option value="thank_you">Thank You</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="subject" className="text-sm font-medium text-zinc-950">
                    Email Subject *
                  </Label>
                  <Input
                    id="subject"
                    data-testid="template-subject"
                    value={formData.subject}
                    onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                    placeholder="Use {first_name}, {company}, {job_title} for personalization"
                    required
                    className="rounded-sm border-zinc-200"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="body" className="text-sm font-medium text-zinc-950">
                    Email Body *
                  </Label>
                  <textarea
                    id="body"
                    data-testid="template-body"
                    value={formData.body}
                    onChange={(e) => setFormData({ ...formData, body: e.target.value })}
                    placeholder="Use {first_name}, {last_name}, {company}, {job_title} for personalization"
                    rows={10}
                    required
                    className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm font-mono"
                  />
                  <p className="text-xs text-zinc-500">
                    Available variables: {'{first_name}'}, {'{last_name}'}, {'{company}'},{' '}
                    {'{job_title}'}
                  </p>
                </div>

                <Button
                  type="submit"
                  data-testid="submit-template-button"
                  className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                >
                  Create Template
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Default Templates Section */}
      <div className="mb-8">
        <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500 mb-4">
          Suggested Templates
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {defaultTemplates.map((template, idx) => (
            <Card
              key={idx}
              className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors"
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-base font-semibold text-zinc-950">
                      {template.name}
                    </CardTitle>
                    <div className="text-xs uppercase tracking-wide text-zinc-500 mt-1">
                      {template.type}
                    </div>
                  </div>
                  <Button
                    onClick={() => copyTemplate(template)}
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 hover:bg-zinc-100 rounded-sm"
                  >
                    <Copy className="w-4 h-4" strokeWidth={1.5} />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                <div>
                  <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Subject</div>
                  <div className="text-sm text-zinc-950 font-medium">{template.subject}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Body</div>
                  <div className="text-xs text-zinc-600 line-clamp-4 whitespace-pre-line">
                    {template.body}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Custom Templates */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-zinc-500">Loading templates...</div>
        </div>
      ) : (
        <div>
          <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500 mb-4">
            Custom Templates ({templates.length})
          </h2>
          {templates.length === 0 ? (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="flex flex-col items-center justify-center h-48">
                <Mail className="w-12 h-12 text-zinc-300 mb-4" strokeWidth={1.5} />
                <p className="text-zinc-500 mb-4">No custom templates yet</p>
                {canEdit && (
                  <Button
                    onClick={() => setDialogOpen(true)}
                    className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                  >
                    <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                    Create Your First Template
                  </Button>
                )}
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {templates.map((template) => (
                <Card
                  key={template.id}
                  data-testid={`template-card-${template.id}`}
                  className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors"
                >
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div>
                        <CardTitle className="text-base font-semibold text-zinc-950">
                          {template.name}
                        </CardTitle>
                        <div className="text-xs uppercase tracking-wide text-zinc-500 mt-1">
                          {template.template_type}
                        </div>
                      </div>
                      <Button
                        onClick={() => copyTemplate(template)}
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 hover:bg-zinc-100 rounded-sm"
                      >
                        <Copy className="w-4 h-4" strokeWidth={1.5} />
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div>
                      <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">
                        Subject
                      </div>
                      <div className="text-sm text-zinc-950 font-medium">{template.subject}</div>
                    </div>
                    <div>
                      <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Body</div>
                      <div className="text-xs text-zinc-600 line-clamp-3 whitespace-pre-line">
                        {template.body}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default EmailTemplates;
