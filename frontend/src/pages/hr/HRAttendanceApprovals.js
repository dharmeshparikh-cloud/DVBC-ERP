import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { 
  CheckCircle, XCircle, Clock, MapPin, User, Calendar, 
  Building2, AlertCircle, Eye, ThumbsUp, ThumbsDown, Loader2,
  Camera, Navigation
} from 'lucide-react';
import { toast } from 'sonner';

const HRAttendanceApprovals = () => {
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [remarks, setRemarks] = useState('');

  useEffect(() => {
    fetchPendingApprovals();
  }, []);

  const fetchPendingApprovals = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/hr/pending-attendance-approvals`);
      setPendingApprovals(res.data.pending_approvals || []);
    } catch (error) {
      toast.error('Failed to fetch pending approvals');
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (action) => {
    if (!selectedRecord) return;
    
    setActionLoading(true);
    try {
      await axios.post(`${API}/hr/attendance-approval/${selectedRecord.id}`, {
        action,
        remarks
      });
      toast.success(`Attendance ${action === 'approve' ? 'approved' : 'rejected'} successfully`);
      setShowDetails(false);
      setSelectedRecord(null);
      setRemarks('');
      fetchPendingApprovals();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to ${action} attendance`);
    } finally {
      setActionLoading(false);
    }
  };

  const openDetails = (record) => {
    setSelectedRecord(record);
    setShowDetails(true);
    setRemarks('');
  };

  return (
    <div data-testid="hr-attendance-approvals">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 dark:text-zinc-100 mb-2">
          Attendance Approvals
        </h1>
        <p className="text-zinc-500 dark:text-zinc-400">
          Review and approve check-ins from unverified locations
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
              <Clock className="w-6 h-6 text-amber-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">{pendingApprovals.length}</p>
              <p className="text-sm text-zinc-500 dark:text-zinc-400">Pending</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
              <CheckCircle className="w-6 h-6 text-emerald-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">-</p>
              <p className="text-sm text-zinc-500 dark:text-zinc-400">Approved Today</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
              <XCircle className="w-6 h-6 text-red-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">-</p>
              <p className="text-sm text-zinc-500 dark:text-zinc-400">Rejected Today</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pending Approvals List */}
      <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm">
        <CardHeader className="border-b border-zinc-200 dark:border-zinc-700 py-4">
          <CardTitle className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            Pending Approvals
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center h-40">
              <Loader2 className="w-6 h-6 animate-spin text-zinc-400" />
            </div>
          ) : pendingApprovals.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-zinc-500">
              <CheckCircle className="w-12 h-12 text-emerald-300 mb-3" />
              <p>No pending approvals</p>
            </div>
          ) : (
            <div className="divide-y divide-zinc-200 dark:divide-zinc-700">
              {pendingApprovals.map((record) => (
                <div 
                  key={record.id} 
                  className="flex items-center gap-4 p-4 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition cursor-pointer"
                  onClick={() => openDetails(record)}
                >
                  {/* Selfie Thumbnail */}
                  <div className="w-14 h-14 rounded-lg overflow-hidden bg-zinc-200 dark:bg-zinc-700 flex-shrink-0">
                    {record.selfie ? (
                      <img src={record.selfie} alt="selfie" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <User className="w-6 h-6 text-zinc-400" />
                      </div>
                    )}
                  </div>

                  {/* Employee Info */}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-zinc-900 dark:text-zinc-100 truncate">
                      {record.employee_name || 'Unknown Employee'}
                    </p>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400">
                      {record.department} • {record.date}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        record.work_location === 'in_office' 
                          ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' 
                          : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                      }`}>
                        {record.work_location === 'in_office' ? 'Office' : 'On-Site'}
                      </span>
                      <span className="text-xs text-zinc-400">
                        {record.check_in_time ? new Date(record.check_in_time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : ''}
                      </span>
                    </div>
                  </div>

                  {/* Location Warning */}
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-amber-500" />
                    <Button variant="ghost" size="sm" className="text-blue-600">
                      <Eye className="w-4 h-4 mr-1" />
                      Review
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Details Dialog */}
      <Dialog open={showDetails} onOpenChange={setShowDetails}>
        <DialogContent className="max-w-2xl border-zinc-200 dark:border-zinc-700 rounded-lg">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
              Review Attendance
            </DialogTitle>
            <DialogDescription className="text-zinc-500 dark:text-zinc-400">
              Verify employee check-in details and take action
            </DialogDescription>
          </DialogHeader>

          {selectedRecord && (
            <div className="space-y-6 mt-4">
              {/* Employee & Selfie */}
              <div className="flex gap-6">
                {/* Selfie */}
                <div className="w-48 flex-shrink-0">
                  <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2 flex items-center gap-1">
                    <Camera className="w-4 h-4" />
                    Selfie
                  </p>
                  <div className="w-full aspect-[3/4] rounded-lg overflow-hidden bg-zinc-200 dark:bg-zinc-700">
                    {selectedRecord.selfie ? (
                      <img src={selectedRecord.selfie} alt="selfie" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <User className="w-12 h-12 text-zinc-400" />
                      </div>
                    )}
                  </div>
                </div>

                {/* Details */}
                <div className="flex-1 space-y-4">
                  <div>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400">Employee</p>
                    <p className="font-medium text-zinc-900 dark:text-zinc-100">{selectedRecord.employee_name}</p>
                    <p className="text-sm text-zinc-500">{selectedRecord.department}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-zinc-500 dark:text-zinc-400">Date</p>
                      <p className="font-medium text-zinc-900 dark:text-zinc-100">{selectedRecord.date}</p>
                    </div>
                    <div>
                      <p className="text-sm text-zinc-500 dark:text-zinc-400">Check-in Time</p>
                      <p className="font-medium text-zinc-900 dark:text-zinc-100">
                        {selectedRecord.check_in_time ? new Date(selectedRecord.check_in_time).toLocaleTimeString() : '-'}
                      </p>
                    </div>
                  </div>

                  <div>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400">Work Location Type</p>
                    <span className={`inline-flex items-center gap-1 text-sm px-2 py-1 rounded-full ${
                      selectedRecord.work_location === 'in_office' 
                        ? 'bg-blue-100 text-blue-700' 
                        : 'bg-emerald-100 text-emerald-700'
                    }`}>
                      {selectedRecord.work_location === 'in_office' ? <Building2 className="w-4 h-4" /> : <MapPin className="w-4 h-4" />}
                      {selectedRecord.work_location === 'in_office' ? 'Office' : 'On-Site (Client)'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Location Details */}
              <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-medium text-amber-800 dark:text-amber-200">Location Not Verified</p>
                    <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                      Employee checked in from a location that is not within 500m of any approved office or client location.
                    </p>
                    
                    {selectedRecord.geo_location && (
                      <div className="mt-3 p-3 rounded-lg bg-white dark:bg-zinc-800">
                        <div className="flex items-start gap-2">
                          <Navigation className="w-4 h-4 text-zinc-500 mt-0.5" />
                          <div>
                            <p className="text-sm text-zinc-700 dark:text-zinc-300">
                              {selectedRecord.geo_location.address || 'Address not available'}
                            </p>
                            <p className="text-xs text-zinc-500 mt-1">
                              Coordinates: {selectedRecord.geo_location.latitude?.toFixed(6)}, {selectedRecord.geo_location.longitude?.toFixed(6)}
                              {selectedRecord.geo_location.accuracy && ` (±${Math.round(selectedRecord.geo_location.accuracy)}m)`}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Employee Justification */}
              {selectedRecord.justification && (
                <div className="p-4 rounded-lg bg-zinc-100 dark:bg-zinc-800">
                  <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">Employee's Justification</p>
                  <p className="text-sm text-zinc-600 dark:text-zinc-400 italic">
                    "{selectedRecord.justification}"
                  </p>
                </div>
              )}

              {/* HR Remarks */}
              <div>
                <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">HR Remarks (optional)</p>
                <Input
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  placeholder="Add remarks for this decision..."
                  className="rounded-sm border-zinc-200 dark:border-zinc-700"
                />
              </div>
            </div>
          )}

          <DialogFooter className="flex gap-3 mt-6">
            <Button 
              variant="outline" 
              onClick={() => setShowDetails(false)}
              className="rounded-sm"
            >
              Cancel
            </Button>
            <Button 
              variant="destructive"
              onClick={() => handleAction('reject')}
              disabled={actionLoading}
              className="rounded-sm bg-red-600 hover:bg-red-700"
            >
              {actionLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ThumbsDown className="w-4 h-4 mr-2" />}
              Reject
            </Button>
            <Button 
              onClick={() => handleAction('approve')}
              disabled={actionLoading}
              className="rounded-sm bg-emerald-600 hover:bg-emerald-700"
            >
              {actionLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ThumbsUp className="w-4 h-4 mr-2" />}
              Approve
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default HRAttendanceApprovals;
