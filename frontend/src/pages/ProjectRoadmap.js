import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Plus, Send, CheckCircle, Clock, AlertCircle, Trash2, Calendar, Columns3, List } from 'lucide-react';
import { toast } from 'sonner';

const ITEM_STATUSES = [
  { value: 'not_started', label: 'Not Started', color: 'bg-zinc-100 text-zinc-600' },
  { value: 'in_progress', label: 'In Progress', color: 'bg-blue-100 text-blue-700' },
  { value: 'completed', label: 'Completed', color: 'bg-emerald-100 text-emerald-700' },
  { value: 'delayed', label: 'Delayed', color: 'bg-red-100 text-red-700' }
];

function ProjectRoadmap() {
  const { user } = useContext(AuthContext);
  const [roadmaps, setRoadmaps] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedRoadmap, setSelectedRoadmap] = useState(null);
  const [viewMode, setViewMode] = useState('table');
  const [formData, setFormData] = useState({ project_id: '', title: '', phases: [{ id: '', month: '', title: '', items: [{ id: '', title: '', description: '', assigned_to: '', status: 'not_started', due_date: '' }] }] });

  const canCreate = ['admin', 'project_manager', 'manager', 'principal_consultant'].includes(user?.role);

  useEffect(function() { fetchData(); }, []);

  function fetchData() {
    Promise.all([
      axios.get(API + '/roadmaps'),
      axios.get(API + '/projects')
    ]).then(function(results) {
      setRoadmaps(results[0].data);
      setProjects(results[1].data);
    }).catch(function() {
      toast.error('Failed to fetch data');
    }).finally(function() {
      setLoading(false);
    });
  }

  function handleCreate(e) {
    e.preventDefault();
    var project = projects.find(function(p) { return p.id === formData.project_id; });
    axios.post(API + '/roadmaps', {
      project_id: formData.project_id,
      title: formData.title || ('Roadmap - ' + (project ? project.name : '')),
      phases: formData.phases.filter(function(p) { return p.month; })
    }).then(function() {
      toast.success('Roadmap created');
      setDialogOpen(false);
      setFormData({ project_id: '', title: '', phases: [{ id: '', month: '', title: '', items: [{ id: '', title: '', description: '', assigned_to: '', status: 'not_started', due_date: '' }] }] });
      fetchData();
    }).catch(function(err) {
      toast.error(err.response?.data?.detail || 'Failed to create');
    });
  }

  function handleSubmitToClient(roadmapId) {
    axios.post(API + '/roadmaps/' + roadmapId + '/submit-to-client').then(function() {
      toast.success('Roadmap submitted to client');
      fetchData();
      if (selectedRoadmap && selectedRoadmap.id === roadmapId) {
        setSelectedRoadmap(function(prev) { return { ...prev, status: 'submitted_to_client', submitted_to_client: true }; });
      }
    }).catch(function() { toast.error('Failed to submit'); });
  }

  function handleItemStatus(roadmapId, itemId, status) {
    axios.patch(API + '/roadmaps/' + roadmapId + '/items/' + itemId + '/status', { status: status }).then(function() {
      toast.success('Status updated');
      fetchData();
      if (selectedRoadmap) {
        axios.get(API + '/roadmaps/' + roadmapId).then(function(res) { setSelectedRoadmap(res.data); });
      }
    }).catch(function() { toast.error('Failed to update'); });
  }

  function addPhase() {
    setFormData({ ...formData, phases: [...formData.phases, { id: '', month: '', title: '', items: [{ id: '', title: '', description: '', assigned_to: '', status: 'not_started', due_date: '' }] }] });
  }

  function addPhaseItem(phaseIdx) {
    var phases = [...formData.phases];
    phases[phaseIdx].items.push({ id: '', title: '', description: '', assigned_to: '', status: 'not_started', due_date: '' });
    setFormData({ ...formData, phases: phases });
  }

  function getStatusBadge(status) {
    var s = ITEM_STATUSES.find(function(st) { return st.value === status; });
    return s ? s.color : 'bg-zinc-100 text-zinc-600';
  }

  // Kanban columns from selected roadmap
  function getAllItems() {
    if (!selectedRoadmap) return [];
    var items = [];
    (selectedRoadmap.phases || []).forEach(function(phase) {
      (phase.items || []).forEach(function(item) {
        items.push({ ...item, phase_month: phase.month, phase_title: phase.title });
      });
    });
    return items;
  }

  var kanbanItems = getAllItems();
  var kanbanColumns = ITEM_STATUSES.map(function(s) {
    return { ...s, items: kanbanItems.filter(function(i) { return i.status === s.value; }) };
  });

  return (
    <div data-testid="project-roadmap-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">Project Roadmap</h1>
          <p className="text-zinc-500">Monthly phased plans linked to SOW, shared with clients</p>
        </div>
        {canCreate && (
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button data-testid="create-roadmap-btn" className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                <Plus className="w-4 h-4 mr-2" /> Create Roadmap
              </Button>
            </DialogTrigger>
            <DialogContent className="border-zinc-200 rounded-sm max-w-3xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Create Project Roadmap</DialogTitle>
                <DialogDescription className="text-zinc-500">Define monthly phases with deliverables</DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreate} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Project *</Label>
                    <select value={formData.project_id} onChange={function(e) { setFormData({ ...formData, project_id: e.target.value }); }}
                      required className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="roadmap-project">
                      <option value="">Select project</option>
                      {projects.map(function(p) { return <option key={p.id} value={p.id}>{p.name} - {p.client_name}</option>; })}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Title</Label>
                    <Input value={formData.title} onChange={function(e) { setFormData({ ...formData, title: e.target.value }); }}
                      placeholder="Roadmap title" className="rounded-sm border-zinc-200" data-testid="roadmap-title" />
                  </div>
                </div>
                {/* Phases */}
                <div className="space-y-4">
                  <Label className="text-sm font-medium text-zinc-950">Monthly Phases</Label>
                  {formData.phases.map(function(phase, pi) {
                    return (
                      <div key={pi} className="border border-zinc-200 rounded-sm p-3 space-y-3">
                        <div className="grid grid-cols-3 gap-3">
                          <Input type="month" value={phase.month} onChange={function(e) { var p = [...formData.phases]; p[pi].month = e.target.value; setFormData({ ...formData, phases: p }); }}
                            className="rounded-sm border-zinc-200" placeholder="Month" />
                          <Input value={phase.title} onChange={function(e) { var p = [...formData.phases]; p[pi].title = e.target.value; setFormData({ ...formData, phases: p }); }}
                            className="rounded-sm border-zinc-200 col-span-2" placeholder="Phase title (e.g., Discovery)" />
                        </div>
                        {phase.items.map(function(item, ii) {
                          return (
                            <div key={ii} className="grid grid-cols-12 gap-2 ml-4">
                              <Input value={item.title} onChange={function(e) { var p = [...formData.phases]; p[pi].items[ii].title = e.target.value; setFormData({ ...formData, phases: p }); }}
                                placeholder="Item title" className="rounded-sm border-zinc-200 col-span-5 text-xs h-8" />
                              <Input value={item.assigned_to} onChange={function(e) { var p = [...formData.phases]; p[pi].items[ii].assigned_to = e.target.value; setFormData({ ...formData, phases: p }); }}
                                placeholder="Assigned to" className="rounded-sm border-zinc-200 col-span-3 text-xs h-8" />
                              <Input type="date" value={item.due_date} onChange={function(e) { var p = [...formData.phases]; p[pi].items[ii].due_date = e.target.value; setFormData({ ...formData, phases: p }); }}
                                className="rounded-sm border-zinc-200 col-span-3 text-xs h-8" />
                              <Button type="button" variant="ghost" className="col-span-1 h-8 px-1" onClick={function() { var p = [...formData.phases]; p[pi].items.splice(ii, 1); if (p[pi].items.length === 0) p[pi].items = [{ id: '', title: '', description: '', assigned_to: '', status: 'not_started', due_date: '' }]; setFormData({ ...formData, phases: p }); }}>
                                <Trash2 className="w-3 h-3 text-red-400" />
                              </Button>
                            </div>
                          );
                        })}
                        <Button type="button" variant="outline" size="sm" className="rounded-sm text-xs ml-4" onClick={function() { addPhaseItem(pi); }}>
                          <Plus className="w-3 h-3 mr-1" /> Add Item
                        </Button>
                      </div>
                    );
                  })}
                  <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={addPhase}>
                    <Plus className="w-4 h-4 mr-1" /> Add Phase
                  </Button>
                </div>
                <Button type="submit" data-testid="save-roadmap" className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">Create Roadmap</Button>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="text-zinc-500">Loading...</div></div>
      ) : !selectedRoadmap ? (
        /* Roadmap List */
        roadmaps.length === 0 ? (
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="flex flex-col items-center justify-center h-40">
              <Calendar className="w-10 h-10 text-zinc-300 mb-3" />
              <p className="text-zinc-500">No roadmaps created yet</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {roadmaps.map(function(rm) {
              var totalItems = 0, completed = 0;
              (rm.phases || []).forEach(function(p) { (p.items || []).forEach(function(i) { totalItems++; if (i.status === 'completed') completed++; }); });
              var pct = totalItems > 0 ? Math.round(completed / totalItems * 100) : 0;
              return (
                <Card key={rm.id} className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors cursor-pointer" data-testid={'roadmap-card-' + rm.id}
                  onClick={function() { axios.get(API + '/roadmaps/' + rm.id).then(function(res) { setSelectedRoadmap(res.data); }); }}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-zinc-950">{rm.title}</div>
                        <div className="text-sm text-zinc-500">{rm.project_name} | {rm.client_name}</div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <div className="text-sm font-medium text-zinc-950">{pct}%</div>
                          <div className="w-20 bg-zinc-200 rounded-full h-1.5 mt-1">
                            <div className={'h-1.5 rounded-full ' + (pct >= 100 ? 'bg-emerald-600' : pct >= 50 ? 'bg-yellow-500' : 'bg-zinc-400')} style={{ width: pct + '%' }} />
                          </div>
                        </div>
                        {rm.submitted_to_client ? (
                          <span className="text-xs px-2 py-1 bg-emerald-50 text-emerald-700 rounded-sm flex items-center gap-1"><Send className="w-3 h-3" /> Sent</span>
                        ) : (
                          <span className="text-xs px-2 py-1 bg-zinc-100 text-zinc-600 rounded-sm">{rm.status}</span>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )
      ) : (
        /* Roadmap Detail View */
        <div>
          <div className="flex items-center justify-between mb-6">
            <div>
              <Button variant="ghost" className="mb-2 text-zinc-500" onClick={function() { setSelectedRoadmap(null); }}>Back to list</Button>
              <h2 className="text-xl font-semibold text-zinc-950">{selectedRoadmap.title}</h2>
              <p className="text-sm text-zinc-500">{selectedRoadmap.project_name} | {selectedRoadmap.client_name}</p>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex border border-zinc-200 rounded-sm">
                <button onClick={function() { setViewMode('table'); }} className={'px-3 py-1.5 text-xs ' + (viewMode === 'table' ? 'bg-zinc-950 text-white' : 'text-zinc-600')} data-testid="view-table">
                  <List className="w-3.5 h-3.5" />
                </button>
                <button onClick={function() { setViewMode('kanban'); }} className={'px-3 py-1.5 text-xs ' + (viewMode === 'kanban' ? 'bg-zinc-950 text-white' : 'text-zinc-600')} data-testid="view-kanban">
                  <Columns3 className="w-3.5 h-3.5" />
                </button>
              </div>
              {canCreate && !selectedRoadmap.submitted_to_client && (
                <Button onClick={function() { handleSubmitToClient(selectedRoadmap.id); }} variant="outline" className="rounded-sm" data-testid="submit-to-client-btn">
                  <Send className="w-4 h-4 mr-2" /> Submit to Client
                </Button>
              )}
            </div>
          </div>

          {viewMode === 'kanban' ? (
            <div className="grid grid-cols-4 gap-4" data-testid="kanban-view">
              {kanbanColumns.map(function(col) {
                return (
                  <div key={col.value} className="space-y-2">
                    <div className={'text-xs font-semibold uppercase tracking-wide px-2 py-1 rounded-sm ' + col.color}>{col.label} ({col.items.length})</div>
                    {col.items.map(function(item) {
                      return (
                        <Card key={item.id} className="border-zinc-200 shadow-none rounded-sm" data-testid={'kanban-item-' + item.id}>
                          <CardContent className="p-3">
                            <div className="text-sm font-medium text-zinc-950 mb-1">{item.title}</div>
                            <div className="text-xs text-zinc-500">{item.phase_title} | {item.phase_month}</div>
                            {item.assigned_to && <div className="text-xs text-zinc-400 mt-1">{item.assigned_to}</div>}
                            <select value={item.status} onChange={function(e) { handleItemStatus(selectedRoadmap.id, item.id, e.target.value); }}
                              className="mt-2 w-full h-7 px-2 rounded-sm border border-zinc-200 bg-white text-xs">
                              {ITEM_STATUSES.map(function(s) { return <option key={s.value} value={s.value}>{s.label}</option>; })}
                            </select>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          ) : (
            /* Table View */
            <div className="space-y-4" data-testid="table-view">
              {(selectedRoadmap.phases || []).map(function(phase) {
                var phaseCompleted = (phase.items || []).filter(function(i) { return i.status === 'completed'; }).length;
                return (
                  <div key={phase.id} className="border border-zinc-200 rounded-sm overflow-hidden">
                    <div className="bg-zinc-50 px-4 py-2 flex items-center justify-between">
                      <div>
                        <span className="font-medium text-sm text-zinc-950">{phase.title || 'Phase'}</span>
                        <span className="text-xs text-zinc-500 ml-2">{phase.month}</span>
                      </div>
                      <span className="text-xs text-zinc-500">{phaseCompleted}/{(phase.items || []).length} completed</span>
                    </div>
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-t border-zinc-100">
                          <th className="text-left px-4 py-2 text-xs uppercase text-zinc-500 font-medium">Item</th>
                          <th className="text-left px-4 py-2 text-xs uppercase text-zinc-500 font-medium">Assigned To</th>
                          <th className="text-left px-4 py-2 text-xs uppercase text-zinc-500 font-medium">Due Date</th>
                          <th className="text-center px-4 py-2 text-xs uppercase text-zinc-500 font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(phase.items || []).map(function(item) {
                          return (
                            <tr key={item.id} className="border-t border-zinc-100 hover:bg-zinc-50" data-testid={'roadmap-item-' + item.id}>
                              <td className="px-4 py-2 font-medium text-zinc-950">{item.title}</td>
                              <td className="px-4 py-2 text-zinc-600">{item.assigned_to || '-'}</td>
                              <td className="px-4 py-2 text-zinc-600">{item.due_date || '-'}</td>
                              <td className="px-4 py-2 text-center">
                                <select value={item.status} onChange={function(e) { handleItemStatus(selectedRoadmap.id, item.id, e.target.value); }}
                                  className={'h-7 px-2 rounded-sm border text-xs ' + getStatusBadge(item.status)}>
                                  {ITEM_STATUSES.map(function(s) { return <option key={s.value} value={s.value}>{s.label}</option>; })}
                                </select>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ProjectRoadmap;
