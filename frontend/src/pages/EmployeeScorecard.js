import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import {
  Users, UserCheck, UserX, Shield, Building2, Briefcase,
  Search, Eye, Clock, FileText, DollarSign, Calendar,
  ChevronRight, TrendingUp, MapPin, Mail, Phone
} from 'lucide-react';
import { toast } from 'sonner';

const EmployeeScorecard = () => {
  const { user } = useContext(AuthContext);
  const [stats, setStats] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [employeeTimeline, setEmployeeTimeline] = useState(null);
  const [linkedRecords, setLinkedRecords] = useState(null);
  const [showDetailDialog, setShowDetailDialog] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, employeesRes] = await Promise.all([
        axios.get(`${API}/employees/stats/summary`),
        axios.get(`${API}/employees`)
      ]);
      setStats(statsRes.data);
      setEmployees(employeesRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load employee data');
    } finally {
      setLoading(false);
    }
  };

  const handleViewEmployee = async (employee) => {
    setSelectedEmployee(employee);
    setShowDetailDialog(true);
    
    try {
      const [timelineRes, linkedRes] = await Promise.all([
        axios.get(`${API}/employees/${employee.id}/timeline`),
        axios.get(`${API}/employees/${employee.id}/linked-records`)
      ]);
      setEmployeeTimeline(timelineRes.data);
      setLinkedRecords(linkedRes.data);
    } catch (error) {
      console.error('Failed to fetch employee details:', error);
    }
  };

  const filteredEmployees = employees.filter(emp => {
    const searchLower = searchTerm.toLowerCase();
    return (
      `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(searchLower) ||
      emp.employee_id?.toLowerCase().includes(searchLower) ||
      emp.email?.toLowerCase().includes(searchLower) ||
      emp.department?.toLowerCase().includes(searchLower)
    );
  });

  const eventIcons = {
    hired: <UserCheck className="w-4 h-4 text-emerald-500" />,
    access_granted: <Shield className="w-4 h-4 text-blue-500" />,
    offer_letter: <FileText className="w-4 h-4 text-purple-500" />,
    leave_request: <Calendar className="w-4 h-4 text-amber-500" />,
    expense: <DollarSign className="w-4 h-4 text-green-500" />,
    project_assignment: <Briefcase className="w-4 h-4 text-indigo-500" />,
    salary_slip: <DollarSign className="w-4 h-4 text-emerald-500" />,
    terminated: <UserX className="w-4 h-4 text-red-500" />,
    first_attendance: <Clock className="w-4 h-4 text-blue-500" />
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="employee-scorecard">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-zinc-900">Employee Scorecard</h1>
        <p className="text-sm text-zinc-500">Track employees from hiring to retiring</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Total</p>
                <p className="text-2xl font-bold text-zinc-900">{stats?.total || 0}</p>
              </div>
              <Users className="w-8 h-8 text-zinc-300" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Active</p>
                <p className="text-2xl font-bold text-emerald-600">{stats?.active || 0}</p>
              </div>
              <UserCheck className="w-8 h-8 text-emerald-300" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">With Access</p>
                <p className="text-2xl font-bold text-blue-600">{stats?.with_portal_access || 0}</p>
              </div>
              <Shield className="w-8 h-8 text-blue-300" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Without Access</p>
                <p className="text-2xl font-bold text-amber-600">{stats?.without_portal_access || 0}</p>
              </div>
              <UserX className="w-8 h-8 text-amber-300" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Terminated</p>
                <p className="text-2xl font-bold text-red-600">{stats?.terminated || 0}</p>
              </div>
              <UserX className="w-8 h-8 text-red-300" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Level Distribution */}
      {stats?.by_level && Object.keys(stats.by_level).length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">By Level</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4">
              {Object.entries(stats.by_level).map(([level, count]) => (
                <div key={level} className="flex items-center gap-2">
                  <Badge variant="outline" className="capitalize">{level}</Badge>
                  <span className="font-bold">{count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Search & Employee List */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Employee Directory</CardTitle>
            <div className="relative w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
              <Input
                placeholder="Search by name, ID, email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 text-xs uppercase text-zinc-500">Emp ID</th>
                  <th className="text-left px-4 py-3 text-xs uppercase text-zinc-500">Name</th>
                  <th className="text-left px-4 py-3 text-xs uppercase text-zinc-500">Department</th>
                  <th className="text-left px-4 py-3 text-xs uppercase text-zinc-500">Designation</th>
                  <th className="text-center px-4 py-3 text-xs uppercase text-zinc-500">Level</th>
                  <th className="text-center px-4 py-3 text-xs uppercase text-zinc-500">Access</th>
                  <th className="text-center px-4 py-3 text-xs uppercase text-zinc-500">Status</th>
                  <th className="text-center px-4 py-3 text-xs uppercase text-zinc-500">Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredEmployees.map(emp => (
                  <tr key={emp.id} className="border-b hover:bg-zinc-50">
                    <td className="px-4 py-3 font-mono text-xs">{emp.employee_id || 'N/A'}</td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium">{emp.first_name} {emp.last_name}</p>
                        <p className="text-xs text-zinc-400">{emp.email}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-zinc-600">{emp.department || '-'}</td>
                    <td className="px-4 py-3 text-zinc-600">{emp.designation || '-'}</td>
                    <td className="px-4 py-3 text-center">
                      <Badge variant="outline" className="capitalize text-xs">
                        {emp.level || 'N/A'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {emp.has_portal_access ? (
                        <Badge className="bg-emerald-100 text-emerald-700">Yes</Badge>
                      ) : (
                        <Badge className="bg-zinc-100 text-zinc-500">No</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <Badge className={emp.status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}>
                        {emp.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleViewEmployee(emp)}
                        data-testid={`view-emp-${emp.employee_id}`}
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Employee Detail Dialog */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Employee Journey</DialogTitle>
          </DialogHeader>
          
          {selectedEmployee && (
            <div className="space-y-6">
              {/* Employee Info */}
              <div className="flex items-start gap-4 p-4 bg-zinc-50 rounded-lg">
                <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center text-2xl font-bold text-emerald-600">
                  {selectedEmployee.first_name?.[0]}{selectedEmployee.last_name?.[0]}
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-bold">
                    {selectedEmployee.first_name} {selectedEmployee.last_name}
                  </h3>
                  <p className="text-sm text-zinc-500">{selectedEmployee.designation} • {selectedEmployee.department}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-zinc-400">
                    <span className="flex items-center gap-1">
                      <Mail className="w-3 h-3" /> {selectedEmployee.email}
                    </span>
                    {selectedEmployee.phone && (
                      <span className="flex items-center gap-1">
                        <Phone className="w-3 h-3" /> {selectedEmployee.phone}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-2 mt-2">
                    <Badge variant="outline" className="font-mono text-xs">
                      {selectedEmployee.employee_id}
                    </Badge>
                    <Badge className={selectedEmployee.has_portal_access ? 'bg-emerald-100 text-emerald-700' : 'bg-zinc-100 text-zinc-500'}>
                      {selectedEmployee.has_portal_access ? 'Portal Access' : 'No Access'}
                    </Badge>
                    <Badge variant="outline" className="capitalize">
                      {selectedEmployee.level}
                    </Badge>
                  </div>
                </div>
              </div>

              {/* Linked Records Summary */}
              {linkedRecords && (
                <div>
                  <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" /> Linked Records ({linkedRecords.total_records})
                  </h4>
                  <div className="grid grid-cols-5 gap-2">
                    {Object.entries(linkedRecords.linked_records).map(([key, count]) => (
                      <div key={key} className="p-2 bg-zinc-50 rounded text-center">
                        <p className="text-lg font-bold">{count}</p>
                        <p className="text-xs text-zinc-500 capitalize">{key.replace('_', ' ')}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Timeline */}
              {employeeTimeline && (
                <div>
                  <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                    <Clock className="w-4 h-4" /> Journey Timeline ({employeeTimeline.total_events} events)
                  </h4>
                  <div className="space-y-3 max-h-[300px] overflow-y-auto">
                    {employeeTimeline.timeline.map((event, idx) => (
                      <div key={idx} className="flex items-start gap-3 p-3 bg-zinc-50 rounded-lg">
                        <div className="mt-1">
                          {eventIcons[event.event] || <ChevronRight className="w-4 h-4" />}
                        </div>
                        <div className="flex-1">
                          <p className="font-medium text-sm">{event.title}</p>
                          <p className="text-xs text-zinc-500">{event.description}</p>
                        </div>
                        <p className="text-xs text-zinc-400">
                          {event.date ? new Date(event.date).toLocaleDateString() : '-'}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default EmployeeScorecard;
