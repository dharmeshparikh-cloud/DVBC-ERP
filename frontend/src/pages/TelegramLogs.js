import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { MessageCircle, Clock, User, Building2, Calendar, RefreshCw, Link2, Users } from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

export default function TelegramLogs() {
  const [meetingLogs, setMeetingLogs] = useState([]);
  const [linkedEmployees, setLinkedEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('meetings');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const [logsRes, employeesRes] = await Promise.all([
        axios.get(`${API}/api/telegram/meeting-logs?limit=100`, { headers }),
        axios.get(`${API}/api/telegram/linked-employees`, { headers })
      ]);

      setMeetingLogs(logsRes.data.logs || []);
      setLinkedEmployees(employeesRes.data.employees || []);
    } catch (error) {
      console.error('Error fetching Telegram data:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (hours) => {
    if (!hours) return '-';
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    if (h === 0) return `${m}m`;
    if (m === 0) return `${h}h`;
    return `${h}h ${m}m`;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Stats
  const totalMeetings = meetingLogs.length;
  const totalHours = meetingLogs.reduce((sum, log) => sum + (log.duration_hours || 0), 0);
  const uniqueClients = [...new Set(meetingLogs.map(log => log.client_name))].length;
  const todayMeetings = meetingLogs.filter(log => {
    const logDate = new Date(log.meeting_date).toDateString();
    return logDate === new Date().toDateString();
  }).length;

  return (
    <div className="p-6 space-y-6" data-testid="telegram-logs-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <MessageCircle className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Telegram Bot Logs</h1>
            <p className="text-gray-500 text-sm">Meeting logs submitted via @dvbc_netra_bot</p>
          </div>
        </div>
        <Button onClick={fetchData} variant="outline" className="gap-2" data-testid="refresh-btn">
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Meetings</p>
                <p className="text-2xl font-bold text-gray-900">{totalMeetings}</p>
              </div>
              <div className="p-2 bg-blue-100 rounded-lg">
                <Calendar className="h-5 w-5 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Hours</p>
                <p className="text-2xl font-bold text-gray-900">{totalHours.toFixed(1)}</p>
              </div>
              <div className="p-2 bg-green-100 rounded-lg">
                <Clock className="h-5 w-5 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Unique Clients</p>
                <p className="text-2xl font-bold text-gray-900">{uniqueClients}</p>
              </div>
              <div className="p-2 bg-purple-100 rounded-lg">
                <Building2 className="h-5 w-5 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Linked Employees</p>
                <p className="text-2xl font-bold text-gray-900">{linkedEmployees.length}</p>
              </div>
              <div className="p-2 bg-amber-100 rounded-lg">
                <Users className="h-5 w-5 text-amber-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <button
          onClick={() => setActiveTab('meetings')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'meetings'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
          data-testid="meetings-tab"
        >
          Meeting Logs ({totalMeetings})
        </button>
        <button
          onClick={() => setActiveTab('employees')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'employees'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
          data-testid="employees-tab"
        >
          Linked Employees ({linkedEmployees.length})
        </button>
      </div>

      {/* Meeting Logs Tab */}
      {activeTab === 'meetings' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Calendar className="h-5 w-5 text-blue-600" />
              Meeting Logs from Telegram
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8 text-gray-500">Loading...</div>
            ) : meetingLogs.length === 0 ? (
              <div className="text-center py-8">
                <MessageCircle className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">No meeting logs yet</p>
                <p className="text-sm text-gray-400 mt-1">
                  Consultants can log meetings via @dvbc_netra_bot on Telegram
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      <th className="text-left p-3 font-medium text-gray-600">Date</th>
                      <th className="text-left p-3 font-medium text-gray-600">Employee</th>
                      <th className="text-left p-3 font-medium text-gray-600">Client</th>
                      <th className="text-left p-3 font-medium text-gray-600">Time</th>
                      <th className="text-left p-3 font-medium text-gray-600">Duration</th>
                      <th className="text-left p-3 font-medium text-gray-600">Notes</th>
                      <th className="text-left p-3 font-medium text-gray-600">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {meetingLogs.map((log, idx) => (
                      <tr key={log.id || idx} className="border-b hover:bg-gray-50">
                        <td className="p-3">
                          <div className="font-medium">{formatDate(log.meeting_date)}</div>
                          <div className="text-xs text-gray-400">{formatTime(log.created_at)}</div>
                        </td>
                        <td className="p-3">
                          <div className="flex items-center gap-2">
                            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                              <span className="text-blue-600 font-medium text-xs">
                                {log.employee_name?.split(' ').map(n => n[0]).join('') || '?'}
                              </span>
                            </div>
                            <div>
                              <div className="font-medium text-sm">{log.employee_name || '-'}</div>
                              <div className="text-xs text-gray-400">{log.employee_id}</div>
                            </div>
                          </div>
                        </td>
                        <td className="p-3">
                          <div className="font-medium">{log.client_name || '-'}</div>
                        </td>
                        <td className="p-3 text-sm">
                          {log.start_time && log.end_time ? (
                            <span>{log.start_time} - {log.end_time}</span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="p-3">
                          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                            {formatDuration(log.duration_hours)}
                          </Badge>
                        </td>
                        <td className="p-3">
                          <div className="max-w-xs truncate text-sm text-gray-600" title={log.notes}>
                            {log.notes || '-'}
                          </div>
                        </td>
                        <td className="p-3">
                          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                            {log.status || 'logged'}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Linked Employees Tab */}
      {activeTab === 'employees' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Link2 className="h-5 w-5 text-green-600" />
              Employees Linked to Telegram
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8 text-gray-500">Loading...</div>
            ) : linkedEmployees.length === 0 ? (
              <div className="text-center py-8">
                <Users className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">No employees linked yet</p>
                <p className="text-sm text-gray-400 mt-1">
                  Employees can link by messaging @dvbc_netra_bot with their Employee ID
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {linkedEmployees.map((emp, idx) => (
                  <div
                    key={emp.employee_id || idx}
                    className="p-4 border rounded-lg hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                        <span className="text-green-600 font-medium">
                          {emp.first_name?.[0]}{emp.last_name?.[0]}
                        </span>
                      </div>
                      <div>
                        <div className="font-medium">{emp.first_name} {emp.last_name}</div>
                        <div className="text-sm text-gray-500">{emp.employee_id}</div>
                      </div>
                    </div>
                    <div className="mt-3 pt-3 border-t">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-500">Telegram</span>
                        <Badge variant="outline" className="bg-green-50 text-green-700">
                          {emp.telegram_username ? `@${emp.telegram_username}` : 'Linked'}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between text-sm mt-1">
                        <span className="text-gray-500">Since</span>
                        <span className="text-gray-700">{formatDate(emp.telegram_linked_at)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Bot Info Card */}
      <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-600 rounded-xl">
              <MessageCircle className="h-6 w-6 text-white" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900">NETRA Telegram Bot</h3>
              <p className="text-sm text-gray-600">@dvbc_netra_bot</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-500">Commands Available</p>
              <p className="text-sm font-medium text-gray-700">Log meeting • Apply leave • My leaves • Log hours</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
