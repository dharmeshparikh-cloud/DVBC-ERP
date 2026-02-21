import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { 
  Building2, Plus, Search, Eye, Edit2, Trash2, 
  User, Phone, Mail, MapPin, Calendar, DollarSign,
  Globe, Users as UsersIcon, TrendingUp
} from 'lucide-react';
import { toast } from 'sonner';

const INDUSTRIES = [
  'Technology', 'Healthcare', 'Finance', 'Manufacturing', 
  'Retail', 'Education', 'Real Estate', 'Consulting',
  'E-commerce', 'Logistics', 'Hospitality', 'Other'
];

const Clients = () => {
  const { user } = useContext(AuthContext);
  const [clients, setClients] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterIndustry, setFilterIndustry] = useState('');
  const [stats, setStats] = useState(null);

  // Dialogs
  const [createDialog, setCreateDialog] = useState(false);
  const [viewDialog, setViewDialog] = useState(false);
  const [editDialog, setEditDialog] = useState(false);
  const [contactDialog, setContactDialog] = useState(false);
  const [revenueDialog, setRevenueDialog] = useState(false);
  const [selectedClient, setSelectedClient] = useState(null);

  // Form data
  const [formData, setFormData] = useState({
    company_name: '',
    industry: '',
    location: '',
    city: '',
    state: '',
    country: 'India',
    address: '',
    website: '',
    business_start_date: '',
    sales_person_id: '',
    sales_person_name: '',
    notes: ''
  });

  // Contact form
  const [contactForm, setContactForm] = useState({
    name: '',
    designation: '',
    email: '',
    phone: '',
    is_primary: false
  });

  // Revenue form
  const [revenueForm, setRevenueForm] = useState({
    year: new Date().getFullYear(),
    quarter: '',
    amount: '',
    currency: 'INR',
    notes: ''
  });

  const canManage = ['admin', 'project_manager', 'sales_manager', 'executive', 'manager'].includes(user?.role);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [clientsRes, usersRes] = await Promise.all([
        axios.get(`${API}/clients`),
        axios.get(`${API}/users-with-roles`)
      ]);
      setClients(clientsRes.data || []);
      setUsers(usersRes.data || []);
      
      if (canManage) {
        try {
          const statsRes = await axios.get(`${API}/clients/stats/summary`);
          setStats(statsRes.data);
        } catch (e) {
          console.error('Error fetching stats:', e);
        }
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load clients');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateClient = async () => {
    if (!formData.company_name) {
      toast.error('Company name is required');
      return;
    }

    try {
      const payload = {
        ...formData,
        business_start_date: formData.business_start_date ? new Date(formData.business_start_date).toISOString() : null
      };

      await axios.post(`${API}/clients`, payload);
      toast.success('Client created successfully');
      setCreateDialog(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create client');
    }
  };

  const handleUpdateClient = async () => {
    if (!selectedClient) return;

    try {
      const payload = {
        ...formData,
        business_start_date: formData.business_start_date ? new Date(formData.business_start_date).toISOString() : null
      };

      await axios.patch(`${API}/clients/${selectedClient.id}`, payload);
      toast.success('Client updated successfully');
      setEditDialog(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update client');
    }
  };

  const handleDeactivateClient = async (clientId) => {
    if (!window.confirm('Are you sure you want to deactivate this client?')) return;

    try {
      await axios.delete(`${API}/clients/${clientId}`);
      toast.success('Client deactivated');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to deactivate client');
    }
  };

  const handleAddContact = async () => {
    if (!selectedClient || !contactForm.name) {
      toast.error('Contact name is required');
      return;
    }

    try {
      await axios.post(`${API}/clients/${selectedClient.id}/contacts`, contactForm);
      toast.success('Contact added');
      setContactDialog(false);
      setContactForm({ name: '', designation: '', email: '', phone: '', is_primary: false });
      
      // Refresh client data
      const res = await axios.get(`${API}/clients/${selectedClient.id}`);
      setSelectedClient(res.data);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add contact');
    }
  };

  const handleAddRevenue = async () => {
    if (!selectedClient || !revenueForm.amount) {
      toast.error('Amount is required');
      return;
    }

    try {
      await axios.post(`${API}/clients/${selectedClient.id}/revenue`, {
        ...revenueForm,
        amount: parseFloat(revenueForm.amount),
        quarter: revenueForm.quarter ? parseInt(revenueForm.quarter) : null
      });
      toast.success('Revenue record added');
      setRevenueDialog(false);
      setRevenueForm({ year: new Date().getFullYear(), quarter: '', amount: '', currency: 'INR', notes: '' });
      
      // Refresh client data
      const res = await axios.get(`${API}/clients/${selectedClient.id}`);
      setSelectedClient(res.data);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add revenue');
    }
  };

  const resetForm = () => {
    setFormData({
      company_name: '',
      industry: '',
      location: '',
      city: '',
      state: '',
      country: 'India',
      address: '',
      website: '',
      business_start_date: '',
      sales_person_id: '',
      sales_person_name: '',
      notes: ''
    });
  };

  const openEditDialog = (client) => {
    setSelectedClient(client);
    setFormData({
      company_name: client.company_name || '',
      industry: client.industry || '',
      location: client.location || '',
      city: client.city || '',
      state: client.state || '',
      country: client.country || 'India',
      address: client.address || '',
      website: client.website || '',
      business_start_date: client.business_start_date ? client.business_start_date.split('T')[0] : '',
      sales_person_id: client.sales_person_id || '',
      sales_person_name: client.sales_person_name || '',
      notes: client.notes || ''
    });
    setEditDialog(true);
  };

  const openViewDialog = async (client) => {
    try {
      const res = await axios.get(`${API}/clients/${client.id}`);
      setSelectedClient(res.data);
      setViewDialog(true);
    } catch (error) {
      toast.error('Failed to load client details');
    }
  };

  const filteredClients = clients.filter(client => {
    const matchesSearch = !searchTerm || 
      client.company_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      client.industry?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesIndustry = !filterIndustry || client.industry === filterIndustry;
    return matchesSearch && matchesIndustry;
  });

  const getTotalRevenue = (client) => {
    if (!client.revenue_history || client.revenue_history.length === 0) return 0;
    return client.revenue_history.reduce((sum, r) => sum + (r.amount || 0), 0);
  };

  if (loading) {
    return <div className="flex items-center justify-center h-96"><div className="text-zinc-500">Loading...</div></div>;
  }

  return (
    <div data-testid="clients-page">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
          Client Master
        </h1>
        <p className="text-zinc-500">Manage client information and relationships</p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase text-zinc-500">Total Clients</p>
                  <p className="text-2xl font-semibold text-zinc-950">{stats.total_clients}</p>
                </div>
                <Building2 className="w-8 h-8 text-zinc-300" />
              </div>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase text-zinc-500">Industries</p>
                  <p className="text-2xl font-semibold text-blue-600">{Object.keys(stats.by_industry).length}</p>
                </div>
                <Globe className="w-8 h-8 text-blue-200" />
              </div>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase text-zinc-500">Total Revenue</p>
                  <p className="text-2xl font-semibold text-emerald-600">₹{(stats.total_revenue / 100000).toFixed(1)}L</p>
                </div>
                <TrendingUp className="w-8 h-8 text-emerald-200" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
            <Input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search clients..."
              className="pl-10 rounded-sm"
            />
          </div>
          <select
            value={filterIndustry}
            onChange={(e) => setFilterIndustry(e.target.value)}
            className="h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
          >
            <option value="">All Industries</option>
            {INDUSTRIES.map(ind => (
              <option key={ind} value={ind}>{ind}</option>
            ))}
          </select>
        </div>
        
        {canManage && (
          <Button 
            onClick={() => { resetForm(); setCreateDialog(true); }}
            className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            data-testid="add-client-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Client
          </Button>
        )}
      </div>

      {/* Clients Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredClients.map(client => (
          <Card key={client.id} className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors" data-testid={`client-card-${client.id}`}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-zinc-100 flex items-center justify-center">
                    <Building2 className="w-5 h-5 text-zinc-500" />
                  </div>
                  <div>
                    <h3 className="font-medium text-zinc-900">{client.company_name}</h3>
                    {client.industry && (
                      <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded">{client.industry}</span>
                    )}
                  </div>
                </div>
              </div>
              
              <div className="space-y-2 text-sm text-zinc-600 mb-4">
                {client.location && (
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-zinc-400" />
                    <span>{client.city ? `${client.city}, ` : ''}{client.location}</span>
                  </div>
                )}
                {client.contacts?.length > 0 && (
                  <div className="flex items-center gap-2">
                    <UsersIcon className="w-4 h-4 text-zinc-400" />
                    <span>{client.contacts.length} contact(s)</span>
                  </div>
                )}
                {client.sales_person_name && (
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4 text-zinc-400" />
                    <span>Sales: {client.sales_person_name}</span>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-zinc-400" />
                  <span>Revenue: ₹{(getTotalRevenue(client) / 100000).toFixed(1)}L</span>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-3 border-t border-zinc-100">
                <Button onClick={() => openViewDialog(client)} variant="ghost" size="sm" className="flex-1 rounded-sm">
                  <Eye className="w-4 h-4 mr-1" />
                  View
                </Button>
                {canManage && (
                  <>
                    <Button onClick={() => openEditDialog(client)} variant="ghost" size="sm" className="flex-1 rounded-sm">
                      <Edit2 className="w-4 h-4 mr-1" />
                      Edit
                    </Button>
                    {user?.role === 'admin' && (
                      <Button onClick={() => handleDeactivateClient(client.id)} variant="ghost" size="sm" className="text-red-500 hover:text-red-600">
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredClients.length === 0 && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-12 text-center">
            <Building2 className="w-12 h-12 text-zinc-300 mx-auto mb-4" />
            <p className="text-zinc-500">
              {clients.length === 0 ? 'No clients yet. Add your first client.' : 'No clients match your search.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Create/Edit Client Dialog */}
      <Dialog open={createDialog || editDialog} onOpenChange={(open) => { setCreateDialog(false); setEditDialog(false); }}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              {editDialog ? 'Edit Client' : 'Add New Client'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-6">
            {/* Basic Info */}
            <div>
              <h4 className="font-medium text-zinc-950 mb-3">Company Information</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2 space-y-2">
                  <Label>Company Name *</Label>
                  <Input
                    value={formData.company_name}
                    onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                    placeholder="Acme Corporation"
                    className="rounded-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Industry</Label>
                  <select
                    value={formData.industry}
                    onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                    className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
                  >
                    <option value="">Select industry...</option>
                    {INDUSTRIES.map(ind => (
                      <option key={ind} value={ind}>{ind}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label>Website</Label>
                  <Input
                    value={formData.website}
                    onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                    placeholder="https://example.com"
                    className="rounded-sm"
                  />
                </div>
              </div>
            </div>

            {/* Location */}
            <div className="border-t border-zinc-100 pt-4">
              <h4 className="font-medium text-zinc-950 mb-3">Location</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>City</Label>
                  <Input
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    placeholder="Mumbai"
                    className="rounded-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label>State</Label>
                  <Input
                    value={formData.state}
                    onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                    placeholder="Maharashtra"
                    className="rounded-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Country</Label>
                  <Input
                    value={formData.country}
                    onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                    placeholder="India"
                    className="rounded-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Location/Region</Label>
                  <Input
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    placeholder="Western India"
                    className="rounded-sm"
                  />
                </div>
                <div className="col-span-2 space-y-2">
                  <Label>Full Address</Label>
                  <Input
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    placeholder="123 Business Park, Andheri East"
                    className="rounded-sm"
                  />
                </div>
              </div>
            </div>

            {/* Sales Info */}
            <div className="border-t border-zinc-100 pt-4">
              <h4 className="font-medium text-zinc-950 mb-3">Sales Information</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Business Start Date</Label>
                  <Input
                    type="date"
                    value={formData.business_start_date}
                    onChange={(e) => setFormData({ ...formData, business_start_date: e.target.value })}
                    className="rounded-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Sales Person</Label>
                  <select
                    value={formData.sales_person_id}
                    onChange={(e) => {
                      const sp = users.find(u => u.id === e.target.value);
                      setFormData({ 
                        ...formData, 
                        sales_person_id: e.target.value,
                        sales_person_name: sp?.full_name || ''
                      });
                    }}
                    className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
                  >
                    <option value="">Select sales person...</option>
                    {users.filter(u => ['executive', 'sales_manager', 'admin'].includes(u.role)).map(u => (
                      <option key={u.id} value={u.id}>{u.full_name}</option>
                    ))}
                  </select>
                </div>
                <div className="col-span-2 space-y-2">
                  <Label>Notes</Label>
                  <textarea
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    placeholder="Additional notes about this client..."
                    rows={3}
                    className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                  />
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-4 border-t border-zinc-100">
              <Button onClick={() => { setCreateDialog(false); setEditDialog(false); }} variant="outline" className="flex-1 rounded-sm">
                Cancel
              </Button>
              <Button 
                onClick={editDialog ? handleUpdateClient : handleCreateClient} 
                className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                {editDialog ? 'Update Client' : 'Create Client'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* View Client Dialog */}
      <Dialog open={viewDialog} onOpenChange={setViewDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Client Details
            </DialogTitle>
          </DialogHeader>
          {selectedClient && (
            <div className="space-y-6">
              {/* Company Info */}
              <div className="flex items-start gap-4">
                <div className="w-16 h-16 rounded-full bg-zinc-100 flex items-center justify-center">
                  <Building2 className="w-8 h-8 text-zinc-500" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-zinc-950">{selectedClient.company_name}</h2>
                  {selectedClient.industry && (
                    <span className="text-sm px-2 py-1 bg-blue-50 text-blue-700 rounded">{selectedClient.industry}</span>
                  )}
                  {selectedClient.website && (
                    <a href={selectedClient.website} target="_blank" rel="noopener noreferrer" className="block text-sm text-blue-600 mt-1">
                      {selectedClient.website}
                    </a>
                  )}
                </div>
              </div>

              {/* Details Grid */}
              <div className="grid grid-cols-2 gap-4 border-t border-zinc-100 pt-4">
                <div>
                  <Label className="text-xs text-zinc-500">Location</Label>
                  <p className="font-medium">{selectedClient.city ? `${selectedClient.city}, ` : ''}{selectedClient.state || ''} {selectedClient.country || ''}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Business Start Date</Label>
                  <p className="font-medium">{selectedClient.business_start_date ? new Date(selectedClient.business_start_date).toLocaleDateString() : '-'}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Sales Person</Label>
                  <p className="font-medium">{selectedClient.sales_person_name || '-'}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Total Revenue</Label>
                  <p className="font-medium text-emerald-600">₹{getTotalRevenue(selectedClient).toLocaleString()}</p>
                </div>
              </div>

              {/* Contacts Section */}
              <div className="border-t border-zinc-100 pt-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium text-zinc-950">Contacts (SPOCs)</h4>
                  {canManage && (
                    <Button 
                      onClick={() => setContactDialog(true)} 
                      variant="outline" 
                      size="sm" 
                      className="rounded-sm"
                    >
                      <Plus className="w-4 h-4 mr-1" />
                      Add Contact
                    </Button>
                  )}
                </div>
                {selectedClient.contacts?.length > 0 ? (
                  <div className="space-y-2">
                    {selectedClient.contacts.map((contact, idx) => (
                      <div key={idx} className="p-3 bg-zinc-50 rounded-sm flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{contact.name}</span>
                            {contact.is_primary && (
                              <span className="text-xs px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded">Primary</span>
                            )}
                          </div>
                          <div className="text-sm text-zinc-500">{contact.designation}</div>
                        </div>
                        <div className="text-sm text-zinc-600 space-y-1">
                          {contact.email && <div className="flex items-center gap-1"><Mail className="w-3 h-3" />{contact.email}</div>}
                          {contact.phone && <div className="flex items-center gap-1"><Phone className="w-3 h-3" />{contact.phone}</div>}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-zinc-400">No contacts added yet.</p>
                )}
              </div>

              {/* Revenue History Section */}
              <div className="border-t border-zinc-100 pt-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium text-zinc-950">Revenue History</h4>
                  {canManage && (
                    <Button 
                      onClick={() => setRevenueDialog(true)} 
                      variant="outline" 
                      size="sm" 
                      className="rounded-sm"
                    >
                      <Plus className="w-4 h-4 mr-1" />
                      Add Revenue
                    </Button>
                  )}
                </div>
                {selectedClient.revenue_history?.length > 0 ? (
                  <div className="space-y-2">
                    {selectedClient.revenue_history.map((rev, idx) => (
                      <div key={idx} className="p-3 bg-zinc-50 rounded-sm flex items-center justify-between">
                        <div>
                          <span className="font-medium">{rev.year}{rev.quarter ? ` Q${rev.quarter}` : ' (Annual)'}</span>
                          {rev.notes && <span className="text-sm text-zinc-500 ml-2">- {rev.notes}</span>}
                        </div>
                        <span className="font-semibold text-emerald-600">₹{rev.amount.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-zinc-400">No revenue records added yet.</p>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Add Contact Dialog */}
      <Dialog open={contactDialog} onOpenChange={setContactDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Add Contact</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input
                value={contactForm.name}
                onChange={(e) => setContactForm({ ...contactForm, name: e.target.value })}
                placeholder="John Doe"
                className="rounded-sm"
              />
            </div>
            <div className="space-y-2">
              <Label>Designation</Label>
              <Input
                value={contactForm.designation}
                onChange={(e) => setContactForm({ ...contactForm, designation: e.target.value })}
                placeholder="CEO"
                className="rounded-sm"
              />
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                type="email"
                value={contactForm.email}
                onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })}
                placeholder="john@example.com"
                className="rounded-sm"
              />
            </div>
            <div className="space-y-2">
              <Label>Phone</Label>
              <Input
                value={contactForm.phone}
                onChange={(e) => setContactForm({ ...contactForm, phone: e.target.value })}
                placeholder="+91 98765 43210"
                className="rounded-sm"
              />
            </div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={contactForm.is_primary}
                onChange={(e) => setContactForm({ ...contactForm, is_primary: e.target.checked })}
                className="rounded"
              />
              <span className="text-sm">Primary Contact</span>
            </label>
            <div className="flex gap-3 pt-4">
              <Button onClick={() => setContactDialog(false)} variant="outline" className="flex-1 rounded-sm">
                Cancel
              </Button>
              <Button onClick={handleAddContact} className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                Add Contact
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Add Revenue Dialog */}
      <Dialog open={revenueDialog} onOpenChange={setRevenueDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Add Revenue Record</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Year *</Label>
                <Input
                  type="number"
                  value={revenueForm.year}
                  onChange={(e) => setRevenueForm({ ...revenueForm, year: parseInt(e.target.value) })}
                  placeholder="2024"
                  className="rounded-sm"
                />
              </div>
              <div className="space-y-2">
                <Label>Quarter (optional)</Label>
                <select
                  value={revenueForm.quarter}
                  onChange={(e) => setRevenueForm({ ...revenueForm, quarter: e.target.value })}
                  className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
                >
                  <option value="">Annual</option>
                  <option value="1">Q1</option>
                  <option value="2">Q2</option>
                  <option value="3">Q3</option>
                  <option value="4">Q4</option>
                </select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Amount (₹) *</Label>
              <Input
                type="number"
                value={revenueForm.amount}
                onChange={(e) => setRevenueForm({ ...revenueForm, amount: e.target.value })}
                placeholder="1000000"
                className="rounded-sm"
              />
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Input
                value={revenueForm.notes}
                onChange={(e) => setRevenueForm({ ...revenueForm, notes: e.target.value })}
                placeholder="Consulting project"
                className="rounded-sm"
              />
            </div>
            <div className="flex gap-3 pt-4">
              <Button onClick={() => setRevenueDialog(false)} variant="outline" className="flex-1 rounded-sm">
                Cancel
              </Button>
              <Button onClick={handleAddRevenue} className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                Add Revenue
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Clients;
