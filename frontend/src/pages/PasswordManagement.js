import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { 
  Key, Search, Shield, UserX, UserCheck, RefreshCw, 
  Lock, Unlock, AlertTriangle, Copy, Eye, EyeOff
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const PasswordManagement = () => {
  const { user } = useContext(AuthContext);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Dialogs
  const [resetDialog, setResetDialog] = useState(false);
  const [disableDialog, setDisableDialog] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [newPassword, setNewPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Check if current user is Admin or HR
  const isAdmin = user?.role === 'admin';
  const isHR = user?.role === 'hr_manager' || user?.department === 'HR';
  const canManage = isAdmin || isHR;

  useEffect(() => {
    if (canManage) {
      fetchEmployees();
    }
  }, [canManage]);

  const fetchEmployees = async () => {
    try {
      const [empRes, usersRes] = await Promise.all([
        axios.get(`${API}/employees`),
        axios.get(`${API}/users-with-roles`)  // HR Manager can access this endpoint
      ]);
      
      // Merge employee data with user data
      const employeesWithAccess = empRes.data.map(emp => {
        const linkedUser = usersRes.data.find(u => u.email === emp.email);
        return {
          ...emp,
          user_id: linkedUser?.id,
          has_access: !!linkedUser,
          is_active: linkedUser?.is_active ?? true,
          role: linkedUser?.role || 'N/A',
          last_login: linkedUser?.last_login
        };
      });
      
      setEmployees(employeesWithAccess);
    } catch (error) {
      console.error('Error fetching employees:', error);
      toast.error('Failed to load employees');
    } finally {
      setLoading(false);
    }
  };

  const generatePassword = (employeeId) => {
    return `Welcome@${employeeId}`;
  };

  const handleResetPassword = async () => {
    if (!selectedEmployee) return;
    
    try {
      const passwordToSet = newPassword || generatePassword(selectedEmployee.employee_id);
      
      await axios.post(`${API}/auth/admin/reset-employee-password`, {
        employee_id: selectedEmployee.employee_id,
        new_password: passwordToSet
      });
      
      toast.success(`Password reset successfully for ${selectedEmployee.first_name} ${selectedEmployee.last_name}`);
      toast.info(`New password: ${passwordToSet}`);
      
      setResetDialog(false);
      setNewPassword('');
      setSelectedEmployee(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reset password');
    }
  };

  const handleToggleAccess = async () => {
    if (!selectedEmployee) return;
    
    // Prevent disabling admin accounts
    if (selectedEmployee.role === 'admin' && selectedEmployee.is_active) {
      toast.error('Cannot disable Admin accounts');
      setDisableDialog(false);
      return;
    }
    
    try {
      await axios.post(`${API}/auth/admin/toggle-employee-access`, {
        employee_id: selectedEmployee.employee_id,
        is_active: !selectedEmployee.is_active
      });
      
      toast.success(`Access ${selectedEmployee.is_active ? 'disabled' : 'enabled'} for ${selectedEmployee.first_name} ${selectedEmployee.last_name}`);
      
      setDisableDialog(false);
      setSelectedEmployee(null);
      fetchEmployees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to toggle access');
    }
  };

  const openResetDialog = (emp) => {
    setSelectedEmployee(emp);
    setNewPassword(generatePassword(emp.employee_id));
    setResetDialog(true);
  };

  const openDisableDialog = (emp) => {
    setSelectedEmployee(emp);
    setDisableDialog(true);
  };

  const filteredEmployees = employees.filter(emp => {
    const query = searchQuery.toLowerCase();
    return (
      emp.employee_id?.toLowerCase().includes(query) ||
      emp.first_name?.toLowerCase().includes(query) ||
      emp.last_name?.toLowerCase().includes(query) ||
      emp.email?.toLowerCase().includes(query) ||
      emp.department?.toLowerCase().includes(query)
    );
  });

  if (!canManage) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="max-w-md">
          <CardContent className="pt-6 text-center">
            <Shield className="w-12 h-12 mx-auto text-zinc-400 mb-4" />
            <h2 className="text-xl font-semibold mb-2">Access Denied</h2>
            <p className="text-zinc-500">Only Admin and HR Managers can access Password Management.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="password-management">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 flex items-center gap-2">
            <Key className="w-6 h-6" />
            Password Management
          </h1>
          <p className="text-sm text-zinc-500">
            Manage employee login credentials and system access
          </p>
        </div>
        <Badge variant={isAdmin ? 'default' : 'secondary'}>
          {isAdmin ? 'Admin Access' : 'HR Access'}
        </Badge>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Total Employees</p>
                <p className="text-2xl font-bold">{employees.length}</p>
              </div>
              <Shield className="w-8 h-8 text-zinc-300" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">With Access</p>
                <p className="text-2xl font-bold text-emerald-600">{employees.filter(e => e.has_access && e.is_active).length}</p>
              </div>
              <UserCheck className="w-8 h-8 text-emerald-200" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Disabled</p>
                <p className="text-2xl font-bold text-red-600">{employees.filter(e => !e.is_active).length}</p>
              </div>
              <UserX className="w-8 h-8 text-red-200" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">No Access</p>
                <p className="text-2xl font-bold text-amber-600">{employees.filter(e => !e.has_access).length}</p>
              </div>
              <Lock className="w-8 h-8 text-amber-200" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
        <Input
          placeholder="Search by Employee ID, name, email..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
          data-testid="search-employees"
        />
      </div>

      {/* Employee Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Employee ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Login</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto text-zinc-400" />
                    <p className="text-zinc-500 mt-2">Loading employees...</p>
                  </TableCell>
                </TableRow>
              ) : filteredEmployees.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <p className="text-zinc-500">No employees found</p>
                  </TableCell>
                </TableRow>
              ) : (
                filteredEmployees.map((emp) => (
                  <TableRow key={emp.id || emp.employee_id}>
                    <TableCell className="font-mono font-medium">{emp.employee_id}</TableCell>
                    <TableCell>{emp.first_name} {emp.last_name}</TableCell>
                    <TableCell className="text-zinc-500">{emp.email}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{emp.department || 'N/A'}</Badge>
                    </TableCell>
                    <TableCell>
                      {!emp.has_access ? (
                        <Badge variant="secondary" className="bg-zinc-100">No Account</Badge>
                      ) : emp.is_active ? (
                        <Badge className="bg-emerald-100 text-emerald-700">Active</Badge>
                      ) : (
                        <Badge className="bg-red-100 text-red-700">Disabled</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-zinc-400">
                      {emp.last_login ? new Date(emp.last_login).toLocaleDateString() : 'Never'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        {emp.has_access && (
                          <>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => openResetDialog(emp)}
                              className="h-8"
                              data-testid={`reset-pwd-${emp.employee_id}`}
                            >
                              <RefreshCw className="w-3 h-3 mr-1" />
                              Reset
                            </Button>
                            {emp.role !== 'admin' && (
                              <Button
                                size="sm"
                                variant={emp.is_active ? 'destructive' : 'default'}
                                onClick={() => openDisableDialog(emp)}
                                className="h-8"
                                data-testid={`toggle-access-${emp.employee_id}`}
                              >
                                {emp.is_active ? (
                                  <>
                                    <Lock className="w-3 h-3 mr-1" />
                                    Disable
                                  </>
                                ) : (
                                  <>
                                    <Unlock className="w-3 h-3 mr-1" />
                                    Enable
                                  </>
                                )}
                              </Button>
                            )}
                          </>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Reset Password Dialog */}
      <Dialog open={resetDialog} onOpenChange={setResetDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <RefreshCw className="w-5 h-5" />
              Reset Password
            </DialogTitle>
            <DialogDescription>
              Reset password for {selectedEmployee?.first_name} {selectedEmployee?.last_name} ({selectedEmployee?.employee_id})
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>New Password</Label>
              <div className="relative">
                <Input
                  type={showPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  data-testid="new-password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setNewPassword(generatePassword(selectedEmployee?.employee_id))}
              >
                Use Default Pattern
              </Button>
              <span className="text-xs text-zinc-500">Welcome@{selectedEmployee?.employee_id}</span>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <p className="text-xs text-amber-800 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                The employee will need to use this password to login.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setResetDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleResetPassword} className="bg-emerald-600 hover:bg-emerald-700">
              Reset Password
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Disable/Enable Access Dialog */}
      <Dialog open={disableDialog} onOpenChange={setDisableDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedEmployee?.is_active ? (
                <>
                  <Lock className="w-5 h-5 text-red-500" />
                  Disable Access
                </>
              ) : (
                <>
                  <Unlock className="w-5 h-5 text-emerald-500" />
                  Enable Access
                </>
              )}
            </DialogTitle>
            <DialogDescription>
              {selectedEmployee?.is_active
                ? `This will prevent ${selectedEmployee?.first_name} ${selectedEmployee?.last_name} from logging into the system.`
                : `This will allow ${selectedEmployee?.first_name} ${selectedEmployee?.last_name} to login again.`}
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            {selectedEmployee?.is_active && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm text-red-800 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  The employee will be immediately logged out and unable to access the system.
                </p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDisableDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleToggleAccess}
              variant={selectedEmployee?.is_active ? 'destructive' : 'default'}
              className={selectedEmployee?.is_active ? '' : 'bg-emerald-600 hover:bg-emerald-700'}
            >
              {selectedEmployee?.is_active ? 'Disable Access' : 'Enable Access'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PasswordManagement;
