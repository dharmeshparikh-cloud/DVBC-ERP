import React, { useState, useEffect, useContext, useRef, useCallback } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, GripVertical } from 'lucide-react';

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
  const [colWidth, setColWidth] = useState(36); // px per day
  const [dragState, setDragState] = useState(null);
  const ganttRef = useRef(null);
  const headerRef = useRef(null);

  // Timeline range
  const [timelineStart, setTimelineStart] = useState(() => {
    const d = new Date(); d.setDate(1); return d;
  });
  const daysVisible = Math.max(60, Math.ceil(900 / colWidth));
  const timelineEnd = addDays(timelineStart, daysVisible);

  useEffect(() => { fetchProjects(); }, []);
  useEffect(() => { if (selectedProject) fetchTasks(); }, [selectedProject]);

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

  const updateTaskDates = async (taskId, startDate, endDate) => {
    try {
      await axios.patch(`${API}/tasks/${taskId}/dates`, { start_date: startDate, due_date: endDate });
      fetchTasks();
    } catch { toast.error('Failed to update dates'); }
  };

  // Timeline columns
  const columns = [];
  for (let i = 0; i < daysVisible; i++) {
    const d = addDays(timelineStart, i);
    columns.push(d);
  }

  const shiftTimeline = (days) => setTimelineStart(prev => addDays(prev, days));

  // --- Drag handlers ---
  const handleMouseDown = useCallback((e, task, type) => {
    e.preventDefault();
    e.stopPropagation();
    setDragState({ taskId: task.id, type, startX: e.clientX, origStart: task.start, origEnd: task.end });
  }, []);

  const handleMouseMove = useCallback((e) => {
    if (!dragState) return;
    const dx = e.clientX - dragState.startX;
    const daysDelta = Math.round(dx / colWidth);
    if (daysDelta === 0) return;

    setTasks(prev => prev.map(t => {
      if (t.id !== dragState.taskId) return t;
      const origStart = new Date(dragState.origStart);
      const origEnd = new Date(dragState.origEnd);
      if (dragState.type === 'move') {
        return { ...t, start: toISO(addDays(origStart, daysDelta)), end: toISO(addDays(origEnd, daysDelta)) };
      } else if (dragState.type === 'resize-end') {
        const newEnd = addDays(origEnd, daysDelta);
        if (newEnd > origStart) return { ...t, end: toISO(newEnd) };
      } else if (dragState.type === 'resize-start') {
        const newStart = addDays(origStart, daysDelta);
        if (newStart < new Date(dragState.origEnd)) return { ...t, start: toISO(newStart) };
      }
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

  // Sync scroll between header and body
  const onScroll = (e) => {
    if (headerRef.current) headerRef.current.scrollLeft = e.target.scrollLeft;
  };

  const tasksWithDates = tasks.filter(t => t.start && t.end);
  const tasksWithoutDates = tasks.filter(t => !t.start || !t.end);
  const project = projects.find(p => p.id === selectedProject);

  return (
    <div data-testid="gantt-chart-page" className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-1">Gantt Chart</h1>
          <p className="text-sm text-zinc-500">Drag bars to adjust task dates. Resize from edges.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => shiftTimeline(-14)} data-testid="timeline-prev"><ChevronLeft className="w-4 h-4" /></Button>
          <Button variant="outline" size="sm" onClick={() => { const d = new Date(); d.setDate(1); setTimelineStart(d); }} className="text-xs">Today</Button>
          <Button variant="ghost" size="sm" onClick={() => shiftTimeline(14)} data-testid="timeline-next"><ChevronRight className="w-4 h-4" /></Button>
          <div className="w-px h-5 bg-zinc-200 mx-1" />
          <Button variant="ghost" size="sm" onClick={() => setColWidth(w => Math.max(18, w - 6))} data-testid="zoom-out"><ZoomOut className="w-4 h-4" /></Button>
          <Button variant="ghost" size="sm" onClick={() => setColWidth(w => Math.min(60, w + 6))} data-testid="zoom-in"><ZoomIn className="w-4 h-4" /></Button>
        </div>
      </div>

      {/* Project Selector */}
      <div className="flex items-center gap-3">
        <select
          value={selectedProject}
          onChange={e => setSelectedProject(e.target.value)}
          className="h-9 px-3 rounded-sm border border-zinc-200 bg-white text-sm min-w-[250px]"
          data-testid="gantt-project-select"
        >
          {projects.map(p => (
            <option key={p.id} value={p.id}>{p.name} — {p.client_name}</option>
          ))}
        </select>
        {project && (
          <div className="flex items-center gap-4 text-xs text-zinc-500">
            <span>{tasksWithDates.length} tasks scheduled</span>
            <span>{tasksWithoutDates.length} unscheduled</span>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 flex-wrap">
        {Object.entries(STATUS_COLORS).map(([key, val]) => (
          <div key={key} className="flex items-center gap-1.5 text-[10px]">
            <div className={`w-3 h-2 rounded-sm ${val.bar}`} />
            <span className="text-zinc-500">{val.label}</span>
          </div>
        ))}
        <div className="w-px h-3 bg-zinc-200 mx-1" />
        {Object.entries(PRIORITY_DOT).map(([key, color]) => (
          <div key={key} className="flex items-center gap-1 text-[10px]">
            <div className={`w-2 h-2 rounded-full ${color}`} />
            <span className="text-zinc-400 capitalize">{key}</span>
          </div>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-zinc-400">Loading...</div>
      ) : tasksWithDates.length === 0 ? (
        <Card className="border-zinc-200 shadow-none">
          <CardContent className="py-12 text-center">
            <p className="text-zinc-500">No tasks with dates found for this project.</p>
            <p className="text-xs text-zinc-400 mt-1">Add start &amp; due dates to tasks in Project Tasks to see them here.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="border border-zinc-200 rounded-sm overflow-hidden bg-white" data-testid="gantt-container">
          {/* Timeline Header */}
          <div className="flex border-b border-zinc-200">
            {/* Task name column header */}
            <div className="w-[220px] min-w-[220px] px-3 py-2 bg-zinc-50 border-r border-zinc-200 text-[10px] font-semibold text-zinc-500 uppercase tracking-widest">
              Task
            </div>
            {/* Scrollable date headers */}
            <div className="flex-1 overflow-hidden" ref={headerRef}>
              <div className="flex" style={{ width: columns.length * colWidth }}>
                {columns.map((d, i) => {
                  const isWeekend = d.getDay() === 0 || d.getDay() === 6;
                  const isFirstOfMonth = d.getDate() === 1;
                  const isToday = toISO(d) === toISO(new Date());
                  return (
                    <div key={i} className={`flex-shrink-0 text-center border-r border-zinc-100 py-1.5 ${isWeekend ? 'bg-zinc-50' : ''} ${isToday ? 'bg-blue-50' : ''}`} style={{ width: colWidth }}>
                      {isFirstOfMonth && <div className="text-[8px] font-bold text-zinc-600 uppercase">{d.toLocaleDateString('en-IN', { month: 'short' })}</div>}
                      <div className={`text-[9px] ${isToday ? 'font-bold text-blue-600' : isWeekend ? 'text-zinc-400' : 'text-zinc-500'}`}>
                        {d.getDate()}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Task Rows */}
          <div className="max-h-[500px] overflow-y-auto">
            <div className="flex">
              {/* Task Name Column */}
              <div className="w-[220px] min-w-[220px] border-r border-zinc-200 bg-white">
                {tasksWithDates.map(task => {
                  const sc = STATUS_COLORS[task.status] || STATUS_COLORS.to_do;
                  const pd = PRIORITY_DOT[task.priority] || PRIORITY_DOT.medium;
                  return (
                    <div key={task.id} className="flex items-center gap-2 px-3 py-2 border-b border-zinc-50 hover:bg-zinc-50 transition-colors h-[40px]" data-testid={`gantt-task-label-${task.id}`}>
                      <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${pd}`} />
                      <div className="min-w-0 flex-1">
                        <div className="text-[11px] font-medium text-zinc-800 truncate">{task.name}</div>
                        <div className="text-[9px] text-zinc-400 truncate">{fmtDate(task.start)} — {fmtDate(task.end)}</div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Gantt Bars Area */}
              <div className="flex-1 overflow-x-auto" ref={ganttRef} onScroll={onScroll}>
                <div style={{ width: columns.length * colWidth, position: 'relative' }}>
                  {tasksWithDates.map((task, rowIdx) => {
                    const sc = STATUS_COLORS[task.status] || STATUS_COLORS.to_do;
                    const taskStart = new Date(task.start);
                    const taskEnd = new Date(task.end);
                    const startOffset = diffDays(timelineStart, taskStart);
                    const duration = Math.max(1, diffDays(taskStart, taskEnd) + 1);
                    const left = startOffset * colWidth;
                    const width = duration * colWidth;

                    // Only render if visible
                    if (startOffset + duration < 0 || startOffset > daysVisible) return null;

                    return (
                      <div key={task.id} className="relative border-b border-zinc-50 h-[40px]" style={{ width: columns.length * colWidth }}>
                        {/* Grid lines */}
                        {columns.map((d, i) => {
                          const isWeekend = d.getDay() === 0 || d.getDay() === 6;
                          const isToday = toISO(d) === toISO(new Date());
                          return <div key={i} className={`absolute top-0 bottom-0 border-r border-zinc-50 ${isWeekend ? 'bg-zinc-50/50' : ''} ${isToday ? 'bg-blue-50/40' : ''}`} style={{ left: i * colWidth, width: colWidth }} />;
                        })}

                        {/* Bar */}
                        <div
                          className={`absolute top-[8px] h-[24px] rounded-sm ${sc.bar} cursor-grab active:cursor-grabbing shadow-sm group flex items-center transition-shadow hover:shadow-md ${dragState?.taskId === task.id ? 'ring-2 ring-blue-400 z-20' : 'z-10'}`}
                          style={{ left: Math.max(0, left), width: Math.max(colWidth * 0.5, width) }}
                          onMouseDown={(e) => handleMouseDown(e, task, 'move')}
                          data-testid={`gantt-bar-${task.id}`}
                        >
                          {/* Resize handle left */}
                          <div
                            className="absolute left-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-black/10 rounded-l-sm"
                            onMouseDown={(e) => handleMouseDown(e, task, 'resize-start')}
                          />
                          {/* Progress fill */}
                          <div className="absolute inset-0 rounded-sm bg-white/20" style={{ width: `${task.progress || 0}%` }} />
                          {/* Label */}
                          {width > colWidth * 3 && (
                            <span className="relative z-10 px-2 text-[9px] font-medium text-white truncate">{task.name}</span>
                          )}
                          {/* Resize handle right */}
                          <div
                            className="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-black/10 rounded-r-sm"
                            onMouseDown={(e) => handleMouseDown(e, task, 'resize-end')}
                          />
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

      {/* Unscheduled Tasks */}
      {tasksWithoutDates.length > 0 && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4">
            <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-3">Unscheduled Tasks ({tasksWithoutDates.length})</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {tasksWithoutDates.map(t => {
                const sc = STATUS_COLORS[t.status] || STATUS_COLORS.to_do;
                return (
                  <div key={t.id} className="flex items-center gap-2 px-3 py-2 border border-zinc-200 rounded-sm text-xs" data-testid={`unscheduled-${t.id}`}>
                    <div className={`w-2 h-2 rounded-full ${sc.bar}`} />
                    <span className="text-zinc-700 truncate">{t.name}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default GanttChart;
