import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API } from '../App';

const ApprovalContext = createContext();

export const useApprovals = () => {
  const context = useContext(ApprovalContext);
  if (!context) {
    throw new Error('useApprovals must be used within ApprovalProvider');
  }
  return context;
};

export const ApprovalProvider = ({ children }) => {
  const [pendingCounts, setPendingCounts] = useState({
    ctc: 0,
    bankChanges: 0,
    leaves: 0,
    expenses: 0,
    attendance: 0,
    total: 0
  });
  const [loading, setLoading] = useState(false);
  const [lastFetched, setLastFetched] = useState(null);

  const fetchPendingCounts = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
      setLoading(true);
      const headers = { Authorization: `Bearer ${token}` };
      
      // Fetch all pending counts in parallel
      const [ctcRes, bankRes, leaveRes, expenseRes, attendanceRes] = await Promise.allSettled([
        axios.get(`${API}/ctc/pending-approvals`, { headers }),
        axios.get(`${API}/hr/bank-change-requests`, { headers }),
        axios.get(`${API}/leave-requests?status=pending`, { headers }),
        axios.get(`${API}/expenses?status=pending`, { headers }),
        axios.get(`${API}/hr/pending-attendance-approvals`, { headers })
      ]);

      const ctcCount = ctcRes.status === 'fulfilled' ? (ctcRes.value.data?.length || 0) : 0;
      const bankCount = bankRes.status === 'fulfilled' ? (bankRes.value.data?.length || 0) : 0;
      const leaveCount = leaveRes.status === 'fulfilled' ? (leaveRes.value.data?.length || 0) : 0;
      const expenseCount = expenseRes.status === 'fulfilled' ? (expenseRes.value.data?.length || 0) : 0;
      const attendanceCount = attendanceRes.status === 'fulfilled' ? (attendanceRes.value.data?.length || 0) : 0;

      setPendingCounts({
        ctc: ctcCount,
        bankChanges: bankCount,
        leaves: leaveCount,
        expenses: expenseCount,
        attendance: attendanceCount,
        total: ctcCount + bankCount + leaveCount + expenseCount + attendanceCount
      });
      setLastFetched(new Date());
    } catch (error) {
      console.error('Error fetching pending counts:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch and polling every 10 seconds
  useEffect(() => {
    fetchPendingCounts();
    const interval = setInterval(fetchPendingCounts, 10000); // Poll every 10 seconds
    return () => clearInterval(interval);
  }, [fetchPendingCounts]);

  // Expose refresh function for manual refresh
  const refresh = () => {
    fetchPendingCounts();
  };

  return (
    <ApprovalContext.Provider value={{ pendingCounts, loading, lastFetched, refresh }}>
      {children}
    </ApprovalContext.Provider>
  );
};

export default ApprovalContext;
