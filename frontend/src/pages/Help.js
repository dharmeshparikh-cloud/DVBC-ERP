import React from 'react';
import { Card, CardContent } from '../components/ui/card';
import { 
  HelpCircle, 
  Mail, 
  Phone, 
  MessageCircle, 
  BookOpen,
  ExternalLink,
  FileText,
  Video
} from 'lucide-react';
import { Button } from '../components/ui/button';

const Help = () => {
  const supportOptions = [
    {
      title: 'Documentation',
      description: 'Browse our comprehensive guides and tutorials',
      icon: BookOpen,
      action: 'View Docs',
      href: '/tutorials',
    },
    {
      title: 'Email Support',
      description: 'Get help from our support team via email',
      icon: Mail,
      action: 'Send Email',
      href: 'mailto:support@dvconsulting.co.in',
    },
    {
      title: 'FAQs',
      description: 'Find answers to frequently asked questions',
      icon: FileText,
      action: 'View FAQs',
      href: '#faqs',
    },
  ];

  const faqs = [
    {
      question: 'How do I reset my password?',
      answer: 'Click on your profile icon in the sidebar, then select "Account settings" to change your password.',
    },
    {
      question: 'How do I apply for leave?',
      answer: 'Navigate to "My Leaves" in the sidebar under "My Workspace", then click "Apply Leave" button.',
    },
    {
      question: 'How do I submit expenses?',
      answer: 'Go to "My Expenses" in the sidebar, click "New Expense" and fill out the expense form with receipts.',
    },
    {
      question: 'How do I check my attendance?',
      answer: 'Navigate to "My Attendance" in the sidebar to view your attendance history and check-in/out times.',
    },
    {
      question: 'Who do I contact for HR issues?',
      answer: 'For HR-related queries, please email hr@dvconsulting.co.in or contact your HR manager directly.',
    },
  ];

  return (
    <div className="space-y-8" data-testid="help-page">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-900 mb-2">Help & Support</h1>
        <p className="text-zinc-500">Get assistance with using NETRA ERP</p>
      </div>

      {/* Support Options */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {supportOptions.map((option) => {
          const Icon = option.icon;
          return (
            <Card key={option.title} className="border-zinc-200 hover:border-zinc-400 transition-colors">
              <CardContent className="p-6">
                <div className="w-12 h-12 rounded-lg bg-emerald-50 flex items-center justify-center mb-4">
                  <Icon className="w-6 h-6 text-emerald-600" />
                </div>
                <h3 className="font-semibold text-zinc-900 mb-2">{option.title}</h3>
                <p className="text-sm text-zinc-500 mb-4">{option.description}</p>
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="w-full"
                  onClick={() => {
                    if (option.href.startsWith('mailto:')) {
                      window.location.href = option.href;
                    } else if (option.href.startsWith('#')) {
                      document.getElementById('faqs')?.scrollIntoView({ behavior: 'smooth' });
                    } else {
                      window.location.href = option.href;
                    }
                  }}
                >
                  {option.action}
                  <ExternalLink className="w-4 h-4 ml-2" />
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* FAQs Section */}
      <div id="faqs">
        <h2 className="text-xl font-semibold text-zinc-900 mb-4">Frequently Asked Questions</h2>
        <div className="space-y-4">
          {faqs.map((faq, index) => (
            <Card key={index} className="border-zinc-200">
              <CardContent className="p-5">
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <HelpCircle className="w-4 h-4 text-emerald-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-zinc-900 mb-1">{faq.question}</h3>
                    <p className="text-sm text-zinc-500">{faq.answer}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Contact Info */}
      <Card className="border-zinc-200 bg-zinc-50">
        <CardContent className="p-6">
          <h3 className="font-semibold text-zinc-900 mb-4">Need More Help?</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-zinc-500" />
              <div>
                <p className="text-sm text-zinc-500">Email</p>
                <p className="font-medium text-zinc-900">support@dvconsulting.co.in</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Phone className="w-5 h-5 text-zinc-500" />
              <div>
                <p className="text-sm text-zinc-500">Phone</p>
                <p className="font-medium text-zinc-900">+91 9876 543210</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Help;
