import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { 
  Receipt, DollarSign, FileText, Download, RefreshCw, 
  Search, CheckCircle, Clock, XCircle, Users
} from 'lucide-react';

const Invoices = () => {
  const { user } = useContext(AuthContext);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [employees, setEmployees] = useState([]);

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  useEffect(() => {
    fetchInvoices();
    fetchEmployees();
  }, []);

  const fetchInvoices = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/invoices`, { headers });
      if (res.ok) {
        const data = await res.json();
        setInvoices(Array.isArray(data) ? data : data.invoices || []);
      }
    } catch (error) {
      console.error('Error fetching invoices:', error);
      toast.error('Failed to fetch invoices');
    } finally {
      setLoading(false);
    }
  };

  const fetchEmployees = async () => {
    try {
      const res = await fetch(`${API}/employees`, { headers });
      if (res.ok) {
        const data = await res.json();
        setEmployees(data);
      }
    } catch (error) {
      console.error('Error fetching employees:', error);
    }
  };

  const getEmployeeName = (empId) => {
    const emp = employees.find(e => e.id === empId);
    return emp ? `${emp.first_name} ${emp.last_name}` : 'Unknown';
  };

  const getStatusBadge = (status) => {
    const styles = {
      paid: { bg: 'bg-green-100 text-green-700 border-green-300', icon: CheckCircle },
      pending: { bg: 'bg-yellow-100 text-yellow-700 border-yellow-300', icon: Clock },
      overdue: { bg: 'bg-red-100 text-red-700 border-red-300', icon: XCircle },
      draft: { bg: 'bg-zinc-100 text-zinc-700 border-zinc-300', icon: FileText }
    };
    const style = styles[status] || styles.pending;
    const Icon = style.icon;
    return (
      <span className={`px-2 py-1 text-xs rounded-full border flex items-center gap-1 w-fit ${style.bg}`}>
        <Icon className="w-3 h-3" />
        {status?.charAt(0).toUpperCase() + status?.slice(1)}
      </span>
    );
  };

  const filteredInvoices = invoices.filter(inv => {
    const matchesSearch = 
      inv.invoice_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inv.client_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inv.project_name?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || inv.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const totalAmount = filteredInvoices.reduce((sum, inv) => sum + (inv.amount || 0), 0);
  const paidAmount = filteredInvoices.filter(i => i.status === 'paid').reduce((sum, inv) => sum + (inv.amount || 0), 0);
  const pendingAmount = filteredInvoices.filter(i => i.status === 'pending' || i.status === 'overdue').reduce((sum, inv) => sum + (inv.amount || 0), 0);

  const downloadCSV = () => {
    const headers = ['Invoice #', 'Client', 'Project', 'Amount', 'Status', 'Date', 'Sales Employee', 'Due Date'];
    const rows = filteredInvoices.map(inv => [
      inv.invoice_number || '',
      inv.client_name || '',
      inv.project_name || '',
      inv.amount || 0,
      inv.status || '',
      inv.created_at?.slice(0, 10) || '',
      getEmployeeName(inv.sales_employee_id),
      inv.due_date?.slice(0, 10) || ''
    ]);

    const csv = [headers, ...rows].map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Invoices_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('CSV downloaded');
  };

  return (
    <div className="p-6 space-y-6" data-testid="invoices-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Invoices</h1>
          <p className="text-zinc-600">All proforma invoices linked with sales employees</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={downloadCSV} variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
          <Button onClick={fetchInvoices} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-white border-zinc-200">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-blue-100 rounded-lg">
                <Receipt className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-zinc-900">{filteredInvoices.length}</p>
                <p className="text-sm text-zinc-600">Total Invoices</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-white border-zinc-200">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-zinc-100 rounded-lg">
                <DollarSign className="w-6 h-6 text-zinc-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-zinc-900">₹{(totalAmount/100000).toFixed(1)}L</p>
                <p className="text-sm text-zinc-600">Total Value</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-white border-zinc-200">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-green-100 rounded-lg">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-green-600">₹{(paidAmount/100000).toFixed(1)}L</p>
                <p className="text-sm text-zinc-600">Paid</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-white border-zinc-200">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-yellow-100 rounded-lg">
                <Clock className="w-6 h-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-yellow-600">₹{(pendingAmount/100000).toFixed(1)}L</p>
                <p className="text-sm text-zinc-600">Pending</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <Input
            placeholder="Search invoices..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 bg-zinc-50 border-zinc-300"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40 bg-zinc-50 border-zinc-300">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="paid">Paid</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="overdue">Overdue</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Invoices Table */}
      <Card className="bg-white border-zinc-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Invoice List
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-zinc-600">Loading...</div>
          ) : filteredInvoices.length === 0 ? (
            <div className="text-center py-8 text-zinc-500">
              <Receipt className="w-12 h-12 mx-auto mb-3 text-zinc-400" />
              <p>No invoices found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-200">
                    <th className="text-left p-3 text-zinc-600">Invoice #</th>
                    <th className="text-left p-3 text-zinc-600">Client</th>
                    <th className="text-left p-3 text-zinc-600">Project</th>
                    <th className="text-right p-3 text-zinc-600">Amount</th>
                    <th className="text-center p-3 text-zinc-600">Status</th>
                    <th className="text-left p-3 text-zinc-600">Sales Employee</th>
                    <th className="text-left p-3 text-zinc-600">Date</th>
                    <th className="text-left p-3 text-zinc-600">Due Date</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredInvoices.map(inv => (
                    <tr key={inv.id} className="border-b border-zinc-100 hover:bg-zinc-50">
                      <td className="p-3 font-mono text-zinc-800">{inv.invoice_number || '-'}</td>
                      <td className="p-3 text-zinc-800 font-medium">{inv.client_name || '-'}</td>
                      <td className="p-3 text-zinc-600">{inv.project_name || '-'}</td>
                      <td className="p-3 text-right font-medium text-zinc-800">
                        ₹{(inv.amount || 0).toLocaleString()}
                      </td>
                      <td className="p-3 text-center">{getStatusBadge(inv.status)}</td>
                      <td className="p-3 text-zinc-600">
                        <div className="flex items-center gap-2">
                          <Users className="w-4 h-4 text-zinc-400" />
                          {getEmployeeName(inv.sales_employee_id)}
                        </div>
                      </td>
                      <td className="p-3 text-zinc-600">{inv.created_at?.slice(0, 10) || '-'}</td>
                      <td className="p-3 text-zinc-600">{inv.due_date?.slice(0, 10) || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default Invoices;
