import React, { useState, useEffect, useContext } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { 
  FileSpreadsheet, FileText, Download, Eye, Search, 
  BarChart3, Users, Building2, DollarSign, Briefcase,
  TrendingUp, Clock, CheckCircle, Filter, ChevronDown
} from 'lucide-react';
import { toast } from 'sonner';

const CATEGORY_ICONS = {
  'Sales': TrendingUp,
  'Finance': DollarSign,
  'HR': Users,
  'Operations': Briefcase
};

const CATEGORY_COLORS = {
  'Sales': 'bg-blue-50 text-blue-700 border-blue-200',
  'Finance': 'bg-emerald-50 text-emerald-700 border-emerald-200',
  'HR': 'bg-purple-50 text-purple-700 border-purple-200',
  'Operations': 'bg-amber-50 text-amber-700 border-amber-200'
};

const Reports = () => {
  const { user } = useContext(AuthContext);
  const [searchParams] = useSearchParams();
  const [reports, setReports] = useState([]);
  const [reportsByCategory, setReportsByCategory] = useState({});
  const [categories, setCategories] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCategory, setFilterCategory] = useState(() => {
    const cat = searchParams.get('category');
    if (!cat) return '';
    const categoryMap = { sales: 'Sales', hr: 'HR', operations: 'Operations', finance: 'Finance' };
    return categoryMap[cat.toLowerCase()] || '';
  });
  
  // Preview dialog
  const [previewDialog, setPreviewDialog] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  
  // Download state
  const [downloading, setDownloading] = useState({});

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [reportsRes, categoriesRes] = await Promise.all([
        axios.get(`${API}/reports`),
        axios.get(`${API}/reports/categories`)
      ]);
      
      setReports(reportsRes.data.reports || []);
      setReportsByCategory(reportsRes.data.by_category || {});
      setCategories(categoriesRes.data || []);
      
      // Try to get stats (may fail for non-admin/manager)
      try {
        const statsRes = await axios.get(`${API}/reports/stats`);
        setStats(statsRes.data);
      } catch (e) {
        console.log('Stats not available for this role');
      }
    } catch (error) {
      console.error('Error fetching reports:', error);
      toast.error('Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = async (reportId) => {
    setPreviewLoading(true);
    setPreviewDialog(true);
    
    try {
      const res = await axios.get(`${API}/reports/${reportId}/preview`);
      setPreviewData(res.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to load preview');
      setPreviewDialog(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleDownload = async (reportId, format) => {
    const key = `${reportId}_${format}`;
    setDownloading(prev => ({ ...prev, [key]: true }));
    
    try {
      const res = await axios.post(
        `${API}/reports/generate`,
        { report_id: reportId, format },
        { responseType: 'blob' }
      );
      
      // Create download link
      const blob = new Blob([res.data], { 
        type: format === 'excel' 
          ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
          : 'application/pdf'
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${reportId}_${new Date().toISOString().split('T')[0]}.${format === 'excel' ? 'xlsx' : 'pdf'}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success(`${format.toUpperCase()} downloaded successfully`);
    } catch (error) {
      toast.error('Failed to download report');
    } finally {
      setDownloading(prev => ({ ...prev, [key]: false }));
    }
  };

  const filteredReports = reports.filter(report => {
    const matchesSearch = !searchTerm || 
      report.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      report.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = !filterCategory || report.category === filterCategory;
    return matchesSearch && matchesCategory;
  });

  // Group filtered reports by category
  const groupedReports = {};
  filteredReports.forEach(report => {
    if (!groupedReports[report.category]) {
      groupedReports[report.category] = [];
    }
    groupedReports[report.category].push(report);
  });

  if (loading) {
    return <div className="flex items-center justify-center h-96"><div className="text-zinc-500">Loading reports...</div></div>;
  }

  return (
    <div data-testid="reports-page">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
          Reports & Analytics
        </h1>
        <p className="text-zinc-500">Generate and download analytical reports</p>
      </div>

      {/* Quick Stats (Admin/Manager only) */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 mb-6">
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-3">
              <p className="text-xs uppercase text-zinc-500">Leads</p>
              <p className="text-xl font-semibold text-zinc-950">{stats.leads}</p>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-3">
              <p className="text-xs uppercase text-zinc-500">Clients</p>
              <p className="text-xl font-semibold text-blue-600">{stats.clients}</p>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-3">
              <p className="text-xs uppercase text-zinc-500">Employees</p>
              <p className="text-xl font-semibold text-purple-600">{stats.employees}</p>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-3">
              <p className="text-xs uppercase text-zinc-500">Projects</p>
              <p className="text-xl font-semibold text-amber-600">{stats.projects}</p>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-3">
              <p className="text-xs uppercase text-zinc-500">Revenue</p>
              <p className="text-xl font-semibold text-emerald-600">₹{(stats.total_revenue / 100000).toFixed(1)}L</p>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-3">
              <p className="text-xs uppercase text-zinc-500">Pending Approvals</p>
              <p className="text-xl font-semibold text-yellow-600">{stats.pending_approvals}</p>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-3">
              <p className="text-xs uppercase text-zinc-500">Pending Exp.</p>
              <p className="text-xl font-semibold text-red-600">₹{(stats.pending_expenses / 1000).toFixed(0)}K</p>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-3">
              <p className="text-xs uppercase text-zinc-500">Approved Exp.</p>
              <p className="text-xl font-semibold text-green-600">₹{(stats.approved_expenses / 1000).toFixed(0)}K</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <Input
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search reports..."
            className="pl-10 rounded-sm"
          />
        </div>
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
        >
          <option value="">All Categories</option>
          {categories.map(cat => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>
        <div className="text-sm text-zinc-500">
          {filteredReports.length} report{filteredReports.length !== 1 ? 's' : ''} available
        </div>
      </div>

      {/* Reports by Category */}
      {Object.entries(groupedReports).map(([category, categoryReports]) => {
        const CategoryIcon = CATEGORY_ICONS[category] || BarChart3;
        const colorClass = CATEGORY_COLORS[category] || 'bg-zinc-50 text-zinc-700 border-zinc-200';
        
        return (
          <div key={category} className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <div className={`p-2 rounded-sm ${colorClass.split(' ')[0]}`}>
                <CategoryIcon className={`w-5 h-5 ${colorClass.split(' ')[1]}`} />
              </div>
              <h2 className="text-lg font-semibold text-zinc-950">{category}</h2>
              <span className="text-sm text-zinc-400">({categoryReports.length})</span>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {categoryReports.map(report => (
                <Card 
                  key={report.id} 
                  className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors"
                  data-testid={`report-card-${report.id}`}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-medium text-zinc-900 mb-1">{report.name}</h3>
                        <p className="text-sm text-zinc-500">{report.description}</p>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded border ${colorClass}`}>
                        {report.category}
                      </span>
                    </div>
                    
                    <div className="flex items-center gap-2 pt-3 border-t border-zinc-100">
                      <Button 
                        onClick={() => handlePreview(report.id)} 
                        variant="ghost" 
                        size="sm" 
                        className="flex-1 rounded-sm"
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        Preview
                      </Button>
                      <Button 
                        onClick={() => handleDownload(report.id, 'excel')}
                        disabled={downloading[`${report.id}_excel`]}
                        variant="ghost" 
                        size="sm" 
                        className="rounded-sm text-emerald-600 hover:text-emerald-700"
                      >
                        <FileSpreadsheet className="w-4 h-4 mr-1" />
                        {downloading[`${report.id}_excel`] ? '...' : 'Excel'}
                      </Button>
                      <Button 
                        onClick={() => handleDownload(report.id, 'pdf')}
                        disabled={downloading[`${report.id}_pdf`]}
                        variant="ghost" 
                        size="sm" 
                        className="rounded-sm text-red-600 hover:text-red-700"
                      >
                        <FileText className="w-4 h-4 mr-1" />
                        {downloading[`${report.id}_pdf`] ? '...' : 'PDF'}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        );
      })}

      {filteredReports.length === 0 && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-12 text-center">
            <BarChart3 className="w-12 h-12 text-zinc-300 mx-auto mb-4" />
            <p className="text-zinc-500">
              {reports.length === 0 
                ? 'No reports available for your role.' 
                : 'No reports match your search criteria.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Preview Dialog */}
      <Dialog open={previewDialog} onOpenChange={setPreviewDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              {previewData?.report_info?.name || 'Report Preview'}
            </DialogTitle>
          </DialogHeader>
          
          {previewLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-zinc-500">Loading preview...</div>
            </div>
          ) : previewData?.data ? (
            <div className="flex-1 overflow-auto">
              {/* Summary Section */}
              {previewData.data.summary && (
                <div className="mb-4 p-4 bg-zinc-50 rounded-sm">
                  <h4 className="font-medium text-zinc-950 mb-2">Summary</h4>
                  <div className="flex flex-wrap gap-4">
                    {Object.entries(previewData.data.summary).map(([key, value]) => (
                      <div key={key} className="text-sm">
                        <span className="text-zinc-500">{key}: </span>
                        <span className="font-medium text-zinc-900">
                          {typeof value === 'object' 
                            ? JSON.stringify(value) 
                            : value}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Data Table */}
              {previewData.data.rows?.length > 0 && (
                <div className="border border-zinc-200 rounded-sm overflow-auto max-h-96">
                  <table className="w-full text-sm">
                    <thead className="bg-zinc-900 text-white sticky top-0">
                      <tr>
                        {previewData.data.columns?.map((col, idx) => (
                          <th key={idx} className="px-3 py-2 text-left font-medium">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.data.rows.slice(0, 50).map((row, rowIdx) => (
                        <tr key={rowIdx} className={rowIdx % 2 === 0 ? 'bg-white' : 'bg-zinc-50'}>
                          {previewData.data.columns?.map((col, colIdx) => (
                            <td key={colIdx} className="px-3 py-2 border-t border-zinc-100">
                              {row[col] ?? '-'}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {previewData.data.rows.length > 50 && (
                    <div className="text-center py-2 text-sm text-zinc-500 bg-zinc-50 border-t border-zinc-200">
                      Showing 50 of {previewData.data.rows.length} rows. Download for full data.
                    </div>
                  )}
                </div>
              )}
              
              {/* Download buttons */}
              <div className="flex gap-3 mt-4 pt-4 border-t border-zinc-100">
                <Button 
                  onClick={() => handleDownload(previewData.report_id, 'excel')}
                  disabled={downloading[`${previewData.report_id}_excel`]}
                  className="bg-emerald-600 text-white hover:bg-emerald-700 rounded-sm"
                >
                  <FileSpreadsheet className="w-4 h-4 mr-2" />
                  Download Excel
                </Button>
                <Button 
                  onClick={() => handleDownload(previewData.report_id, 'pdf')}
                  disabled={downloading[`${previewData.report_id}_pdf`]}
                  className="bg-red-600 text-white hover:bg-red-700 rounded-sm"
                >
                  <FileText className="w-4 h-4 mr-2" />
                  Download PDF
                </Button>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-zinc-500">
              No data available for preview
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Reports;
