import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Users, Plus, Briefcase, TrendingUp, Search, UserCheck, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { formatINR } from '../utils/currency';

const Consultants = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [consultants, setConsultants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    department: ''
  });

  useEffect(() => {
    fetchConsultants();
  }, []);

  const fetchConsultants = async () => {
    try {
      const response = await axios.get(`${API}/consultants`);
      setConsultants(response.data);
    } catch (error) {
      toast.error('Failed to fetch consultants');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/consultants`, {
        ...formData,
        role: 'consultant'
      });
      toast.success('Consultant created successfully');
      setDialogOpen(false);
      setFormData({ email: '', password: '', full_name: '', department: '' });
      fetchConsultants();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create consultant');
    }
  };

  const getBandwidthColor = (percentage) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-yellow-500';
    return 'bg-emerald-500';
  };

  const filteredConsultants = consultants.filter(c => 
    c.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const isAdmin = user?.role === 'admin';

  return (
    <div data-testid="consultants-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
            Consultants
          </h1>
          <p className="text-zinc-500">Manage consultants and their project assignments</p>
        </div>
        {isAdmin && (
          <Button
            onClick={() => setDialogOpen(true)}
            data-testid="add-consultant-btn"
            className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
          >
            <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
            Add Consultant
          </Button>
        )}
      </div>

      {/* Search */}
      <div className="mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-zinc-400" strokeWidth={1.5} />
          <Input
            placeholder="Search consultants..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 rounded-sm border-zinc-200"
          />
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-zinc-500 uppercase tracking-wide">Total Consultants</div>
                <div className="text-2xl font-semibold text-zinc-950">{consultants.length}</div>
              </div>
              <Users className="w-8 h-8 text-zinc-300" strokeWidth={1} />
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-zinc-500 uppercase tracking-wide">Available</div>
                <div className="text-2xl font-semibold text-emerald-600">
                  {consultants.filter(c => c.stats?.available_slots > 0).length}
                </div>
              </div>
              <UserCheck className="w-8 h-8 text-emerald-200" strokeWidth={1} />
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-zinc-500 uppercase tracking-wide">At Capacity</div>
                <div className="text-2xl font-semibold text-red-600">
                  {consultants.filter(c => c.stats?.available_slots === 0).length}
                </div>
              </div>
              <AlertCircle className="w-8 h-8 text-red-200" strokeWidth={1} />
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-zinc-500 uppercase tracking-wide">Total Project Value</div>
                <div className="text-2xl font-semibold text-zinc-950">
                  {formatINR(consultants.reduce((sum, c) => sum + (c.stats?.total_project_value || 0), 0), false)}
                </div>
              </div>
              <TrendingUp className="w-8 h-8 text-zinc-300" strokeWidth={1} />
            </div>
          </CardContent>
        </Card>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-zinc-500">Loading consultants...</div>
        </div>
      ) : filteredConsultants.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-64">
            <Users className="w-12 h-12 text-zinc-300 mb-4" strokeWidth={1} />
            <p className="text-zinc-500 mb-4">
              {searchQuery ? 'No consultants match your search' : 'No consultants registered yet'}
            </p>
            {isAdmin && !searchQuery && (
              <Button
                onClick={() => setDialogOpen(true)}
                className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                Add First Consultant
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {/* Table Header */}
          <div className="hidden md:grid grid-cols-12 gap-4 px-4 py-2 bg-zinc-50 rounded-sm text-xs font-medium uppercase tracking-wide text-zinc-500">
            <div className="col-span-3">Consultant</div>
            <div className="col-span-2">Projects</div>
            <div className="col-span-2">Meetings</div>
            <div className="col-span-2">Project Value</div>
            <div className="col-span-2">Bandwidth</div>
            <div className="col-span-1">Actions</div>
          </div>

          {/* Consultant Rows */}
          {filteredConsultants.map((consultant) => (
            <Card
              key={consultant.id}
              data-testid={`consultant-card-${consultant.id}`}
              className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors"
            >
              <CardContent className="py-4">
                <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
                  {/* Name & Email */}
                  <div className="col-span-3">
                    <div className="font-medium text-zinc-950">{consultant.full_name}</div>
                    <div className="text-sm text-zinc-500">{consultant.email}</div>
                    {consultant.profile?.preferred_mode && (
                      <span className="inline-block mt-1 px-2 py-0.5 text-xs bg-zinc-100 text-zinc-600 rounded-sm capitalize">
                        {consultant.profile.preferred_mode}
                      </span>
                    )}
                  </div>

                  {/* Projects */}
                  <div className="col-span-2">
                    <div className="flex items-center gap-2">
                      <Briefcase className="w-4 h-4 text-zinc-400" strokeWidth={1.5} />
                      <span className="font-semibold text-zinc-950">
                        {consultant.stats?.total_projects || 0}
                      </span>
                      <span className="text-zinc-500">/ {consultant.stats?.max_projects || 8}</span>
                    </div>
                    <div className="text-xs text-zinc-500 mt-1">
                      {consultant.stats?.available_slots || 0} slots available
                    </div>
                  </div>

                  {/* Meetings */}
                  <div className="col-span-2">
                    <div className="text-sm">
                      <span className="font-semibold text-zinc-950">
                        {consultant.stats?.total_meetings_completed || 0}
                      </span>
                      <span className="text-zinc-500">
                        {' / '}{consultant.stats?.total_meetings_committed || 0}
                      </span>
                    </div>
                    <div className="text-xs text-zinc-500">completed / committed</div>
                  </div>

                  {/* Project Value */}
                  <div className="col-span-2">
                    <div className="font-semibold text-zinc-950">
                      {formatINR(consultant.stats?.total_project_value || 0, false)}
                    </div>
                    <div className="text-xs text-zinc-500">total value</div>
                  </div>

                  {/* Bandwidth Bar */}
                  <div className="col-span-2">
                    <div className="flex items-center gap-2 mb-1">
                      <div className="flex-1 h-2 bg-zinc-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${getBandwidthColor(consultant.stats?.bandwidth_percentage || 0)} transition-all`}
                          style={{ width: `${consultant.stats?.bandwidth_percentage || 0}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-zinc-600">
                        {consultant.stats?.bandwidth_percentage || 0}%
                      </span>
                    </div>
                    <div className="text-xs text-zinc-500">capacity used</div>
                  </div>

                  {/* Actions */}
                  <div className="col-span-1">
                    <Button
                      onClick={() => navigate(`/consultants/${consultant.id}`)}
                      variant="ghost"
                      size="sm"
                      className="text-zinc-600 hover:text-zinc-950"
                    >
                      View
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Add Consultant Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Add New Consultant
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Create a consultant account. They will be able to login and view assigned projects.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Full Name *</Label>
              <Input
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                required
                placeholder="John Smith"
                className="rounded-sm border-zinc-200"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Email *</Label>
              <Input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                placeholder="consultant@company.com"
                className="rounded-sm border-zinc-200"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Password *</Label>
              <Input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
                placeholder="••••••••"
                className="rounded-sm border-zinc-200"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Department</Label>
              <Input
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                placeholder="e.g., Operations, HR, Sales"
                className="rounded-sm border-zinc-200"
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              Create Consultant
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Consultants;
