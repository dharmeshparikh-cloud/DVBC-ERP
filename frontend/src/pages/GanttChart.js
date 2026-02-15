import React, { useState, useEffect, useContext, useRef, useCallback } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Send, MessageSquare, FileText } from 'lucide-react';

const STATUS_COLORS = {
  to_do: { bar: 'bg-zinc-300', text: 'text-zinc-600', label: 'To Do' },
  in_progress: { bar: 'bg-blue-500', text: 'text-blue-700', label: 'In Progress' },
  completed: { bar: 'bg-emerald-500', text: 'text-emerald-700', label: 'Done' },
  delayed: { bar: 'bg-red-500', text: 'text-red-700', label: 'Delayed' },
  delegated: { bar: 'bg-purple-400', text: 'text-purple-700', label: 'Delegated' },
  cancelled: { bar: 'bg-zinc-200', text: 'text-zinc-400', label: 'Cancelled' },
};
const PRIORITY_DOT = { urgent: 'bg-red-500', high: 'bg-orange-500', medium: 'bg-yellow-500', low: 'bg-zinc-400' };

const addDays = (date, days) => { const d = new Date(date); d.setDate(d.getDate() + days); return d; };
const diffDays = (a, b) => Math.round((new Date(b) - new Date(a)) / 86400000);
const fmtDate = (d) => new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
const toISO = (d) => new Date(d).toISOString().split('T')[0];

const GanttChart = () => {
  const { user } = useContext(AuthContext);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [colWidth, setColWidth] = useState(36);
  const [dragState, setDragState] = useState(null);
  const [commLogOpen, setCommLogOpen] = useState(false);
  const [sendReportOpen, setSendReportOpen] = useState(false);
  const [commLogs, setCommLogs] = useState([]);
  const [reportForm, setReportForm] = useState({ client_name: '', subject: '', message: '', sow_id: '' });
  const [sows, setSows] = useState([]);
  const ganttRef = useRef(null);
  const headerRef = useRef(null);

  const [timelineStart, setTimelineStart] = useState(() => { const d = new Date(); d.setDate(1); return d; });
  const daysVisible = Math.max(60, Math.ceil(900 / colWidth));
  const canManage = ['admin', 'project_manager', 'manager', 'principal_consultant'].includes(user?.role);

  useEffect(() => { fetchProjects(); }, []);
  useEffect(() => { if (selectedProject) { fetchTasks(); fetchSOWs(); fetchCommLogs(); } }, [selectedProject]);

  const fetchProjects = async () => {
    try {
      const res = await axios.get(`${API}/projects`);
      setProjects(res.data);
      if (res.data.length > 0) setSelectedProject(res.data[0].id);
    } catch { toast.error('Failed to load projects'); }
    finally { setLoading(false); }
  };

  const fetchTasks = async () => {
    try {
      const res = await axios.get(`${API}/projects/${selectedProject}/tasks-gantt`);
      setTasks(res.data);
    } catch { toast.error('Failed to load tasks'); }
  };

  const fetchSOWs = async () => {
    try {
      const res = await axios.get(`${API}/sows`);
      const proj = projects.find(p => p.id === selectedProject);
      setSows(res.data.filter(s => s.lead_id === proj?.lead_id || s.project_id === selectedProject));
    } catch { /* silent */ }
  };

  const fetchCommLogs = async () => {
    try {
      const res = await axios.get(`${API}/client-communications?project_id=${selectedProject}`);
      setCommLogs(res.data);
    } catch { /* silent */ }
  };

  const updateTaskDates = async (taskId, startDate, endDate) => {
    try {
      await axios.patch(`${API}/tasks/${taskId}/dates`, { start_date: startDate, due_date: endDate });
      fetchTasks();
    } catch { toast.error('Failed to update dates'); }
  };

  const sendProgressReport = async () => {
    if (!reportForm.sow_id) return toast.error('Select a SOW');
    try {
      const res = await axios.post(`${API}/sow/${reportForm.sow_id}/send-progress-report`, {
        client_name: reportForm.client_name || project?.client_name || 'Client',
        subject: reportForm.subject,
        message: reportForm.message,
      });
      toast.success(`Progress report sent (${res.data.progress}% complete)`);
      setSendReportOpen(false);
      setReportForm({ client_name: '', subject: '', message: '', sow_id: '' });
      fetchCommLogs();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const sendManualUpdate = async () => {
    if (!reportForm.subject || !reportForm.message) return toast.error('Subject and message required');
    try {
      await axios.post(`${API}/client-communications`, {
        project_id: selectedProject,
        sow_id: reportForm.sow_id,
        client_name: reportForm.client_name || project?.client_name || 'Client',
        type: 'manual_update',
        subject: reportForm.subject,
        message: reportForm.message,
      });
      toast.success('Update sent to client');
      setSendReportOpen(false);
      setReportForm({ client_name: '', subject: '', message: '', sow_id: '' });
      fetchCommLogs();
    } catch { toast.error('Failed'); }
  };

  // Timeline columns
  const columns = [];
  for (let i = 0; i < daysVisible; i++) columns.push(addDays(timelineStart, i));
  const shiftTimeline = (days) => setTimelineStart(prev => addDays(prev, days));

  // Drag handlers
  const handleMouseDown = useCallback((e, task, type) => {
    e.preventDefault(); e.stopPropagation();
    setDragState({ taskId: task.id, type, startX: e.clientX, origStart: task.start, origEnd: task.end });
  }, []);

  const handleMouseMove = useCallback((e) => {
    if (!dragState) return;
    const daysDelta = Math.round((e.clientX - dragState.startX) / colWidth);
    if (daysDelta === 0) return;
    setTasks(prev => prev.map(t => {
      if (t.id !== dragState.taskId) return t;
      const os = new Date(dragState.origStart), oe = new Date(dragState.origEnd);
      if (dragState.type === 'move') return { ...t, start: toISO(addDays(os, daysDelta)), end: toISO(addDays(oe, daysDelta)) };
      if (dragState.type === 'resize-end') { const ne = addDays(oe, daysDelta); return ne > os ? { ...t, end: toISO(ne) } : t; }
      if (dragState.type === 'resize-start') { const ns = addDays(os, daysDelta); return ns < oe ? { ...t, start: toISO(ns) } : t; }
      return t;
    }));
  }, [dragState, colWidth]);

  const handleMouseUp = useCallback(() => {
    if (!dragState) return;
    const task = tasks.find(t => t.id === dragState.taskId);
    if (task && (task.start !== dragState.origStart || task.end !== dragState.origEnd)) {
      updateTaskDates(task.id, task.start, task.end);
      toast.success(`Updated: ${task.name}`);
    }
    setDragState(null);
  }, [dragState, tasks]);

  useEffect(() => {
    if (dragState) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => { window.removeEventListener('mousemove', handleMouseMove); window.removeEventListener('mouseup', handleMouseUp); };
    }
  }, [dragState, handleMouseMove, handleMouseUp]);

  const onScroll = (e) => { if (headerRef.current) headerRef.current.scrollLeft = e.target.scrollLeft; };

  const tasksWithDates = tasks.filter(t => t.start && t.end);
  const tasksWithoutDates = tasks.filter(t => !t.start || !t.end);
  const project = projects.find(p => p.id === selectedProject);

  // Group tasks by SOW item
  const sowGroups = {};
  tasksWithDates.forEach(t => {
    const key = t.sow_item_title || (t.sow_item_id ? `SOW Item ${t.sow_item_id.slice(0, 6)}` : 'Unlinked Tasks');
    if (!sowGroups[key]) sowGroups[key] = [];
    sowGroups[key].push(t);
  });
  const hasSOWGrouping = Object.keys(sowGroups).length > 1 || (Object.keys(sowGroups).length === 1 && !sowGroups['Unlinked Tasks']);

  // Flat ordered list for rendering
  const orderedTasks = hasSOWGrouping
    ? Object.entries(sowGroups).flatMap(([group, items]) => [{ _isGroup: true, label: group, count: items.length }, ...items])
    : tasksWithDates;

  return (
    <div data-testid="gantt-chart-page" className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-1">Gantt Chart</h1>
          <p className="text-sm text-zinc-500">Drag bars to adjust dates. Tasks linked to SOW items are grouped.</p>
        </div>
        <div className="flex items-center gap-2">
          {canManage && (
            <>
              <Button variant="outline" size="sm" onClick={() => setSendReportOpen(true)} className="text-xs gap-1" data-testid="send-report-btn">
                <Send className="w-3.5 h-3.5" /> Send Client Update
              </Button>
              <Button variant="outline" size="sm" onClick={() => setCommLogOpen(true)} className="text-xs gap-1" data-testid="comm-log-btn">
                <MessageSquare className="w-3.5 h-3.5" /> Comm Log ({commLogs.length})
              </Button>
            </>
          )}
          <div className="w-px h-5 bg-zinc-200" />
          <Button variant="ghost" size="sm" onClick={() => shiftTimeline(-14)}><ChevronLeft className="w-4 h-4" /></Button>
          <Button variant="outline" size="sm" onClick={() => { const d = new Date(); d.setDate(1); setTimelineStart(d); }} className="text-xs">Today</Button>
          <Button variant="ghost" size="sm" onClick={() => shiftTimeline(14)}><ChevronRight className="w-4 h-4" /></Button>
          <Button variant="ghost" size="sm" onClick={() => setColWidth(w => Math.max(18, w - 6))}><ZoomOut className="w-4 h-4" /></Button>
          <Button variant="ghost" size="sm" onClick={() => setColWidth(w => Math.min(60, w + 6))}><ZoomIn className="w-4 h-4" /></Button>
        </div>
      </div>

      {/* Project Selector + Legend */}
      <div className="flex items-center justify-between">
        <select value={selectedProject} onChange={e => setSelectedProject(e.target.value)}
          className="h-9 px-3 rounded-sm border border-zinc-200 bg-white text-sm min-w-[250px]" data-testid="gantt-project-select">
          {projects.map(p => (<option key={p.id} value={p.id}>{p.name} — {p.client_name}</option>))}
        </select>
        <div className="flex items-center gap-2.5">
          {Object.entries(STATUS_COLORS).map(([k, v]) => (
            <div key={k} className="flex items-center gap-1 text-[10px]"><div className={`w-3 h-2 rounded-sm ${v.bar}`} /><span className="text-zinc-500">{v.label}</span></div>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-zinc-400">Loading...</div>
      ) : tasksWithDates.length === 0 ? (
        <Card className="border-zinc-200 shadow-none">
          <CardContent className="py-12 text-center">
            <p className="text-zinc-500">No scheduled tasks. Add start &amp; due dates to tasks, optionally linking them to SOW items.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="border border-zinc-200 rounded-sm overflow-hidden bg-white" data-testid="gantt-container">
          {/* Header */}
          <div className="flex border-b border-zinc-200">
            <div className="w-[220px] min-w-[220px] px-3 py-2 bg-zinc-50 border-r border-zinc-200 text-[10px] font-semibold text-zinc-500 uppercase tracking-widest">Task</div>
            <div className="flex-1 overflow-hidden" ref={headerRef}>
              <div className="flex" style={{ width: columns.length * colWidth }}>
                {columns.map((d, i) => {
                  const isWe = d.getDay() === 0 || d.getDay() === 6;
                  const isToday = toISO(d) === toISO(new Date());
                  const isFOM = d.getDate() === 1;
                  return (
                    <div key={i} className={`flex-shrink-0 text-center border-r border-zinc-100 py-1.5 ${isWe ? 'bg-zinc-50' : ''} ${isToday ? 'bg-blue-50' : ''}`} style={{ width: colWidth }}>
                      {isFOM && <div className="text-[8px] font-bold text-zinc-600 uppercase">{d.toLocaleDateString('en-IN', { month: 'short' })}</div>}
                      <div className={`text-[9px] ${isToday ? 'font-bold text-blue-600' : isWe ? 'text-zinc-400' : 'text-zinc-500'}`}>{d.getDate()}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Rows */}
          <div className="max-h-[500px] overflow-y-auto">
            <div className="flex">
              <div className="w-[220px] min-w-[220px] border-r border-zinc-200 bg-white">
                {orderedTasks.map((item, idx) => {
                  if (item._isGroup) {
                    return (
                      <div key={`g-${idx}`} className="flex items-center gap-2 px-3 py-1.5 bg-zinc-100 border-b border-zinc-200 h-[28px]">
                        <FileText className="w-3 h-3 text-zinc-400" />
                        <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-wider truncate">{item.label}</span>
                        <Badge variant="secondary" className="text-[9px] px-1 py-0 bg-zinc-200 text-zinc-600">{item.count}</Badge>
                      </div>
                    );
                  }
                  const pd = PRIORITY_DOT[item.priority] || PRIORITY_DOT.medium;
                  return (
                    <div key={item.id} className="flex items-center gap-2 px-3 py-2 border-b border-zinc-50 hover:bg-zinc-50 h-[40px]">
                      <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${pd}`} />
                      <div className="min-w-0 flex-1">
                        <div className="text-[11px] font-medium text-zinc-800 truncate">{item.name}</div>
                        <div className="text-[9px] text-zinc-400">{fmtDate(item.start)} — {fmtDate(item.end)}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="flex-1 overflow-x-auto" ref={ganttRef} onScroll={onScroll}>
                <div style={{ width: columns.length * colWidth, position: 'relative' }}>
                  {orderedTasks.map((item, idx) => {
                    if (item._isGroup) {
                      return <div key={`gb-${idx}`} className="h-[28px] bg-zinc-100/50 border-b border-zinc-200" style={{ width: columns.length * colWidth }} />;
                    }
                    const sc = STATUS_COLORS[item.status] || STATUS_COLORS.to_do;
                    const startOff = diffDays(timelineStart, new Date(item.start));
                    const dur = Math.max(1, diffDays(new Date(item.start), new Date(item.end)) + 1);
                    const left = startOff * colWidth, width = dur * colWidth;
                    if (startOff + dur < 0 || startOff > daysVisible) return <div key={item.id} className="h-[40px] border-b border-zinc-50" style={{ width: columns.length * colWidth }} />;
                    return (
                      <div key={item.id} className="relative border-b border-zinc-50 h-[40px]" style={{ width: columns.length * colWidth }}>
                        {columns.map((d, i) => {
                          const isWe = d.getDay() === 0 || d.getDay() === 6;
                          const isToday = toISO(d) === toISO(new Date());
                          return <div key={i} className={`absolute top-0 bottom-0 border-r border-zinc-50 ${isWe ? 'bg-zinc-50/50' : ''} ${isToday ? 'bg-blue-50/40' : ''}`} style={{ left: i * colWidth, width: colWidth }} />;
                        })}
                        <div
                          className={`absolute top-[8px] h-[24px] rounded-sm ${sc.bar} cursor-grab active:cursor-grabbing shadow-sm group hover:shadow-md ${dragState?.taskId === item.id ? 'ring-2 ring-blue-400 z-20' : 'z-10'}`}
                          style={{ left: Math.max(0, left), width: Math.max(colWidth * 0.5, width) }}
                          onMouseDown={(e) => handleMouseDown(e, item, 'move')} data-testid={`gantt-bar-${item.id}`}
                        >
                          <div className="absolute left-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-black/10 rounded-l-sm" onMouseDown={(e) => handleMouseDown(e, item, 'resize-start')} />
                          <div className="absolute inset-0 rounded-sm bg-white/20" style={{ width: `${item.progress || 0}%` }} />
                          {width > colWidth * 3 && <span className="relative z-10 px-2 text-[9px] font-medium text-white truncate">{item.name}</span>}
                          <div className="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-black/10 rounded-r-sm" onMouseDown={(e) => handleMouseDown(e, item, 'resize-end')} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Unscheduled */}
      {tasksWithoutDates.length > 0 && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4">
            <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-3">Unscheduled Tasks ({tasksWithoutDates.length})</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {tasksWithoutDates.map(t => (
                <div key={t.id} className="flex items-center gap-2 px-3 py-2 border border-zinc-200 rounded-sm text-xs">
                  <div className={`w-2 h-2 rounded-full ${(STATUS_COLORS[t.status] || STATUS_COLORS.to_do).bar}`} />
                  <span className="text-zinc-700 truncate">{t.name}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Send Client Update Dialog */}
      <Dialog open={sendReportOpen} onOpenChange={setSendReportOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Send Client Update</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <Label className="text-xs">SOW (for auto-progress report)</Label>
              <select value={reportForm.sow_id} onChange={e => setReportForm({ ...reportForm, sow_id: e.target.value })}
                className="w-full h-9 px-3 rounded-sm border border-zinc-200 bg-white text-sm" data-testid="report-sow-select">
                <option value="">Select SOW (optional for manual)</option>
                {sows.map(s => (<option key={s.id} value={s.id}>{s.title || `SOW-${s.id.slice(0, 8)}`}</option>))}
              </select>
            </div>
            <div>
              <Label className="text-xs">Client Name</Label>
              <Input value={reportForm.client_name} onChange={e => setReportForm({ ...reportForm, client_name: e.target.value })}
                placeholder={project?.client_name || 'Client'} className="h-9" data-testid="report-client-name" />
            </div>
            <div>
              <Label className="text-xs">Subject</Label>
              <Input value={reportForm.subject} onChange={e => setReportForm({ ...reportForm, subject: e.target.value })}
                placeholder="Progress Update" className="h-9" data-testid="report-subject" />
            </div>
            <div>
              <Label className="text-xs">Message (leave empty for auto-generated progress report)</Label>
              <textarea value={reportForm.message} onChange={e => setReportForm({ ...reportForm, message: e.target.value })}
                className="w-full h-28 px-3 py-2 rounded-sm border border-zinc-200 bg-white text-sm resize-none" placeholder="Auto-generated if SOW selected..." data-testid="report-message" />
            </div>
            <div className="flex gap-2">
              {reportForm.sow_id && (
                <Button onClick={sendProgressReport} className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm h-9 text-xs gap-1" data-testid="send-progress-btn">
                  <Send className="w-3.5 h-3.5" /> Send Progress Report
                </Button>
              )}
              <Button onClick={sendManualUpdate} variant="outline" className="flex-1 rounded-sm h-9 text-xs gap-1" data-testid="send-manual-btn">
                <MessageSquare className="w-3.5 h-3.5" /> Send Manual Update
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Communication Log Dialog */}
      <Dialog open={commLogOpen} onOpenChange={setCommLogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Client Communication Log</DialogTitle></DialogHeader>
          {commLogs.length === 0 ? (
            <div className="text-center py-8 text-zinc-400 text-sm">No communications logged yet</div>
          ) : (
            <div className="space-y-3">
              {commLogs.map(c => (
                <div key={c.id} className="border border-zinc-200 rounded-sm p-3" data-testid={`comm-${c.id}`}>
                  <div className="flex items-start justify-between mb-1">
                    <div>
                      <div className="text-xs font-semibold text-zinc-900">{c.subject}</div>
                      <div className="text-[10px] text-zinc-400">To: {c.client_name} | By: {c.sent_by_name} | {new Date(c.created_at).toLocaleString()}</div>
                    </div>
                    <Badge variant="secondary" className={`text-[9px] ${c.type === 'progress_update' ? 'bg-blue-50 text-blue-700' : 'bg-zinc-100 text-zinc-600'}`}>
                      {c.type === 'progress_update' ? 'Auto Report' : 'Manual'}
                    </Badge>
                  </div>
                  <p className="text-xs text-zinc-600 whitespace-pre-line mt-1 line-clamp-4">{c.message}</p>
                  {c.sow_progress && (
                    <div className="mt-2 flex items-center gap-3 text-[10px] text-zinc-500">
                      <span>Progress: <span className="font-bold text-zinc-800">{c.sow_progress.overall_percent}%</span></span>
                      <span>Tasks: {c.sow_progress.completed}/{c.sow_progress.total_tasks}</span>
                      {c.sow_progress.delayed > 0 && <span className="text-red-600">{c.sow_progress.delayed} delayed</span>}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default GanttChart;
