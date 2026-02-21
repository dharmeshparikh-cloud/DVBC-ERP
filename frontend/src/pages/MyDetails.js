import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { AuthContext, API } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { 
  User, Mail, Phone, MapPin, Building2, Briefcase, Calendar,
  CreditCard, Edit2, Save, X, Clock, CheckCircle, AlertCircle,
  FileText, Upload, Send, UserCog, Shield
} from 'lucide-react';

const MyDetails = () => {
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Edit states
  const [editSection, setEditSection] = useState(null);
  const [editData, setEditData] = useState({});
  const [changeReason, setChangeReason] = useState('');
  
  // Pending requests
  const [pendingRequests, setPendingRequests] = useState([]);
  
  // Document upload
  const [uploadingDoc, setUploadingDoc] = useState(false);

  useEffect(() => {
    fetchProfile();
    fetchPendingRequests();
  }, []);

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/my/profile`);
      setProfile(res.data);
    } catch (err) {
      toast.error('Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  const fetchPendingRequests = async () => {
    try {
      const res = await axios.get(`${API}/my/change-requests`);
      setPendingRequests(res.data || []);
    } catch (err) {
      console.error('Failed to fetch pending requests');
    }
  };

  const openEditDialog = (section, data) => {
    setEditSection(section);
    setEditData({ ...data });
    setChangeReason('');
  };

  const closeEditDialog = () => {
    setEditSection(null);
    setEditData({});
    setChangeReason('');
  };

  const submitChangeRequest = async () => {
    if (!changeReason.trim()) {
      toast.error('Please provide a reason for the change');
      return;
    }

    setSaving(true);
    try {
      await axios.post(`${API}/my/change-request`, {
        section: editSection,
        changes: editData,
        reason: changeReason
      });
      toast.success('Change request submitted for HR approval');
      closeEditDialog();
      fetchPendingRequests();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit change request');
    } finally {
      setSaving(false);
    }
  };

  const getSectionIcon = (section) => {
    switch (section) {
      case 'personal': return User;
      case 'contact': return Phone;
      case 'address': return MapPin;
      case 'bank': return CreditCard;
      case 'emergency': return Shield;
      default: return FileText;
    }
  };

  const hasPendingRequest = (section) => {
    return pendingRequests.some(r => r.section === section && r.status === 'pending');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-12 h-12 mx-auto text-zinc-300 mb-4" />
        <p className="text-zinc-500">Unable to load profile</p>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <UserCog className="w-6 h-6 text-orange-500" />
            My Details
          </h1>
          <p className={`text-sm mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
            View and request changes to your profile information
          </p>
        </div>
      </div>

      {/* Pending Requests Banner */}
      {pendingRequests.length > 0 && (
        <div className={`p-4 rounded-lg border ${isDark ? 'bg-amber-900/20 border-amber-700' : 'bg-amber-50 border-amber-200'}`}>
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-5 h-5 text-amber-500" />
            <span className={`font-medium ${isDark ? 'text-amber-300' : 'text-amber-700'}`}>
              Pending Change Requests
            </span>
          </div>
          <div className="space-y-2">
            {pendingRequests.filter(r => r.status === 'pending').map(req => {
              const Icon = getSectionIcon(req.section);
              return (
                <div key={req.id} className={`flex items-center gap-2 text-sm ${isDark ? 'text-amber-200' : 'text-amber-600'}`}>
                  <Icon className="w-4 h-4" />
                  <span className="capitalize">{req.section.replace('_', ' ')}</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-amber-200 text-amber-800">
                    Awaiting HR Approval
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Personal Information */}
        <Card className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <User className="w-5 h-5 text-blue-500" />
                Personal Information
              </CardTitle>
              <CardDescription>Basic personal details (Read-only)</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-zinc-500">Full Name</Label>
                <p className="font-medium">{profile.first_name} {profile.last_name}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Employee ID</Label>
                <p className="font-medium">{profile.employee_id}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Date of Birth</Label>
                <p className="font-medium">{profile.date_of_birth || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Gender</Label>
                <p className="font-medium capitalize">{profile.gender || 'Not set'}</p>
              </div>
            </div>
            <p className="text-xs text-zinc-500 mt-2">
              To change personal details, contact HR directly.
            </p>
          </CardContent>
        </Card>

        {/* Contact Information */}
        <Card className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Phone className="w-5 h-5 text-green-500" />
                Contact Information
              </CardTitle>
              <CardDescription>Phone and email details</CardDescription>
            </div>
            {!hasPendingRequest('contact') && (
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => openEditDialog('contact', {
                  personal_email: profile.personal_email,
                  phone: profile.phone,
                  alternate_phone: profile.alternate_phone
                })}
              >
                <Edit2 className="w-4 h-4 mr-1" /> Edit
              </Button>
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-zinc-500">Work Email</Label>
                <p className="font-medium">{profile.email}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Personal Email</Label>
                <p className="font-medium">{profile.personal_email || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Phone</Label>
                <p className="font-medium">{profile.phone || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Alternate Phone</Label>
                <p className="font-medium">{profile.alternate_phone || 'Not set'}</p>
              </div>
            </div>
            {hasPendingRequest('contact') && (
              <p className="text-xs text-amber-500 flex items-center gap-1">
                <Clock className="w-3 h-3" /> Change request pending approval
              </p>
            )}
          </CardContent>
        </Card>

        {/* Address */}
        <Card className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <MapPin className="w-5 h-5 text-red-500" />
                Address
              </CardTitle>
              <CardDescription>Current and permanent address</CardDescription>
            </div>
            {!hasPendingRequest('address') && (
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => openEditDialog('address', {
                  current_address: profile.current_address || '',
                  permanent_address: profile.permanent_address || '',
                  city: profile.city || '',
                  state: profile.state || '',
                  pincode: profile.pincode || ''
                })}
              >
                <Edit2 className="w-4 h-4 mr-1" /> Edit
              </Button>
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <Label className="text-xs text-zinc-500">Current Address</Label>
              <p className="font-medium">{profile.current_address || 'Not set'}</p>
            </div>
            <div>
              <Label className="text-xs text-zinc-500">Permanent Address</Label>
              <p className="font-medium">{profile.permanent_address || 'Not set'}</p>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label className="text-xs text-zinc-500">City</Label>
                <p className="font-medium">{profile.city || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">State</Label>
                <p className="font-medium">{profile.state || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Pincode</Label>
                <p className="font-medium">{profile.pincode || 'Not set'}</p>
              </div>
            </div>
            {hasPendingRequest('address') && (
              <p className="text-xs text-amber-500 flex items-center gap-1">
                <Clock className="w-3 h-3" /> Change request pending approval
              </p>
            )}
          </CardContent>
        </Card>

        {/* Bank Details */}
        <Card className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <CreditCard className="w-5 h-5 text-purple-500" />
                Bank Details
              </CardTitle>
              <CardDescription>Salary account information</CardDescription>
            </div>
            {!hasPendingRequest('bank') && (
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => openEditDialog('bank', {
                  bank_name: profile.bank_name || '',
                  account_number: profile.account_number || '',
                  ifsc_code: profile.ifsc_code || '',
                  branch: profile.bank_branch || ''
                })}
              >
                <Edit2 className="w-4 h-4 mr-1" /> Edit
              </Button>
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-zinc-500">Bank Name</Label>
                <p className="font-medium">{profile.bank_name || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Branch</Label>
                <p className="font-medium">{profile.bank_branch || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Account Number</Label>
                <p className="font-medium">
                  {profile.account_number 
                    ? `****${profile.account_number.slice(-4)}` 
                    : 'Not set'
                  }
                </p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">IFSC Code</Label>
                <p className="font-medium">{profile.ifsc_code || 'Not set'}</p>
              </div>
            </div>
            {hasPendingRequest('bank') && (
              <p className="text-xs text-amber-500 flex items-center gap-1">
                <Clock className="w-3 h-3" /> Change request pending approval
              </p>
            )}
          </CardContent>
        </Card>

        {/* Emergency Contact */}
        <Card className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Shield className="w-5 h-5 text-orange-500" />
                Emergency Contact
              </CardTitle>
              <CardDescription>Emergency contact details</CardDescription>
            </div>
            {!hasPendingRequest('emergency') && (
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => openEditDialog('emergency', {
                  emergency_contact_name: profile.emergency_contact_name || '',
                  emergency_contact_phone: profile.emergency_contact_phone || '',
                  emergency_contact_relation: profile.emergency_contact_relation || ''
                })}
              >
                <Edit2 className="w-4 h-4 mr-1" /> Edit
              </Button>
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-zinc-500">Contact Name</Label>
                <p className="font-medium">{profile.emergency_contact_name || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Relation</Label>
                <p className="font-medium capitalize">{profile.emergency_contact_relation || 'Not set'}</p>
              </div>
              <div className="col-span-2">
                <Label className="text-xs text-zinc-500">Phone</Label>
                <p className="font-medium">{profile.emergency_contact_phone || 'Not set'}</p>
              </div>
            </div>
            {hasPendingRequest('emergency') && (
              <p className="text-xs text-amber-500 flex items-center gap-1">
                <Clock className="w-3 h-3" /> Change request pending approval
              </p>
            )}
          </CardContent>
        </Card>

        {/* Employment Information (Read-only) */}
        <Card className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Briefcase className="w-5 h-5 text-teal-500" />
              Employment Information
            </CardTitle>
            <CardDescription>Job details (Read-only)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-zinc-500">Department</Label>
                <p className="font-medium">{profile.department || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Designation</Label>
                <p className="font-medium">{profile.designation || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Date of Joining</Label>
                <p className="font-medium">{profile.date_of_joining || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Reporting Manager</Label>
                <p className="font-medium">{profile.reporting_manager_name || 'Not set'}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Edit Dialog */}
      <Dialog open={!!editSection} onOpenChange={() => closeEditDialog()}>
        <DialogContent className={`max-w-lg ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {editSection && React.createElement(getSectionIcon(editSection), { className: 'w-5 h-5 text-orange-500' })}
              Edit {editSection?.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </DialogTitle>
            <DialogDescription>
              Your changes will be submitted for HR approval
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Contact Section */}
            {editSection === 'contact' && (
              <>
                <div>
                  <Label>Personal Email</Label>
                  <Input
                    type="email"
                    value={editData.personal_email || ''}
                    onChange={e => setEditData({...editData, personal_email: e.target.value})}
                    placeholder="personal@email.com"
                  />
                </div>
                <div>
                  <Label>Phone Number</Label>
                  <Input
                    value={editData.phone || ''}
                    onChange={e => setEditData({...editData, phone: e.target.value})}
                    placeholder="+91 98765 43210"
                  />
                </div>
                <div>
                  <Label>Alternate Phone</Label>
                  <Input
                    value={editData.alternate_phone || ''}
                    onChange={e => setEditData({...editData, alternate_phone: e.target.value})}
                    placeholder="+91 98765 43210"
                  />
                </div>
              </>
            )}

            {/* Address Section */}
            {editSection === 'address' && (
              <>
                <div>
                  <Label>Current Address</Label>
                  <Textarea
                    value={editData.current_address || ''}
                    onChange={e => setEditData({...editData, current_address: e.target.value})}
                    rows={2}
                  />
                </div>
                <div>
                  <Label>Permanent Address</Label>
                  <Textarea
                    value={editData.permanent_address || ''}
                    onChange={e => setEditData({...editData, permanent_address: e.target.value})}
                    rows={2}
                  />
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <Label>City</Label>
                    <Input
                      value={editData.city || ''}
                      onChange={e => setEditData({...editData, city: e.target.value})}
                    />
                  </div>
                  <div>
                    <Label>State</Label>
                    <Input
                      value={editData.state || ''}
                      onChange={e => setEditData({...editData, state: e.target.value})}
                    />
                  </div>
                  <div>
                    <Label>Pincode</Label>
                    <Input
                      value={editData.pincode || ''}
                      onChange={e => setEditData({...editData, pincode: e.target.value})}
                    />
                  </div>
                </div>
              </>
            )}

            {/* Bank Section */}
            {editSection === 'bank' && (
              <>
                <div>
                  <Label>Bank Name</Label>
                  <Input
                    value={editData.bank_name || ''}
                    onChange={e => setEditData({...editData, bank_name: e.target.value})}
                    placeholder="HDFC Bank"
                  />
                </div>
                <div>
                  <Label>Branch</Label>
                  <Input
                    value={editData.branch || ''}
                    onChange={e => setEditData({...editData, branch: e.target.value})}
                    placeholder="Mumbai Main Branch"
                  />
                </div>
                <div>
                  <Label>Account Number</Label>
                  <Input
                    value={editData.account_number || ''}
                    onChange={e => setEditData({...editData, account_number: e.target.value})}
                    placeholder="1234567890123"
                  />
                </div>
                <div>
                  <Label>IFSC Code</Label>
                  <Input
                    value={editData.ifsc_code || ''}
                    onChange={e => setEditData({...editData, ifsc_code: e.target.value.toUpperCase()})}
                    placeholder="HDFC0001234"
                  />
                </div>
              </>
            )}

            {/* Emergency Contact Section */}
            {editSection === 'emergency' && (
              <>
                <div>
                  <Label>Contact Name</Label>
                  <Input
                    value={editData.emergency_contact_name || ''}
                    onChange={e => setEditData({...editData, emergency_contact_name: e.target.value})}
                    placeholder="John Doe"
                  />
                </div>
                <div>
                  <Label>Relation</Label>
                  <Input
                    value={editData.emergency_contact_relation || ''}
                    onChange={e => setEditData({...editData, emergency_contact_relation: e.target.value})}
                    placeholder="Spouse / Parent / Sibling"
                  />
                </div>
                <div>
                  <Label>Phone Number</Label>
                  <Input
                    value={editData.emergency_contact_phone || ''}
                    onChange={e => setEditData({...editData, emergency_contact_phone: e.target.value})}
                    placeholder="+91 98765 43210"
                  />
                </div>
              </>
            )}

            {/* Reason for change */}
            <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
              <Label className="text-orange-600">Reason for Change *</Label>
              <Textarea
                value={changeReason}
                onChange={e => setChangeReason(e.target.value)}
                placeholder="Please provide a reason for this change request..."
                rows={2}
                className="mt-2"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={closeEditDialog}>
              Cancel
            </Button>
            <Button 
              onClick={submitChangeRequest}
              disabled={saving}
              className="bg-orange-500 hover:bg-orange-600"
            >
              {saving ? 'Submitting...' : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Submit for Approval
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MyDetails;
