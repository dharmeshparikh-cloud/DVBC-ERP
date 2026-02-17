import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import axios from 'axios';
import { 
  Car, Bike, MapPin, Calendar, CheckCircle, XCircle, 
  Clock, TrendingUp, IndianRupee, Filter, Search,
  ChevronDown, FileText, User, Navigation
} from 'lucide-react';
import { toast } from 'sonner';

const TravelReimbursement = () => {
  const { user } = useContext(AuthContext);
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState('all'); // all, pending, approved, rejected
  const [selectedMonth, setSelectedMonth] = useState(new Date().toISOString().slice(0, 7));
  const [searchQuery, setSearchQuery] = useState('');

  const fetchClaims = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filter !== 'all') params.append('status', filter);
      if (selectedMonth) params.append('month', selectedMonth);
      
      const response = await axios.get(`${API}/travel/reimbursements?${params.toString()}`);
      setClaims(response.data.records || []);
    } catch (error) {
      toast.error('Failed to fetch travel claims');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/travel/stats?month=${selectedMonth}`);
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats');
    }
  };

  useEffect(() => {
    fetchClaims();
    fetchStats();
  }, [filter, selectedMonth]);

  const handleApprove = async (claimId) => {
    try {
      await axios.post(`${API}/travel/reimbursements/${claimId}/approve`);
      toast.success('Travel claim approved');
      fetchClaims();
      fetchStats();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve');
    }
  };

  const handleReject = async (claimId) => {
    const reason = prompt('Please enter rejection reason:');
    if (!reason) return;
    
    try {
      await axios.post(`${API}/travel/reimbursements/${claimId}/reject`, { reason });
      toast.success('Travel claim rejected');
      fetchClaims();
      fetchStats();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reject');
    }
  };

  const handleConvertToExpense = async (claimId) => {
    try {
      const response = await axios.post(`${API}/travel/reimbursements/${claimId}/convert-to-expense`);
      toast.success(`Converted to expense: ${response.data.expense_id}`);
      fetchClaims();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to convert');
    }
  };

  const filteredClaims = claims.filter(claim => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      claim.employee_name?.toLowerCase().includes(query) ||
      claim.start_location?.name?.toLowerCase().includes(query) ||
      claim.end_location?.name?.toLowerCase().includes(query)
    );
  });

  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-amber-100 text-amber-700 border-amber-200',
      approved: 'bg-emerald-100 text-emerald-700 border-emerald-200',
      rejected: 'bg-red-100 text-red-700 border-red-200',
      linked_to_expense: 'bg-blue-100 text-blue-700 border-blue-200'
    };
    const labels = {
      pending: 'Pending',
      approved: 'Approved',
      rejected: 'Rejected',
      linked_to_expense: 'Linked to Expense'
    };
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full border ${styles[status] || 'bg-gray-100 text-gray-600'}`}>
        {labels[status] || status}
      </span>
    );
  };

  const getVehicleIcon = (type) => {
    switch(type) {
      case 'two_wheeler': return <Bike className="w-5 h-5" />;
      default: return <Car className="w-5 h-5" />;
    }
  };

  return (
    <div className="space-y-6" data-testid="travel-reimbursement-page">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">Travel Reimbursement</h1>
          <p className="text-zinc-500 dark:text-zinc-400">Manage employee travel claims and reimbursements</p>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="month"
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className="px-3 py-2 rounded-lg border border-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-white text-sm"
          />
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-zinc-800 rounded-xl p-4 border border-zinc-200 dark:border-zinc-700">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-teal-100 dark:bg-teal-900/30 flex items-center justify-center">
                <FileText className="w-5 h-5 text-teal-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-zinc-900 dark:text-white">{stats.total_records}</p>
                <p className="text-xs text-zinc-500">Total Claims</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-zinc-800 rounded-xl p-4 border border-zinc-200 dark:border-zinc-700">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                <Clock className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-zinc-900 dark:text-white">{stats.pending_count}</p>
                <p className="text-xs text-zinc-500">Pending</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-zinc-800 rounded-xl p-4 border border-zinc-200 dark:border-zinc-700">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <Navigation className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-zinc-900 dark:text-white">{stats.total_distance_km?.toLocaleString()}</p>
                <p className="text-xs text-zinc-500">Total km</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-zinc-800 rounded-xl p-4 border border-zinc-200 dark:border-zinc-700">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                <IndianRupee className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-zinc-900 dark:text-white">₹{stats.total_amount?.toLocaleString()}</p>
                <p className="text-xs text-zinc-500">Total Amount</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white dark:bg-zinc-800 rounded-xl p-4 border border-zinc-200 dark:border-zinc-700">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
            <input
              type="text"
              placeholder="Search by employee or location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-600 dark:bg-zinc-700 dark:text-white text-sm"
            />
          </div>
          <div className="flex gap-2">
            {['all', 'pending', 'approved', 'rejected'].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                  filter === f 
                    ? 'bg-teal-600 text-white' 
                    : 'bg-zinc-100 dark:bg-zinc-700 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-200'
                }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Claims Table */}
      <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full mx-auto"></div>
            <p className="text-zinc-500 mt-4">Loading claims...</p>
          </div>
        ) : filteredClaims.length === 0 ? (
          <div className="p-8 text-center">
            <Car className="w-12 h-12 text-zinc-300 mx-auto mb-4" />
            <p className="text-zinc-500">No travel claims found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-zinc-50 dark:bg-zinc-700/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase">Employee</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase">Route</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase">Date</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase">Vehicle</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase">Distance</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase">Amount</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-700">
                {filteredClaims.map((claim) => (
                  <tr key={claim.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-700/30">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-teal-100 flex items-center justify-center">
                          <User className="w-4 h-4 text-teal-600" />
                        </div>
                        <span className="text-sm font-medium text-zinc-900 dark:text-white">{claim.employee_name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm">
                        <div className="flex items-center gap-1 text-zinc-700 dark:text-zinc-300">
                          <MapPin className="w-3 h-3 text-emerald-500" />
                          <span className="truncate max-w-[120px]">{claim.start_location?.name || 'N/A'}</span>
                        </div>
                        <div className="flex items-center gap-1 text-zinc-500 dark:text-zinc-400">
                          <MapPin className="w-3 h-3 text-red-500" />
                          <span className="truncate max-w-[120px]">{claim.end_location?.name || 'N/A'}</span>
                        </div>
                        {claim.is_round_trip && (
                          <span className="text-xs text-teal-600 font-medium">Round Trip</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-300">
                        <Calendar className="w-4 h-4" />
                        {claim.travel_date}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-300">
                        {getVehicleIcon(claim.vehicle_type)}
                        <span className="capitalize">{claim.vehicle_type?.replace('_', ' ')}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm font-medium text-zinc-900 dark:text-white">{claim.distance_km} km</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm font-bold text-emerald-600">₹{claim.final_amount?.toLocaleString()}</span>
                    </td>
                    <td className="px-4 py-3">
                      {getStatusBadge(claim.status)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {claim.status === 'pending' && (
                          <>
                            <button
                              onClick={() => handleApprove(claim.id)}
                              className="p-1.5 rounded-lg bg-emerald-100 text-emerald-600 hover:bg-emerald-200 transition"
                              title="Approve"
                              data-testid={`approve-${claim.id}`}
                            >
                              <CheckCircle className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleReject(claim.id)}
                              className="p-1.5 rounded-lg bg-red-100 text-red-600 hover:bg-red-200 transition"
                              title="Reject"
                              data-testid={`reject-${claim.id}`}
                            >
                              <XCircle className="w-4 h-4" />
                            </button>
                          </>
                        )}
                        {claim.status === 'approved' && (
                          <button
                            onClick={() => handleConvertToExpense(claim.id)}
                            className="px-2 py-1 rounded-lg bg-blue-100 text-blue-600 hover:bg-blue-200 transition text-xs font-medium"
                            title="Convert to Expense"
                          >
                            To Expense
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default TravelReimbursement;
