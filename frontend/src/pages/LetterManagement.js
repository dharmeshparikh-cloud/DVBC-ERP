import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { 
  FileText, Send, CheckCircle, Clock, Eye, Plus, Edit, Trash2,
  Mail, User, Building2, Calendar, DollarSign, History, FileSignature
} from 'lucide-react';
import { toast } from 'sonner';
import CompanyLetterhead, { HRSignatureBlock, LetterHeader } from '../components/CompanyLetterhead';

const LetterManagement = () => {
  const { user } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('offer-letters');
  const [stats, setStats] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [offerLetters, setOfferLetters] = useState([]);
  const [appointmentLetters, setAppointmentLetters] = useState([]);
  const [candidates, setCandidates] = useState([]);
  
  // Dialogs
  const [templateDialog, setTemplateDialog] = useState(false);
  const [offerDialog, setOfferDialog] = useState(false);
  const [appointmentDialog, setAppointmentDialog] = useState(false);
  const [previewDialog, setPreviewDialog] = useState(false);
  const [historyDialog, setHistoryDialog] = useState(false);
  
  // Form states
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [selectedLetter, setSelectedLetter] = useState(null);
  const [templateHistory, setTemplateHistory] = useState([]);
  
  const [templateForm, setTemplateForm] = useState({
    template_type: 'offer_letter',
    name: '',
    subject: '',
    body_content: '',
    is_default: false
  });
  
  const [offerForm, setOfferForm] = useState({
    candidate_id: '',
    template_id: '',
    designation: '',
    department: '',
    joining_date: '',
    salary_details: { gross_monthly: '', basic: '', hra: '', special_allowance: '' },
    hr_signature_text: user?.full_name || ''
  });

  const isAdmin = user?.role === 'admin';
  const isHR = ['hr_manager', 'hr_executive'].includes(user?.role);
  const canEdit = isAdmin || user?.role === 'hr_manager';

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      const [statsRes, templatesRes, offerRes, appointmentRes, candidatesRes] = await Promise.all([
        fetch(`${API}/letters/stats`, { headers }),
        fetch(`${API}/letters/templates`, { headers }),
        fetch(`${API}/letters/offer-letters`, { headers }),
        fetch(`${API}/letters/appointment-letters`, { headers }),
        fetch(`${API}/onboarding-candidates?status=verified`, { headers }).catch(() => ({ ok: false }))
      ]);

      if (statsRes.ok) setStats(await statsRes.json());
      if (templatesRes.ok) setTemplates(await templatesRes.json());
      if (offerRes.ok) setOfferLetters(await offerRes.json());
      if (appointmentRes.ok) setAppointmentLetters(await appointmentRes.json());
      if (candidatesRes.ok) {
        const data = await candidatesRes.json();
        setCandidates(Array.isArray(data) ? data : []);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTemplate = async () => {
    try {
      const token = localStorage.getItem('token');
      const url = editingTemplate 
        ? `${API}/letters/templates/${editingTemplate.id}`
        : `${API}/letters/templates`;
      
      const response = await fetch(url, {
        method: editingTemplate ? 'PUT' : 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(templateForm)
      });

      if (response.ok) {
        toast.success(`Template ${editingTemplate ? 'updated' : 'created'} successfully`);
        setTemplateDialog(false);
        setEditingTemplate(null);
        setTemplateForm({ template_type: 'offer_letter', name: '', subject: '', body_content: '', is_default: false });
        fetchData();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to save template');
      }
    } catch (error) {
      toast.error('Error saving template');
    }
  };

  const handleCreateOfferLetter = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/letters/offer-letters`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(offerForm)
      });

      if (response.ok) {
        const result = await response.json();
        toast.success('Offer letter created and sent!');
        setOfferDialog(false);
        setOfferForm({
          candidate_id: '',
          template_id: '',
          designation: '',
          department: '',
          joining_date: '',
          salary_details: { gross_monthly: '', basic: '', hra: '', special_allowance: '' },
          hr_signature_text: user?.full_name || ''
        });
        fetchData();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to create offer letter');
      }
    } catch (error) {
      toast.error('Error creating offer letter');
    }
  };

  const handleViewHistory = async (template) => {
    const token = localStorage.getItem('token');
    try {
      const response = await fetch(`${API}/letters/templates/${template.id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setTemplateHistory(data.history || []);
        setHistoryDialog(true);
      }
    } catch (error) {
      toast.error('Failed to load history');
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      pending_acceptance: 'bg-amber-100 text-amber-700',
      accepted: 'bg-green-100 text-green-700',
      rejected: 'bg-red-100 text-red-700',
      expired: 'bg-gray-100 text-gray-700'
    };
    return <Badge className={styles[status] || 'bg-gray-100'}>{status?.replace('_', ' ')}</Badge>;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="letter-management-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <FileText className="w-6 h-6 text-orange-500" />
            Letter Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage offer letters, appointment letters, and templates
          </p>
        </div>
        {canEdit && (
          <Button onClick={() => setTemplateDialog(true)} data-testid="create-template-btn">
            <Plus className="w-4 h-4 mr-2" />
            New Template
          </Button>
        )}
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-100 rounded-lg">
                  <Clock className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.offer_letters?.pending || 0}</p>
                  <p className="text-sm text-muted-foreground">Pending Offers</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.offer_letters?.accepted || 0}</p>
                  <p className="text-sm text-muted-foreground">Offers Accepted</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <FileSignature className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.appointment_letters?.pending || 0}</p>
                  <p className="text-sm text-muted-foreground">Pending Appointments</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <FileText className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.templates || 0}</p>
                  <p className="text-sm text-muted-foreground">Templates</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="offer-letters" className="flex items-center gap-2">
            <Mail className="w-4 h-4" />
            Offer Letters
            {stats?.offer_letters?.pending > 0 && (
              <Badge variant="destructive" className="ml-1">{stats.offer_letters.pending}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="appointment-letters" className="flex items-center gap-2">
            <FileSignature className="w-4 h-4" />
            Appointment Letters
          </TabsTrigger>
          <TabsTrigger value="templates" className="flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Templates
          </TabsTrigger>
        </TabsList>

        {/* Offer Letters Tab */}
        <TabsContent value="offer-letters" className="mt-4">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium">Offer Letters</h3>
            {canEdit && (
              <Button onClick={() => setOfferDialog(true)} data-testid="create-offer-btn">
                <Plus className="w-4 h-4 mr-2" />
                Create Offer Letter
              </Button>
            )}
          </div>
          
          {offerLetters.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Mail className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium">No Offer Letters</h3>
                <p className="text-muted-foreground mt-2">
                  Create an offer letter for verified candidates.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {offerLetters.map((letter) => (
                <Card key={letter.id} className="hover:border-orange-200 transition-colors">
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h4 className="font-medium">{letter.candidate_name}</h4>
                          {getStatusBadge(letter.status)}
                          {letter.employee_id_assigned && (
                            <Badge variant="outline">{letter.employee_id_assigned}</Badge>
                          )}
                        </div>
                        <div className="grid grid-cols-3 gap-4 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Building2 className="w-4 h-4" />
                            {letter.designation} - {letter.department}
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="w-4 h-4" />
                            Joining: {new Date(letter.joining_date).toLocaleDateString()}
                          </span>
                          <span className="flex items-center gap-1">
                            <Mail className="w-4 h-4" />
                            {letter.candidate_email}
                          </span>
                        </div>
                        {letter.accepted_at && (
                          <p className="text-xs text-green-600 mt-2">
                            Accepted on {new Date(letter.accepted_at).toLocaleString()} - {letter.acceptance_signature}
                          </p>
                        )}
                      </div>
                      <div className="flex gap-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => { setSelectedLetter(letter); setPreviewDialog(true); }}
                        >
                          <Eye className="w-4 h-4 mr-1" />
                          Preview
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Appointment Letters Tab */}
        <TabsContent value="appointment-letters" className="mt-4">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium">Appointment Letters</h3>
            {canEdit && (
              <Button onClick={() => setAppointmentDialog(true)} data-testid="create-appointment-btn">
                <Plus className="w-4 h-4 mr-2" />
                Create Appointment Letter
              </Button>
            )}
          </div>
          
          {appointmentLetters.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <FileSignature className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium">No Appointment Letters</h3>
                <p className="text-muted-foreground mt-2">
                  Appointment letters can be created after offer acceptance.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {appointmentLetters.map((letter) => (
                <Card key={letter.id} className="hover:border-orange-200 transition-colors">
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h4 className="font-medium">{letter.employee_name}</h4>
                          <Badge variant="outline">{letter.employee_code}</Badge>
                          {getStatusBadge(letter.status)}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          Sent on {new Date(letter.sent_at).toLocaleDateString()}
                        </p>
                        {letter.accepted_at && (
                          <p className="text-xs text-green-600 mt-2">
                            Accepted on {new Date(letter.accepted_at).toLocaleString()}
                          </p>
                        )}
                      </div>
                      <Button variant="outline" size="sm">
                        <Eye className="w-4 h-4 mr-1" />
                        Preview
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Templates Tab */}
        <TabsContent value="templates" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {templates.map((template) => (
              <Card key={template.id} className="hover:border-orange-200 transition-colors">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{template.name}</CardTitle>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="capitalize">
                        {template.template_type.replace('_', ' ')}
                      </Badge>
                      {template.is_default && (
                        <Badge className="bg-green-100 text-green-700">Default</Badge>
                      )}
                    </div>
                  </div>
                  <CardDescription>{template.subject}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">
                      v{template.version} • Last updated {new Date(template.updated_at).toLocaleDateString()}
                    </span>
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewHistory(template)}
                        data-testid={`view-history-${template.id}`}
                      >
                        <History className="w-4 h-4" />
                      </Button>
                      {canEdit && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setEditingTemplate(template);
                              setTemplateForm({
                                template_type: template.template_type,
                                name: template.name,
                                subject: template.subject,
                                body_content: template.body_content,
                                is_default: template.is_default
                              });
                              setTemplateDialog(true);
                            }}
                            data-testid={`edit-template-${template.id}`}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Template Dialog */}
      <Dialog open={templateDialog} onOpenChange={setTemplateDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingTemplate ? 'Edit Template' : 'Create New Template'}</DialogTitle>
            <DialogDescription>
              Create a letter template with placeholders like {'{{employee_name}}'}, {'{{designation}}'}, etc.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Template Type</Label>
                <Select 
                  value={templateForm.template_type} 
                  onValueChange={(v) => setTemplateForm({...templateForm, template_type: v})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="offer_letter">Offer Letter</SelectItem>
                    <SelectItem value="appointment_letter">Appointment Letter</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Template Name</Label>
                <Input 
                  value={templateForm.name}
                  onChange={(e) => setTemplateForm({...templateForm, name: e.target.value})}
                  placeholder="e.g., Standard Offer Letter"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Email Subject</Label>
              <Input 
                value={templateForm.subject}
                onChange={(e) => setTemplateForm({...templateForm, subject: e.target.value})}
                placeholder="e.g., Offer Letter - {{designation}} Position"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Letter Content (HTML supported)</Label>
              <Textarea 
                value={templateForm.body_content}
                onChange={(e) => setTemplateForm({...templateForm, body_content: e.target.value})}
                placeholder="Dear {{employee_name}},&#10;&#10;We are pleased to offer you..."
                className="min-h-[300px] font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">
                Available placeholders: {'{{employee_name}}'}, {'{{designation}}'}, {'{{department}}'}, {'{{joining_date}}'}, {'{{gross_salary}}'}, {'{{employee_id}}'}
              </p>
            </div>
            
            <div className="flex items-center gap-2">
              <input 
                type="checkbox"
                id="is_default"
                checked={templateForm.is_default}
                onChange={(e) => setTemplateForm({...templateForm, is_default: e.target.checked})}
                className="rounded"
              />
              <Label htmlFor="is_default">Set as default template for this type</Label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => { setTemplateDialog(false); setEditingTemplate(null); }}>
              Cancel
            </Button>
            <Button onClick={handleCreateTemplate}>
              {editingTemplate ? 'Update Template' : 'Create Template'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Offer Letter Dialog */}
      <Dialog open={offerDialog} onOpenChange={setOfferDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create Offer Letter</DialogTitle>
            <DialogDescription>
              Create and send an offer letter to a verified candidate
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Select Candidate</Label>
                <Select 
                  value={offerForm.candidate_id}
                  onValueChange={(v) => setOfferForm({...offerForm, candidate_id: v})}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select candidate" />
                  </SelectTrigger>
                  <SelectContent>
                    {candidates.map(c => (
                      <SelectItem key={c.id} value={c.id}>
                        {c.first_name} {c.last_name} - {c.email}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Template</Label>
                <Select 
                  value={offerForm.template_id}
                  onValueChange={(v) => setOfferForm({...offerForm, template_id: v})}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select template" />
                  </SelectTrigger>
                  <SelectContent>
                    {templates.filter(t => t.template_type === 'offer_letter').map(t => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.name} {t.is_default && '(Default)'}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Designation</Label>
                <Input 
                  value={offerForm.designation}
                  onChange={(e) => setOfferForm({...offerForm, designation: e.target.value})}
                  placeholder="e.g., Senior Consultant"
                />
              </div>
              <div className="space-y-2">
                <Label>Department</Label>
                <Input 
                  value={offerForm.department}
                  onChange={(e) => setOfferForm({...offerForm, department: e.target.value})}
                  placeholder="e.g., Technology"
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Joining Date</Label>
                <Input 
                  type="date"
                  value={offerForm.joining_date}
                  onChange={(e) => setOfferForm({...offerForm, joining_date: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>Gross Monthly Salary</Label>
                <Input 
                  type="number"
                  value={offerForm.salary_details.gross_monthly}
                  onChange={(e) => setOfferForm({
                    ...offerForm, 
                    salary_details: {...offerForm.salary_details, gross_monthly: e.target.value}
                  })}
                  placeholder="e.g., 75000"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>HR Signature (Text)</Label>
              <Input 
                value={offerForm.hr_signature_text}
                onChange={(e) => setOfferForm({...offerForm, hr_signature_text: e.target.value})}
                placeholder="HR Manager Name"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setOfferDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateOfferLetter}>
              <Send className="w-4 h-4 mr-2" />
              Create & Send Offer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* History Dialog */}
      <Dialog open={historyDialog} onOpenChange={setHistoryDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Template History</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 max-h-[400px] overflow-y-auto">
            {templateHistory.length === 0 ? (
              <p className="text-center text-muted-foreground py-4">No history available</p>
            ) : (
              templateHistory.map((entry, idx) => (
                <div key={idx} className="border rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="outline">v{entry.version}</Badge>
                    <span className="text-xs text-muted-foreground">
                      {new Date(entry.modified_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-sm font-medium">{entry.name}</p>
                  <p className="text-xs text-muted-foreground">
                    Modified by {entry.modified_by_name}
                  </p>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog open={previewDialog} onOpenChange={setPreviewDialog}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Letter Preview</DialogTitle>
          </DialogHeader>
          {selectedLetter && (
            <div className="scale-75 origin-top">
              <CompanyLetterhead>
                <LetterHeader 
                  date={selectedLetter.created_at}
                  reference={`DVBC/HR/${new Date().getFullYear()}/${selectedLetter.id?.slice(0,8)}`}
                  recipientName={selectedLetter.candidate_name || selectedLetter.employee_name}
                />
                <div className="letter-body">
                  <h2 className="text-xl font-bold text-center mb-6 underline">
                    {selectedLetter.letter_type === 'offer_letter' ? 'OFFER OF EMPLOYMENT' : 'APPOINTMENT LETTER'}
                  </h2>
                  <p className="mb-4">Dear {selectedLetter.candidate_name || selectedLetter.employee_name},</p>
                  <p className="mb-4">
                    We are pleased to offer you the position of <strong>{selectedLetter.designation}</strong> in 
                    our <strong>{selectedLetter.department}</strong> department.
                  </p>
                  {selectedLetter.joining_date && (
                    <p className="mb-4">
                      Your joining date will be <strong>{new Date(selectedLetter.joining_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' })}</strong>.
                    </p>
                  )}
                  {selectedLetter.salary_details?.gross_monthly && (
                    <p className="mb-4">
                      Your gross monthly salary will be <strong>₹{Number(selectedLetter.salary_details.gross_monthly).toLocaleString('en-IN')}</strong>.
                    </p>
                  )}
                </div>
                <HRSignatureBlock 
                  signatureText={selectedLetter.hr_signature_text}
                  hrName={selectedLetter.created_by_name}
                  hrDesignation="HR Manager"
                />
              </CompanyLetterhead>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default LetterManagement;
