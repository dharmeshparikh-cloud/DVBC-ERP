import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { AlertTriangle, Clock, CheckCircle, ArrowRight, Users, Calendar } from 'lucide-react';
import { toast } from 'sonner';
import { formatINR } from '../utils/currency';

const HandoverAlerts = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    try {
      const response = await axios.get(`${API}/projects/handover-alerts`);
      setAlerts(response.data);
    } catch (error) {
      toast.error('Failed to fetch handover alerts');
    } finally {
      setLoading(false);
    }
  };

  const getAlertStyle = (alertType) => {
    switch (alertType) {
      case 'overdue':
        return {
          bg: 'bg-red-50 border-red-200',
          icon: <AlertTriangle className="w-5 h-5 text-red-600" />,
          badge: 'bg-red-100 text-red-700',
          text: 'OVERDUE'
        };
      case 'critical':
        return {
          bg: 'bg-orange-50 border-orange-200',
          icon: <AlertTriangle className="w-5 h-5 text-orange-600" />,
          badge: 'bg-orange-100 text-orange-700',
          text: 'CRITICAL'
        };
      case 'warning':
        return {
          bg: 'bg-yellow-50 border-yellow-200',
          icon: <Clock className="w-5 h-5 text-yellow-600" />,
          badge: 'bg-yellow-100 text-yellow-700',
          text: 'WARNING'
        };
      default:
        return {
          bg: 'bg-emerald-50 border-emerald-200',
          icon: <CheckCircle className="w-5 h-5 text-emerald-600" />,
          badge: 'bg-emerald-100 text-emerald-700',
          text: 'ON TRACK'
        };
    }
  };

  const overdueCount = alerts.filter(a => a.alert_type === 'overdue').length;
  const criticalCount = alerts.filter(a => a.alert_type === 'critical').length;
  const warningCount = alerts.filter(a => a.alert_type === 'warning').length;
  const onTrackCount = alerts.filter(a => a.alert_type === 'on_track').length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-zinc-500">Loading alerts...</div>
      </div>
    );
  }

  return (
    <div data-testid="handover-alerts-page">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
          Handover Alerts
        </h1>
        <p className="text-zinc-500">
          Projects must be handed over within 15 days of agreement approval
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card className="border-red-200 bg-red-50 shadow-none rounded-sm">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-red-600 uppercase tracking-wide">Overdue</div>
                <div className="text-2xl font-semibold text-red-700">{overdueCount}</div>
              </div>
              <AlertTriangle className="w-8 h-8 text-red-300" strokeWidth={1} />
            </div>
          </CardContent>
        </Card>
        <Card className="border-orange-200 bg-orange-50 shadow-none rounded-sm">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-orange-600 uppercase tracking-wide">Critical (0-3 days)</div>
                <div className="text-2xl font-semibold text-orange-700">{criticalCount}</div>
              </div>
              <Clock className="w-8 h-8 text-orange-300" strokeWidth={1} />
            </div>
          </CardContent>
        </Card>
        <Card className="border-yellow-200 bg-yellow-50 shadow-none rounded-sm">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-yellow-600 uppercase tracking-wide">Warning (4-7 days)</div>
                <div className="text-2xl font-semibold text-yellow-700">{warningCount}</div>
              </div>
              <Clock className="w-8 h-8 text-yellow-300" strokeWidth={1} />
            </div>
          </CardContent>
        </Card>
        <Card className="border-emerald-200 bg-emerald-50 shadow-none rounded-sm">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-emerald-600 uppercase tracking-wide">On Track</div>
                <div className="text-2xl font-semibold text-emerald-700">{onTrackCount}</div>
              </div>
              <CheckCircle className="w-8 h-8 text-emerald-300" strokeWidth={1} />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Alerts List */}
      {alerts.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-64">
            <CheckCircle className="w-12 h-12 text-emerald-300 mb-4" strokeWidth={1} />
            <p className="text-zinc-500">No pending handovers</p>
            <p className="text-sm text-zinc-400">All approved agreements have been processed</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {alerts.map((alert) => {
            const style = getAlertStyle(alert.alert_type);
            return (
              <Card 
                key={alert.agreement?.id} 
                className={`${style.bg} shadow-none rounded-sm`}
                data-testid={`alert-card-${alert.agreement?.id}`}
              >
                <CardContent className="py-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      {style.icon}
                      <div>
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-semibold text-zinc-950">
                            {alert.lead?.company || 'Unknown Company'}
                          </h3>
                          <span className={`px-2 py-0.5 text-xs font-medium rounded-sm ${style.badge}`}>
                            {style.text}
                          </span>
                          {alert.has_project && (
                            <span className="px-2 py-0.5 text-xs font-medium rounded-sm bg-blue-100 text-blue-700">
                              PROJECT CREATED
                            </span>
                          )}
                        </div>
                        <div className="space-y-1 text-sm">
                          <div className="text-zinc-600">
                            <span className="text-zinc-500">Contact:</span>{' '}
                            {alert.lead?.first_name} {alert.lead?.last_name}
                          </div>
                          <div className="text-zinc-600">
                            <span className="text-zinc-500">Agreement:</span>{' '}
                            {alert.agreement?.agreement_number}
                          </div>
                          <div className="flex items-center gap-4 text-zinc-600">
                            <span>
                              <span className="text-zinc-500">Approved:</span>{' '}
                              {alert.days_since_approval} days ago
                            </span>
                            <span className={alert.days_remaining <= 0 ? 'text-red-600 font-semibold' : ''}>
                              <span className="text-zinc-500">Remaining:</span>{' '}
                              {alert.days_remaining <= 0 
                                ? `${Math.abs(alert.days_remaining)} days overdue`
                                : `${alert.days_remaining} days`
                              }
                            </span>
                          </div>
                        </div>
                        
                        {/* Status Indicators */}
                        <div className="flex items-center gap-4 mt-3">
                          <div className="flex items-center gap-2">
                            {alert.has_project ? (
                              <CheckCircle className="w-4 h-4 text-emerald-600" />
                            ) : (
                              <Clock className="w-4 h-4 text-zinc-400" />
                            )}
                            <span className={`text-xs ${alert.has_project ? 'text-emerald-600' : 'text-zinc-400'}`}>
                              Project Created
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            {alert.has_consultants_assigned?.length > 0 ? (
                              <CheckCircle className="w-4 h-4 text-emerald-600" />
                            ) : (
                              <Clock className="w-4 h-4 text-zinc-400" />
                            )}
                            <span className={`text-xs ${alert.has_consultants_assigned?.length > 0 ? 'text-emerald-600' : 'text-zinc-400'}`}>
                              Consultants Assigned ({alert.has_consultants_assigned?.length || 0})
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex flex-col gap-2">
                      {!alert.has_project && (
                        <Button
                          onClick={() => navigate('/projects')}
                          size="sm"
                          className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                        >
                          Create Project
                          <ArrowRight className="w-4 h-4 ml-2" strokeWidth={1.5} />
                        </Button>
                      )}
                      {alert.has_project && alert.has_consultants_assigned?.length === 0 && (
                        <Button
                          onClick={() => navigate('/consultants')}
                          size="sm"
                          className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                        >
                          <Users className="w-4 h-4 mr-2" strokeWidth={1.5} />
                          Assign Consultants
                        </Button>
                      )}
                      {alert.has_project && (
                        <Button
                          onClick={() => navigate(`/projects/${alert.project?.id}/tasks`)}
                          size="sm"
                          variant="outline"
                          className="rounded-sm"
                        >
                          View Tasks
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default HandoverAlerts;
