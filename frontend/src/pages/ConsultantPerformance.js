import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Plus, CheckCircle, XCircle, Clock, Trash2, Shield, Star, Target } from 'lucide-react';
import { toast } from 'sonner';

const DEFAULT_METRICS = [
  { name: 'SOW Timely Delivery', key: 'sow_delivery', weight: 20, description: 'SOW items delivered on time' },
  { name: 'Roadmap Achievement', key: 'roadmap_achievement', weight: 20, description: 'Roadmap milestones completed vs planned' },
  { name: 'Records Timeliness', key: 'records_timeliness', weight: 15, description: 'Timely update of project records' },
  { name: 'SOW Quality Score', key: 'sow_quality', weight: 25, description: 'Quality rating of SOW documents by RM' },
  { name: 'Meeting Adherence', key: 'meeting_adherence', weight: 20, description: 'Meeting schedule and date adherence' }
];

const STATUS_STYLES = {
  pending_approval: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  rejected: 'bg-red-50 text-red-700 border-red-200'
};

function ConsultantPerformance() {
  const { user } = useContext(AuthContext);
  const [activeTab, setActiveTab] = useState('metrics');
  const [projects, setProjects] = useState([]);
  const [configs, setConfigs] = useState([]);
  const [scores, setScores] = useState([]);
  const [consultants, setConsultants] = useState([]);
  const [summary, setSummary] = useState([]);
  const [loading, setLoading] = useState(true);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [scoreDialogOpen, setScoreDialogOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState('');

  // Metric config form
  const [configForm, setConfigForm] = useState({ project_id: '', project_name: '', metrics: DEFAULT_METRICS.map(function(m) { return { ...m }; }) });
  // Score form
  const [scoreForm, setScoreForm] = useState({ project_id: '', consultant_id: '', month: '', scores: [] });

  const isAdmin = user?.role === 'admin';
  const canConfigMetrics = ['admin', 'principal_consultant', 'project_manager'].includes(user?.role);
  const canRate = ['admin', 'manager', 'project_manager', 'principal_consultant'].includes(user?.role);

  useEffect(function() { fetchData(); }, []);

  function fetchData() {
    Promise.all([
      axios.get(API + '/projects'),
      axios.get(API + '/performance-metrics'),
      axios.get(API + '/performance-scores'),
      axios.get(API + '/users'),
      axios.get(API + '/performance-scores/summary').catch(function() { return { data: [] }; })
    ]).then(function(results) {
      setProjects(results[0].data);
      setConfigs(results[1].data);
      setScores(results[2].data);
      setConsultants(results[3].data);
      setSummary(results[4].data);
    }).catch(function() {
      toast.error('Failed to fetch data');
    }).finally(function() { setLoading(false); });
  }

  function handleCreateConfig(e) {
    e.preventDefault();
    var project = projects.find(function(p) { return p.id === configForm.project_id; });
    axios.post(API + '/performance-metrics', {
      project_id: configForm.project_id,
      project_name: project ? project.name : '',
      metrics: configForm.metrics.filter(function(m) { return m.name; })
    }).then(function() {
      toast.success('Metrics created. Pending admin approval.');
      setConfigDialogOpen(false);
      setConfigForm({ project_id: '', project_name: '', metrics: DEFAULT_METRICS.map(function(m) { return { ...m }; }) });
      fetchData();
    }).catch(function(err) { toast.error(err.response?.data?.detail || 'Failed'); });
  }

  function handleApprove(configId) {
    axios.post(API + '/performance-metrics/' + configId + '/approve').then(function() {
      toast.success('Metrics approved');
      fetchData();
    }).catch(function(err) { toast.error(err.response?.data?.detail || 'Failed'); });
  }

  function handleReject(configId) {
    axios.post(API + '/performance-metrics/' + configId + '/reject').then(function() {
      toast.success('Metrics rejected');
      fetchData();
    }).catch(function(err) { toast.error(err.response?.data?.detail || 'Failed'); });
  }

  function openScoreDialog() {
    setScoreForm({ project_id: '', consultant_id: '', month: new Date().toISOString().slice(0, 7), scores: [] });
    setScoreDialogOpen(true);
  }

  function loadMetricsForScoring(projectId) {
    var config = configs.find(function(c) { return c.project_id === projectId && c.status === 'approved'; });
    if (config) {
      setScoreForm(function(prev) {
        return { ...prev, project_id: projectId, scores: config.metrics.map(function(m) { return { metric_id: m.id, metric_name: m.name, score: 0, comments: '' }; }) };
      });
    } else {
      toast.error('No approved metrics for this project');
      setScoreForm(function(prev) { return { ...prev, project_id: projectId, scores: [] }; });
    }
  }

  function handleSubmitScore(e) {
    e.preventDefault();
    axios.post(API + '/performance-scores', scoreForm).then(function() {
      toast.success('Performance score submitted');
      setScoreDialogOpen(false);
      fetchData();
    }).catch(function(err) { toast.error(err.response?.data?.detail || 'Failed'); });
  }

  function addMetric() {
    setConfigForm({ ...configForm, metrics: [...configForm.metrics, { name: '', key: '', weight: 10, description: '' }] });
  }

  function updateMetric(idx, field, value) {
    var m = [...configForm.metrics];
    m[idx] = { ...m[idx], [field]: field === 'weight' ? parseInt(value) || 0 : value };
    setConfigForm({ ...configForm, metrics: m });
  }

  function removeMetric(idx) {
    if (configForm.metrics.length > 1) {
      setConfigForm({ ...configForm, metrics: configForm.metrics.filter(function(_, i) { return i !== idx; }) });
    }
  }

  var filteredScores = selectedProject ? scores.filter(function(s) { return s.project_id === selectedProject; }) : scores;

  return (
    <div data-testid="consultant-performance-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">Consultant Performance</h1>
          <p className="text-zinc-500">Configure metrics, rate consultants, track performance</p>
        </div>
        <div className="flex gap-2">
          {canConfigMetrics && (
            <Dialog open={configDialogOpen} onOpenChange={setConfigDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" className="rounded-sm" data-testid="config-metrics-btn"><Target className="w-4 h-4 mr-2" /> Configure Metrics</Button>
              </DialogTrigger>
              <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Configure Performance Metrics</DialogTitle>
                  <DialogDescription className="text-zinc-500">Customizable per project. Requires admin approval.</DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreateConfig} className="space-y-4">
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Project *</Label>
                    <select value={configForm.project_id} onChange={function(e) { setConfigForm({ ...configForm, project_id: e.target.value }); }}
                      required className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="config-project">
                      <option value="">Select project</option>
                      {projects.map(function(p) { return <option key={p.id} value={p.id}>{p.name} - {p.client_name}</option>; })}
                    </select>
                  </div>
                  <div className="space-y-3">
                    <Label className="text-sm font-medium text-zinc-950">Metrics (Total weight should = 100)</Label>
                    {configForm.metrics.map(function(m, i) {
                      return (
                        <div key={i} className="grid grid-cols-12 gap-2 items-end">
                          <Input value={m.name} onChange={function(e) { updateMetric(i, 'name', e.target.value); }}
                            placeholder="Metric name" className="rounded-sm border-zinc-200 col-span-4 text-xs h-8" />
                          <Input value={m.description} onChange={function(e) { updateMetric(i, 'description', e.target.value); }}
                            placeholder="Description" className="rounded-sm border-zinc-200 col-span-5 text-xs h-8" />
                          <Input type="number" value={m.weight} onChange={function(e) { updateMetric(i, 'weight', e.target.value); }}
                            className="rounded-sm border-zinc-200 col-span-2 text-xs h-8" min="0" max="100" />
                          <Button type="button" variant="ghost" className="col-span-1 h-8 px-1" onClick={function() { removeMetric(i); }}>
                            <Trash2 className="w-3 h-3 text-red-400" />
                          </Button>
                        </div>
                      );
                    })}
                    <div className="flex items-center justify-between">
                      <Button type="button" variant="outline" size="sm" className="rounded-sm text-xs" onClick={addMetric}><Plus className="w-3 h-3 mr-1" /> Add Metric</Button>
                      <span className="text-xs text-zinc-500">Total: {configForm.metrics.reduce(function(s, m) { return s + (m.weight || 0); }, 0)}%</span>
                    </div>
                  </div>
                  <Button type="submit" data-testid="save-config" className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">Save (Pending Admin Approval)</Button>
                </form>
              </DialogContent>
            </Dialog>
          )}
          {canRate && (
            <Dialog open={scoreDialogOpen} onOpenChange={setScoreDialogOpen}>
              <DialogTrigger asChild>
                <Button className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none" data-testid="rate-btn" onClick={openScoreDialog}><Star className="w-4 h-4 mr-2" /> Rate Consultant</Button>
              </DialogTrigger>
              <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Rate Consultant Performance</DialogTitle>
                  <DialogDescription className="text-zinc-500">Score each metric (0-100)</DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmitScore} className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-zinc-950">Project *</Label>
                      <select value={scoreForm.project_id} onChange={function(e) { loadMetricsForScoring(e.target.value); }}
                        required className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="score-project">
                        <option value="">Select</option>
                        {projects.map(function(p) { return <option key={p.id} value={p.id}>{p.name}</option>; })}
                      </select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-zinc-950">Consultant *</Label>
                      <select value={scoreForm.consultant_id} onChange={function(e) { setScoreForm({ ...scoreForm, consultant_id: e.target.value }); }}
                        required className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="score-consultant">
                        <option value="">Select</option>
                        {consultants.map(function(u) { return <option key={u.id} value={u.id}>{u.full_name}</option>; })}
                      </select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-zinc-950">Month *</Label>
                      <Input type="month" value={scoreForm.month} onChange={function(e) { setScoreForm({ ...scoreForm, month: e.target.value }); }}
                        required className="rounded-sm border-zinc-200" />
                    </div>
                  </div>
                  {scoreForm.scores.length > 0 ? (
                    <div className="space-y-3">
                      {scoreForm.scores.map(function(s, i) {
                        return (
                          <div key={i} className="border border-zinc-200 rounded-sm p-3">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-sm font-medium text-zinc-950">{s.metric_name}</span>
                              <span className="text-lg font-semibold text-zinc-950">{s.score}/100</span>
                            </div>
                            <input type="range" min="0" max="100" value={s.score}
                              onChange={function(e) { var sc = [...scoreForm.scores]; sc[i].score = parseInt(e.target.value); setScoreForm({ ...scoreForm, scores: sc }); }}
                              className="w-full h-2 bg-zinc-200 rounded-lg appearance-none cursor-pointer" />
                            <Input value={s.comments} onChange={function(e) { var sc = [...scoreForm.scores]; sc[i].comments = e.target.value; setScoreForm({ ...scoreForm, scores: sc }); }}
                              placeholder="Comments (optional)" className="rounded-sm border-zinc-200 mt-2 text-xs" />
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-sm text-zinc-500 text-center py-4">Select a project with approved metrics to start scoring</div>
                  )}
                  <Button type="submit" disabled={scoreForm.scores.length === 0} data-testid="submit-score"
                    className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">Submit Score</Button>
                </form>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-zinc-200">
        <button onClick={function() { setActiveTab('metrics'); }} data-testid="tab-metrics"
          className={'px-4 py-2 text-sm font-medium ' + (activeTab === 'metrics' ? 'border-b-2 border-zinc-950 text-zinc-950' : 'text-zinc-500')}>Metrics Config</button>
        <button onClick={function() { setActiveTab('scores'); }} data-testid="tab-scores"
          className={'px-4 py-2 text-sm font-medium ' + (activeTab === 'scores' ? 'border-b-2 border-zinc-950 text-zinc-950' : 'text-zinc-500')}>Scores</button>
        <button onClick={function() { setActiveTab('summary'); }} data-testid="tab-summary"
          className={'px-4 py-2 text-sm font-medium ' + (activeTab === 'summary' ? 'border-b-2 border-zinc-950 text-zinc-950' : 'text-zinc-500')}>Summary</button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="text-zinc-500">Loading...</div></div>
      ) : activeTab === 'metrics' ? (
        /* Metrics Config Tab */
        configs.length === 0 ? (
          <Card className="border-zinc-200 shadow-none rounded-sm"><CardContent className="flex flex-col items-center justify-center h-40">
            <Target className="w-10 h-10 text-zinc-300 mb-3" /><p className="text-zinc-500">No performance metrics configured</p>
          </CardContent></Card>
        ) : (
          <div className="space-y-3">
            {configs.map(function(cfg) {
              return (
                <Card key={cfg.id} className="border-zinc-200 shadow-none rounded-sm" data-testid={'config-' + cfg.id}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <div className="font-medium text-zinc-950">{cfg.project_name || 'Project'}</div>
                        <div className="text-xs text-zinc-500">By {cfg.created_by_name}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={'text-xs px-2 py-1 rounded-sm border ' + (STATUS_STYLES[cfg.status] || STATUS_STYLES.pending_approval)}>
                          {cfg.status === 'pending_approval' ? 'Pending Approval' : cfg.status === 'approved' ? 'Approved' : 'Rejected'}
                        </span>
                        {isAdmin && cfg.status === 'pending_approval' && (
                          <div className="flex gap-1">
                            <Button onClick={function() { handleApprove(cfg.id); }} variant="ghost" size="sm" className="text-emerald-600" data-testid={'approve-' + cfg.id}><CheckCircle className="w-4 h-4" /></Button>
                            <Button onClick={function() { handleReject(cfg.id); }} variant="ghost" size="sm" className="text-red-500" data-testid={'reject-' + cfg.id}><XCircle className="w-4 h-4" /></Button>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="grid grid-cols-5 gap-2">
                      {(cfg.metrics || []).map(function(m) {
                        return (
                          <div key={m.id || m.key} className="bg-zinc-50 rounded-sm p-2 border border-zinc-100">
                            <div className="text-xs font-medium text-zinc-700">{m.name}</div>
                            <div className="text-lg font-semibold text-zinc-950">{m.weight}%</div>
                            <div className="text-[10px] text-zinc-400">{m.description}</div>
                          </div>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )
      ) : activeTab === 'scores' ? (
        /* Scores Tab */
        <div>
          <div className="mb-4">
            <select value={selectedProject} onChange={function(e) { setSelectedProject(e.target.value); }}
              className="h-9 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="filter-project">
              <option value="">All Projects</option>
              {projects.map(function(p) { return <option key={p.id} value={p.id}>{p.name}</option>; })}
            </select>
          </div>
          {filteredScores.length === 0 ? (
            <Card className="border-zinc-200 shadow-none rounded-sm"><CardContent className="flex flex-col items-center justify-center h-40">
              <Star className="w-10 h-10 text-zinc-300 mb-3" /><p className="text-zinc-500">No scores recorded</p>
            </CardContent></Card>
          ) : (
            <div className="border border-zinc-200 rounded-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-zinc-50">
                  <tr>
                    <th className="text-left px-4 py-3 text-xs uppercase text-zinc-500 font-medium">Consultant</th>
                    <th className="text-left px-4 py-3 text-xs uppercase text-zinc-500 font-medium">Month</th>
                    <th className="text-center px-4 py-3 text-xs uppercase text-zinc-500 font-medium">Overall</th>
                    <th className="text-left px-4 py-3 text-xs uppercase text-zinc-500 font-medium">Rated By</th>
                    <th className="text-left px-4 py-3 text-xs uppercase text-zinc-500 font-medium">Breakdown</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredScores.map(function(s) {
                    var scoreColor = s.overall_score >= 80 ? 'text-emerald-700 bg-emerald-50' : s.overall_score >= 60 ? 'text-yellow-700 bg-yellow-50' : 'text-red-700 bg-red-50';
                    return (
                      <tr key={s.id} className="border-t border-zinc-100 hover:bg-zinc-50" data-testid={'score-row-' + s.id}>
                        <td className="px-4 py-3 font-medium text-zinc-950">{s.consultant_name}</td>
                        <td className="px-4 py-3 text-zinc-700">{s.month}</td>
                        <td className="px-4 py-3 text-center"><span className={'text-sm font-bold px-2 py-1 rounded-sm ' + scoreColor}>{s.overall_score}%</span></td>
                        <td className="px-4 py-3 text-zinc-600">{s.rated_by_name}</td>
                        <td className="px-4 py-3">
                          <div className="flex gap-1 flex-wrap">
                            {(s.scores || []).map(function(sc, i) {
                              return <span key={i} className="text-[10px] px-1.5 py-0.5 bg-zinc-100 text-zinc-600 rounded-sm">{sc.metric_name}: {sc.score}</span>;
                            })}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        /* Summary Tab */
        summary.length === 0 ? (
          <Card className="border-zinc-200 shadow-none rounded-sm"><CardContent className="flex flex-col items-center justify-center h-40">
            <Target className="w-10 h-10 text-zinc-300 mb-3" /><p className="text-zinc-500">No performance data yet</p>
          </CardContent></Card>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {summary.map(function(s) {
              var avgColor = s.avg_score >= 80 ? 'text-emerald-700' : s.avg_score >= 60 ? 'text-yellow-700' : 'text-red-600';
              return (
                <Card key={s.consultant_id} className="border-zinc-200 shadow-none rounded-sm" data-testid={'summary-' + s.consultant_id}>
                  <CardContent className="p-4">
                    <div className="font-medium text-zinc-950 mb-1">{s.consultant_name}</div>
                    <div className="text-xs text-zinc-500 mb-3">{s.months_rated} months rated</div>
                    <div className={'text-3xl font-bold mb-2 ' + avgColor}>{s.avg_score}%</div>
                    <div className="w-full bg-zinc-200 rounded-full h-2">
                      <div className={'h-2 rounded-full ' + (s.avg_score >= 80 ? 'bg-emerald-500' : s.avg_score >= 60 ? 'bg-yellow-500' : 'bg-red-500')} style={{ width: s.avg_score + '%' }} />
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )
      )}
    </div>
  );
}

export default ConsultantPerformance;
