import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { 
  TrendingUp, Users, Target, DollarSign, ArrowRight, Calendar,
  CheckCircle, Clock, AlertCircle, BarChart3, PieChart, ArrowUpRight,
  ChevronRight, Filter, RefreshCw, User, Briefcase, AlertTriangle,
  Zap, TrendingDown
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

const SalesDashboard = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('month');
  const [funnelData, setFunnelData] = useState(null);
  const [myFunnelData, setMyFunnelData] = useState(null);
  const [trendsData, setTrendsData] = useState(null);
  const [bottleneckData, setBottleneckData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [timeInStageData, setTimeInStageData] = useState(null);
  const [winLossData, setWinLossData] = useState(null);
  const [velocityData, setVelocityData] = useState(null);

  const isManager = ['admin', 'manager', 'sr_manager', 'principal_consultant', 'sales_manager'].includes(user?.role);

  useEffect(() => {
    fetchAllData();
  }, [period]);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const promises = [
        axios.get(`${API}/analytics/my-funnel-summary?period=${period}`),
      ];
      
      if (isManager) {
        promises.push(axios.get(`${API}/analytics/funnel-summary?period=${period}`));
        promises.push(axios.get(`${API}/analytics/funnel-trends?period=${period}`));
        promises.push(axios.get(`${API}/analytics/bottleneck-analysis`));
        promises.push(axios.get(`${API}/analytics/forecasting`));
        promises.push(axios.get(`${API}/analytics/time-in-stage`));
        promises.push(axios.get(`${API}/analytics/win-loss`));
        promises.push(axios.get(`${API}/analytics/velocity`));
      }
      
      const results = await Promise.all(promises);
      setMyFunnelData(results[0].data);
      
      if (isManager) {
        setFunnelData(results[1].data);
        setTrendsData(results[2].data);
        setBottleneckData(results[3].data);
        setForecastData(results[4].data);
        setTimeInStageData(results[5].data);
        setWinLossData(results[6].data);
        setVelocityData(results[7].data);
      }
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    if (amount >= 100000) {
      return `₹${(amount / 100000).toFixed(1)}L`;
    }
    return `₹${amount?.toLocaleString() || 0}`;
  };

  const getStageColor = (stage) => {
    const colors = {
      lead: 'bg-gray-100 text-gray-700 border-gray-200',
      meeting: 'bg-blue-100 text-blue-700 border-blue-200',
      pricing: 'bg-indigo-100 text-indigo-700 border-indigo-200',
      sow: 'bg-purple-100 text-purple-700 border-purple-200',
      quotation: 'bg-pink-100 text-pink-700 border-pink-200',
      agreement: 'bg-orange-100 text-orange-700 border-orange-200',
      payment: 'bg-amber-100 text-amber-700 border-amber-200',
      kickoff: 'bg-cyan-100 text-cyan-700 border-cyan-200',
      complete: 'bg-emerald-100 text-emerald-700 border-emerald-200'
    };
    return colors[stage] || 'bg-zinc-100 text-zinc-700';
  };

  const getProgressColor = (percentage) => {
    if (percentage >= 100) return 'bg-emerald-500';
    if (percentage >= 75) return 'bg-blue-500';
    if (percentage >= 50) return 'bg-amber-500';
    return 'bg-red-500';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-zinc-900"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="sales-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Sales Dashboard</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            {isManager ? 'Team funnel analytics and performance' : 'Your sales funnel progress'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-32" data-testid="period-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="week">This Week</SelectItem>
              <SelectItem value="month">This Month</SelectItem>
              <SelectItem value="quarter">This Quarter</SelectItem>
              <SelectItem value="year">This Year</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={fetchAllData}>
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Target vs Achievement - My Performance */}
      {myFunnelData?.targets && (
        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Target className="w-4 h-4 text-blue-600" />
                My Target vs Achievement
              </CardTitle>
              <Badge variant="outline" className="text-xs">
                {period === 'week' ? 'This Week' : period === 'month' ? 'This Month' : period === 'quarter' ? 'This Quarter' : 'This Year'}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-6">
              {/* Meetings */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-600 dark:text-zinc-400">Meetings</span>
                  <span className="text-sm font-medium">
                    {myFunnelData.targets.meetings.achieved} / {myFunnelData.targets.meetings.target || '-'}
                  </span>
                </div>
                <Progress 
                  value={Math.min(myFunnelData.targets.meetings.percentage, 100)} 
                  className="h-2"
                />
                <p className="text-xs text-zinc-500 text-right">
                  {myFunnelData.targets.meetings.percentage}%
                </p>
              </div>
              
              {/* Closures */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-600 dark:text-zinc-400">Closures</span>
                  <span className="text-sm font-medium">
                    {myFunnelData.targets.closures.achieved} / {myFunnelData.targets.closures.target || '-'}
                  </span>
                </div>
                <Progress 
                  value={Math.min(myFunnelData.targets.closures.percentage, 100)} 
                  className="h-2"
                />
                <p className="text-xs text-zinc-500 text-right">
                  {myFunnelData.targets.closures.percentage}%
                </p>
              </div>
              
              {/* Revenue */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-600 dark:text-zinc-400">Revenue</span>
                  <span className="text-sm font-medium">
                    {formatCurrency(myFunnelData.targets.revenue.achieved)} / {formatCurrency(myFunnelData.targets.revenue.target) || '-'}
                  </span>
                </div>
                <Progress 
                  value={Math.min(myFunnelData.targets.revenue.percentage, 100)} 
                  className="h-2"
                />
                <p className="text-xs text-zinc-500 text-right">
                  {myFunnelData.targets.revenue.percentage}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* My Funnel Summary */}
      {myFunnelData && (
        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-indigo-600" />
                My Funnel Progress
              </CardTitle>
              <div className="flex items-center gap-2">
                <Badge className="bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                  {myFunnelData.total_leads} Leads
                </Badge>
                <Badge className="bg-emerald-100 text-emerald-700">
                  {myFunnelData.conversion_rate}% Conversion
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-9 gap-1">
              {Object.entries(myFunnelData.stage_counts).map(([stage, count], index) => (
                <div key={stage} className="text-center relative">
                  <div className={`rounded-lg py-3 px-1 border ${getStageColor(stage)}`}>
                    <p className="text-xl font-bold">{count}</p>
                    <p className="text-[10px] mt-1 capitalize truncate">{stage}</p>
                  </div>
                  {index < 8 && (
                    <ArrowRight className="w-3 h-3 absolute -right-2 top-1/2 -translate-y-1/2 text-zinc-300 z-10" />
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Manager View: Team Summary */}
      {isManager && funnelData && (
        <>
          {/* Team Overview Cards */}
          <div className="grid grid-cols-4 gap-4">
            <Card className="border-zinc-200 dark:border-zinc-800">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400">Total Leads</p>
                    <p className="text-3xl font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                      {funnelData.summary.total_leads}
                    </p>
                  </div>
                  <div className="w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                    <Users className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="border-zinc-200 dark:border-zinc-800">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400">In Progress</p>
                    <p className="text-3xl font-bold text-amber-600 mt-1">
                      {funnelData.summary.in_progress}
                    </p>
                  </div>
                  <div className="w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                    <Clock className="w-6 h-6 text-amber-600 dark:text-amber-400" />
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="border-zinc-200 dark:border-zinc-800">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400">Completed</p>
                    <p className="text-3xl font-bold text-emerald-600 mt-1">
                      {funnelData.summary.completed}
                    </p>
                  </div>
                  <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                    <CheckCircle className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="border-zinc-200 dark:border-zinc-800">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400">Conversion Rate</p>
                    <p className="text-3xl font-bold text-indigo-600 mt-1">
                      {funnelData.summary.conversion_rate}%
                    </p>
                  </div>
                  <div className="w-12 h-12 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
                    <TrendingUp className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Team Funnel Stages */}
          <Card className="border-zinc-200 dark:border-zinc-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <PieChart className="w-4 h-4 text-purple-600" />
                Team Funnel - Stage Distribution
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-9 gap-2">
                {funnelData.funnel_stages.map((stage, index) => {
                  const count = funnelData.stage_counts[stage.id] || 0;
                  const percentage = funnelData.summary.total_leads > 0 
                    ? Math.round((count / funnelData.summary.total_leads) * 100) 
                    : 0;
                  
                  return (
                    <div key={stage.id} className="text-center relative">
                      <div className={`rounded-xl py-4 px-2 border-2 ${getStageColor(stage.id)} hover:scale-105 transition-transform cursor-pointer`}>
                        <p className="text-2xl font-bold">{count}</p>
                        <p className="text-xs mt-1 font-medium">{stage.name}</p>
                        <p className="text-[10px] text-zinc-500 mt-0.5">{percentage}%</p>
                      </div>
                      {index < 8 && (
                        <ChevronRight className="w-4 h-4 absolute -right-3 top-1/2 -translate-y-1/2 text-zinc-400 z-10" />
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Employee Breakdown */}
          {funnelData.employee_breakdown?.length > 0 && (
            <Card className="border-zinc-200 dark:border-zinc-800">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    <User className="w-4 h-4 text-cyan-600" />
                    Employee-wise Funnel Summary
                  </CardTitle>
                  <Link to="/manager-leads-dashboard">
                    <Button variant="outline" size="sm">
                      View Detailed <ArrowUpRight className="w-3 h-3 ml-1" />
                    </Button>
                  </Link>
                </div>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-200 dark:border-zinc-700">
                        <th className="text-left py-3 px-2 font-medium text-zinc-600 dark:text-zinc-400">Employee</th>
                        <th className="text-center py-3 px-1 font-medium text-zinc-600 dark:text-zinc-400">Lead</th>
                        <th className="text-center py-3 px-1 font-medium text-zinc-600 dark:text-zinc-400">Meet</th>
                        <th className="text-center py-3 px-1 font-medium text-zinc-600 dark:text-zinc-400">Price</th>
                        <th className="text-center py-3 px-1 font-medium text-zinc-600 dark:text-zinc-400">SOW</th>
                        <th className="text-center py-3 px-1 font-medium text-zinc-600 dark:text-zinc-400">Quote</th>
                        <th className="text-center py-3 px-1 font-medium text-zinc-600 dark:text-zinc-400">Agree</th>
                        <th className="text-center py-3 px-1 font-medium text-zinc-600 dark:text-zinc-400">Pay</th>
                        <th className="text-center py-3 px-1 font-medium text-zinc-600 dark:text-zinc-400">Kick</th>
                        <th className="text-center py-3 px-1 font-medium text-zinc-600 dark:text-zinc-400">Done</th>
                        <th className="text-center py-3 px-2 font-medium text-zinc-600 dark:text-zinc-400">Total</th>
                        <th className="text-center py-3 px-2 font-medium text-zinc-600 dark:text-zinc-400">Conv%</th>
                      </tr>
                    </thead>
                    <tbody>
                      {funnelData.employee_breakdown.slice(0, 10).map((emp, index) => (
                        <tr key={emp.employee_id} className="border-b border-zinc-100 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                          <td className="py-3 px-2 font-medium text-zinc-900 dark:text-zinc-100">{emp.employee_name}</td>
                          <td className="text-center py-3 px-1">{emp.stages.lead}</td>
                          <td className="text-center py-3 px-1">{emp.stages.meeting}</td>
                          <td className="text-center py-3 px-1">{emp.stages.pricing}</td>
                          <td className="text-center py-3 px-1">{emp.stages.sow}</td>
                          <td className="text-center py-3 px-1">{emp.stages.quotation}</td>
                          <td className="text-center py-3 px-1">{emp.stages.agreement}</td>
                          <td className="text-center py-3 px-1">{emp.stages.payment}</td>
                          <td className="text-center py-3 px-1">{emp.stages.kickoff}</td>
                          <td className="text-center py-3 px-1">
                            <span className="text-emerald-600 font-medium">{emp.stages.complete}</span>
                          </td>
                          <td className="text-center py-3 px-2 font-bold">{emp.total_leads}</td>
                          <td className="text-center py-3 px-2">
                            <Badge className={emp.conversion_rate >= 20 ? 'bg-emerald-100 text-emerald-700' : emp.conversion_rate >= 10 ? 'bg-amber-100 text-amber-700' : 'bg-zinc-100 text-zinc-700'}>
                              {emp.conversion_rate}%
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Trends Chart */}
          {trendsData?.trends?.length > 0 && (
            <Card className="border-zinc-200 dark:border-zinc-800">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-green-600" />
                  Funnel Trends
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-6 gap-4">
                  {trendsData.trends.map((trend, index) => (
                    <div key={index} className="text-center p-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg">
                      <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-2">{trend.period}</p>
                      <p className="text-lg font-bold text-zinc-900 dark:text-zinc-100">{trend.leads_created}</p>
                      <p className="text-xs text-zinc-500">New Leads</p>
                      <div className="mt-2 pt-2 border-t border-zinc-200 dark:border-zinc-700">
                        <p className="text-sm font-medium text-emerald-600">{trend.completed} closed</p>
                        <p className="text-xs text-zinc-500">{trend.conversion_rate}% conv.</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Bottleneck Analysis & Forecasting */}
          <div className="grid grid-cols-2 gap-6">
            {/* Bottleneck Analysis */}
            {bottleneckData && (
              <Card className="border-zinc-200 dark:border-zinc-800">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-red-500" />
                      Bottleneck Analysis
                    </CardTitle>
                    <Badge variant="outline" className="text-xs">
                      {bottleneckData.overall_conversion}% Overall Conv.
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {bottleneckData.bottlenecks?.slice(0, 5).map((bn, index) => (
                      <div key={index} className="flex items-center justify-between">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <span className="text-xs text-zinc-500 truncate">{bn.from_name}</span>
                          <ArrowRight className="w-3 h-3 text-zinc-400 flex-shrink-0" />
                          <span className="text-xs text-zinc-500 truncate">{bn.to_name}</span>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <div className="w-20">
                            <div className="h-2 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                              <div 
                                className={`h-full rounded-full ${bn.conversion_rate >= 70 ? 'bg-emerald-500' : bn.conversion_rate >= 40 ? 'bg-amber-500' : 'bg-red-500'}`}
                                style={{ width: `${Math.min(bn.conversion_rate, 100)}%` }}
                              />
                            </div>
                          </div>
                          <span className={`text-xs font-medium w-12 text-right ${bn.is_bottleneck ? 'text-red-600' : 'text-zinc-600'}`}>
                            {bn.conversion_rate}%
                          </span>
                          {bn.is_bottleneck && (
                            <TrendingDown className="w-3 h-3 text-red-500" />
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  {bottleneckData.worst_bottleneck && bottleneckData.worst_bottleneck.drop_off_rate > 30 && (
                    <div className="mt-4 p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="text-xs font-medium text-red-700 dark:text-red-300">
                            Critical Bottleneck Detected
                          </p>
                          <p className="text-xs text-red-600 dark:text-red-400 mt-0.5">
                            {bottleneckData.worst_bottleneck.drop_off_rate}% drop-off from {bottleneckData.worst_bottleneck.from_name} to {bottleneckData.worst_bottleneck.to_name}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Sales Forecasting */}
            {forecastData && (
              <Card className="border-zinc-200 dark:border-zinc-800">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Zap className="w-4 h-4 text-amber-500" />
                      Sales Forecast
                    </CardTitle>
                    <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                      {forecastData.total_pipeline} in Pipeline
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  {/* Time-based Forecast */}
                  <div className="grid grid-cols-3 gap-3 mb-4">
                    <div className="p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg text-center">
                      <p className="text-xs text-blue-600 dark:text-blue-400">30 Days</p>
                      <p className="text-xl font-bold text-blue-700 dark:text-blue-300">{forecastData.time_based_forecast?.['30_days']?.deals || 0}</p>
                      <p className="text-xs text-blue-500">{formatCurrency(forecastData.time_based_forecast?.['30_days']?.value || 0)}</p>
                    </div>
                    <div className="p-3 bg-indigo-50 dark:bg-indigo-950/30 rounded-lg text-center">
                      <p className="text-xs text-indigo-600 dark:text-indigo-400">60 Days</p>
                      <p className="text-xl font-bold text-indigo-700 dark:text-indigo-300">{forecastData.time_based_forecast?.['60_days']?.deals || 0}</p>
                      <p className="text-xs text-indigo-500">{formatCurrency(forecastData.time_based_forecast?.['60_days']?.value || 0)}</p>
                    </div>
                    <div className="p-3 bg-purple-50 dark:bg-purple-950/30 rounded-lg text-center">
                      <p className="text-xs text-purple-600 dark:text-purple-400">90 Days</p>
                      <p className="text-xl font-bold text-purple-700 dark:text-purple-300">{forecastData.time_based_forecast?.['90_days']?.deals || 0}</p>
                      <p className="text-xs text-purple-500">{formatCurrency(forecastData.time_based_forecast?.['90_days']?.value || 0)}</p>
                    </div>
                  </div>
                  
                  {/* Weighted Summary */}
                  <div className="p-3 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs text-emerald-600 dark:text-emerald-400">Expected Pipeline Value</p>
                        <p className="text-lg font-bold text-emerald-700 dark:text-emerald-300">
                          {formatCurrency(forecastData.weighted_summary?.expected_value || 0)}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-emerald-600 dark:text-emerald-400">Expected Deals</p>
                        <p className="text-lg font-bold text-emerald-700 dark:text-emerald-300">
                          {forecastData.weighted_summary?.expected_deals || 0}
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  {/* Insights */}
                  {forecastData.insights?.length > 0 && (
                    <div className="mt-3 space-y-1">
                      {forecastData.insights.filter(Boolean).slice(0, 2).map((insight, i) => (
                        <p key={i} className="text-xs text-zinc-500 dark:text-zinc-400 flex items-start gap-1">
                          <span className="text-amber-500">•</span> {insight}
                        </p>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Advanced Analytics Row */}
          <div className="grid grid-cols-3 gap-6">
            {/* Time-in-Stage */}
            {timeInStageData && (
              <Card className="border-zinc-200 dark:border-zinc-800">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Clock className="w-4 h-4 text-blue-500" />
                      Time in Stage
                    </CardTitle>
                    <Badge variant="outline" className="text-xs">
                      {timeInStageData.overall_metrics?.avg_total_days || 0} days avg
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {timeInStageData.stages?.filter(s => s.avg_days !== null).slice(0, 6).map((stage, i) => (
                      <div key={i} className="flex items-center justify-between">
                        <span className="text-xs text-zinc-600 dark:text-zinc-400">{stage.name}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                            <div 
                              className={`h-full rounded-full ${stage.avg_days <= 5 ? 'bg-emerald-500' : stage.avg_days <= 10 ? 'bg-amber-500' : 'bg-red-500'}`}
                              style={{ width: `${Math.min((stage.avg_days / 14) * 100, 100)}%` }}
                            />
                          </div>
                          <span className={`text-xs font-medium w-14 text-right ${stage.is_slow ? 'text-red-600' : 'text-zinc-600'}`}>
                            {stage.avg_days} days
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                  {timeInStageData.overall_metrics?.slowest_stage && (
                    <p className="text-xs text-amber-600 mt-3 pt-2 border-t border-zinc-100 dark:border-zinc-800">
                      Slowest: {timeInStageData.overall_metrics.slowest_stage} ({timeInStageData.overall_metrics.slowest_stage_days} days)
                    </p>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Win/Loss Analysis */}
            {winLossData && (
              <Card className="border-zinc-200 dark:border-zinc-800">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                      <PieChart className="w-4 h-4 text-purple-500" />
                      Win/Loss Analysis
                    </CardTitle>
                    <Badge className={winLossData.summary?.win_rate >= 50 ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}>
                      {winLossData.summary?.win_rate || 0}% Win Rate
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-4 gap-2 mb-3">
                    <div className="text-center p-2 bg-emerald-50 dark:bg-emerald-950/30 rounded-lg">
                      <p className="text-lg font-bold text-emerald-600">{winLossData.summary?.won || 0}</p>
                      <p className="text-[10px] text-emerald-500">Won</p>
                    </div>
                    <div className="text-center p-2 bg-red-50 dark:bg-red-950/30 rounded-lg">
                      <p className="text-lg font-bold text-red-600">{winLossData.summary?.lost || 0}</p>
                      <p className="text-[10px] text-red-500">Lost</p>
                    </div>
                    <div className="text-center p-2 bg-amber-50 dark:bg-amber-950/30 rounded-lg">
                      <p className="text-lg font-bold text-amber-600">{winLossData.summary?.stale_30_days || 0}</p>
                      <p className="text-[10px] text-amber-500">Stale</p>
                    </div>
                    <div className="text-center p-2 bg-blue-50 dark:bg-blue-950/30 rounded-lg">
                      <p className="text-lg font-bold text-blue-600">{winLossData.summary?.active || 0}</p>
                      <p className="text-[10px] text-blue-500">Active</p>
                    </div>
                  </div>
                  
                  {winLossData.at_risk?.count > 0 && (
                    <div className="p-2 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg">
                      <p className="text-xs font-medium text-amber-700 dark:text-amber-300 mb-1">
                        ⚠️ {winLossData.at_risk.count} leads at risk (30+ days stale)
                      </p>
                      {winLossData.at_risk.leads?.slice(0, 2).map((lead, i) => (
                        <p key={i} className="text-[10px] text-amber-600">
                          • {lead.company} (stuck at {lead.stale_at_stage})
                        </p>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Velocity Metrics */}
            {velocityData && (
              <Card className="border-zinc-200 dark:border-zinc-800">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Zap className="w-4 h-4 text-cyan-500" />
                      Sales Velocity
                    </CardTitle>
                    <Badge variant="outline" className="text-xs">
                      {velocityData.summary?.completed_deals || 0} deals
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-center mb-4">
                    <p className="text-3xl font-bold text-cyan-600">
                      {velocityData.summary?.avg_days_to_close || '-'}
                    </p>
                    <p className="text-xs text-zinc-500">Avg Days to Close</p>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2 mb-3">
                    <div className="text-center p-2 bg-emerald-50 dark:bg-emerald-950/30 rounded-lg">
                      <p className="text-sm font-bold text-emerald-600">{velocityData.summary?.min_days || '-'}</p>
                      <p className="text-[10px] text-emerald-500">Fastest</p>
                    </div>
                    <div className="text-center p-2 bg-red-50 dark:bg-red-950/30 rounded-lg">
                      <p className="text-sm font-bold text-red-600">{velocityData.summary?.max_days || '-'}</p>
                      <p className="text-[10px] text-red-500">Slowest</p>
                    </div>
                  </div>
                  
                  {velocityData.fastest_deal && (
                    <p className="text-xs text-zinc-500">
                      ⚡ Fastest: {velocityData.fastest_deal.company} ({velocityData.fastest_deal.days} days)
                    </p>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'New Lead', href: '/leads', icon: Users, color: 'bg-blue-600 hover:bg-blue-700' },
          { label: 'View Pipeline', href: '/leads', icon: TrendingUp, color: 'bg-indigo-600 hover:bg-indigo-700' },
          { label: 'Kickoff Requests', href: '/kickoff-requests', icon: Briefcase, color: 'bg-amber-600 hover:bg-amber-700' },
          { label: isManager ? 'Team Dashboard' : 'My Leads', href: isManager ? '/manager-leads-dashboard' : '/leads', icon: BarChart3, color: 'bg-emerald-600 hover:bg-emerald-700' },
        ].map((action, i) => (
          <Link key={i} to={action.href}>
            <Card className="border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors cursor-pointer">
              <CardContent className="pt-4 pb-4 flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg ${action.color} flex items-center justify-center transition-colors`}>
                  <action.icon className="w-5 h-5 text-white" />
                </div>
                <span className="font-medium text-zinc-700 dark:text-zinc-300">{action.label}</span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default SalesDashboard;
