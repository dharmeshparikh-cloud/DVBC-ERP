import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import {
  Clock, Calendar, Plus, Check, X, ChevronLeft, ChevronRight,
  FileText, Briefcase, Save, Send, Edit2, Loader2
} from 'lucide-react';
import { toast } from 'sonner';
import { format, startOfWeek, endOfWeek, addDays, addWeeks, subWeeks, isToday, parseISO } from 'date-fns';

const HOURS_OPTIONS = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10];

const Timesheets = () => {
  const { user } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [currentWeek, setCurrentWeek] = useState(startOfWeek(new Date(), { weekStartsOn: 1 }));
  const [projects, setProjects] = useState([]);
  const [timesheetData, setTimesheetData] = useState({});
  const [timesheetStatus, setTimesheetStatus] = useState('draft'); // draft, submitted, approved, rejected
  const [showAddProjectDialog, setShowAddProjectDialog] = useState(false);
  const [selectedProjectToAdd, setSelectedProjectToAdd] = useState(null);
  const [allProjects, setAllProjects] = useState([]);
  const [notes, setNotes] = useState({});

  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(currentWeek, i));
  const weekEndDate = endOfWeek(currentWeek, { weekStartsOn: 1 });

  useEffect(() => {
    fetchData();
  }, [currentWeek]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const weekStart = format(currentWeek, 'yyyy-MM-dd');
      const weekEnd = format(weekEndDate, 'yyyy-MM-dd');
      
      const [assignmentsRes, timesheetRes, allProjectsRes] = await Promise.all([
        axios.get(`${API}/consultants/my/projects`).catch(() => ({ data: [] })),
        axios.get(`${API}/timesheets?week_start=${weekStart}`).catch(() => ({ data: null })),
        axios.get(`${API}/projects`).catch(() => ({ data: [] }))
      ]);
      
      const assignedProjects = assignmentsRes.data || [];
      setProjects(assignedProjects);
      setAllProjects(allProjectsRes.data || []);
      
      // API returns array of timesheets - get the first one if exists
      const timesheetRecord = Array.isArray(timesheetRes.data) 
        ? timesheetRes.data[0] 
        : timesheetRes.data;
      
      if (timesheetRecord && typeof timesheetRecord === 'object') {
        setTimesheetData(timesheetRecord.entries || {});
        setTimesheetStatus(timesheetRecord.status || 'draft');
        setNotes(timesheetRecord.notes || {});
      } else {
        // Initialize empty timesheet
        const emptyData = {};
        assignedProjects.forEach(p => {
          emptyData[p.id] = weekDays.reduce((acc, day) => {
            acc[format(day, 'yyyy-MM-dd')] = 0;
            return acc;
          }, {});
        });
        setTimesheetData(emptyData);
        setTimesheetStatus('draft');
        setNotes({});
      }
    } catch (error) {
      console.error('Failed to fetch timesheet data:', error);
      toast.error('Failed to load timesheet');
    } finally {
      setLoading(false);
    }
  };

  const handleHoursChange = (projectId, date, hours) => {
    setTimesheetData(prev => ({
      ...prev,
      [projectId]: {
        ...prev[projectId],
        [date]: hours
      }
    }));
  };

  const handleNotesChange = (projectId, note) => {
    setNotes(prev => ({
      ...prev,
      [projectId]: note
    }));
  };

  const handleSave = async (submitForApproval = false) => {
    setSaving(true);
    try {
      const weekStart = format(currentWeek, 'yyyy-MM-dd');
      await axios.post(`${API}/timesheets`, {
        week_start: weekStart,
        entries: timesheetData,
        notes: notes,
        status: submitForApproval ? 'submitted' : 'draft'
      });
      
      if (submitForApproval) {
        setTimesheetStatus('submitted');
        toast.success('Timesheet submitted for approval');
      } else {
        toast.success('Timesheet saved as draft');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save timesheet');
    } finally {
      setSaving(false);
    }
  };

  const handleAddProject = () => {
    if (!selectedProjectToAdd) return;
    
    // Add project to timesheet
    setTimesheetData(prev => ({
      ...prev,
      [selectedProjectToAdd]: weekDays.reduce((acc, day) => {
        acc[format(day, 'yyyy-MM-dd')] = 0;
        return acc;
      }, {})
    }));
    
    const project = allProjects.find(p => p.id === selectedProjectToAdd);
    if (project && !projects.find(p => p.id === selectedProjectToAdd)) {
      setProjects(prev => [...prev, project]);
    }
    
    setShowAddProjectDialog(false);
    setSelectedProjectToAdd(null);
  };

  const getTotalForDay = (date) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    if (!timesheetData || typeof timesheetData !== 'object') return 0;
    return Object.values(timesheetData).reduce((sum, projectData) => {
      return sum + (projectData?.[dateStr] || 0);
    }, 0);
  };

  const getTotalForProject = (projectId) => {
    const projectData = timesheetData?.[projectId] || {};
    return Object.values(projectData).reduce((sum, hours) => sum + (hours || 0), 0);
  };

  const getWeekTotal = () => {
    if (!timesheetData || typeof timesheetData !== 'object') return 0;
    return Object.values(timesheetData).reduce((sum, projectData) => {
      if (!projectData || typeof projectData !== 'object') return sum;
      return sum + Object.values(projectData).reduce((s, h) => s + (h || 0), 0);
    }, 0);
  };

  const isEditable = timesheetStatus === 'draft' || timesheetStatus === 'rejected';

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="timesheets-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Timesheets</h1>
          <p className="text-sm text-zinc-500">Log your work hours by project</p>
        </div>
        <div className="flex items-center gap-2">
          {isEditable && (
            <>
              <Button variant="outline" onClick={() => handleSave(false)} disabled={saving}>
                <Save className="w-4 h-4 mr-2" /> Save Draft
              </Button>
              <Button onClick={() => handleSave(true)} disabled={saving}>
                <Send className="w-4 h-4 mr-2" /> Submit for Approval
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Week Navigation */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <Button variant="ghost" size="sm" onClick={() => setCurrentWeek(subWeeks(currentWeek, 1))}>
              <ChevronLeft className="w-4 h-4 mr-1" /> Previous Week
            </Button>
            <div className="text-center">
              <h3 className="font-semibold text-zinc-900">
                {format(currentWeek, 'MMM dd')} - {format(weekEndDate, 'MMM dd, yyyy')}
              </h3>
              <Badge className={
                timesheetStatus === 'approved' ? 'bg-emerald-100 text-emerald-700' :
                timesheetStatus === 'submitted' ? 'bg-blue-100 text-blue-700' :
                timesheetStatus === 'rejected' ? 'bg-red-100 text-red-700' :
                'bg-zinc-100 text-zinc-700'
              }>
                {timesheetStatus.charAt(0).toUpperCase() + timesheetStatus.slice(1)}
              </Badge>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setCurrentWeek(addWeeks(currentWeek, 1))}>
              Next Week <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Timesheet Grid */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Time Entries</CardTitle>
            {isEditable && (
              <Button variant="outline" size="sm" onClick={() => setShowAddProjectDialog(true)}>
                <Plus className="w-4 h-4 mr-1" /> Add Project
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-200">
                  <th className="text-left py-3 px-2 w-48 text-xs uppercase text-zinc-500">Project</th>
                  {weekDays.map(day => (
                    <th key={day.toISOString()} className={`text-center py-3 px-2 w-20 text-xs uppercase ${isToday(day) ? 'bg-blue-50' : ''}`}>
                      <div className={isToday(day) ? 'text-blue-600 font-bold' : 'text-zinc-500'}>
                        {format(day, 'EEE')}
                      </div>
                      <div className={isToday(day) ? 'text-blue-600' : 'text-zinc-400'}>
                        {format(day, 'd')}
                      </div>
                    </th>
                  ))}
                  <th className="text-center py-3 px-2 w-20 text-xs uppercase text-zinc-500 bg-zinc-50">Total</th>
                </tr>
              </thead>
              <tbody>
                {projects.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="text-center py-12 text-zinc-400">
                      <Briefcase className="w-8 h-8 mx-auto mb-2" />
                      <p>No projects assigned. Click "Add Project" to log time.</p>
                    </td>
                  </tr>
                ) : (
                  projects.map(project => (
                    <tr key={project.id} className="border-b border-zinc-100 hover:bg-zinc-50">
                      <td className="py-3 px-2">
                        <div>
                          <p className="font-medium text-zinc-900 truncate max-w-[180px]">{project.name}</p>
                          <p className="text-xs text-zinc-400">{project.client_name}</p>
                        </div>
                      </td>
                      {weekDays.map(day => {
                        const dateStr = format(day, 'yyyy-MM-dd');
                        const hours = timesheetData[project.id]?.[dateStr] || 0;
                        return (
                          <td key={dateStr} className={`text-center py-2 px-1 ${isToday(day) ? 'bg-blue-50' : ''}`}>
                            {isEditable ? (
                              <select
                                value={hours}
                                onChange={(e) => handleHoursChange(project.id, dateStr, parseFloat(e.target.value))}
                                className="w-16 h-8 text-center text-sm border border-zinc-200 rounded"
                              >
                                {HOURS_OPTIONS.map(h => (
                                  <option key={h} value={h}>{h}</option>
                                ))}
                              </select>
                            ) : (
                              <span className={`font-medium ${hours > 0 ? 'text-zinc-900' : 'text-zinc-300'}`}>
                                {hours}
                              </span>
                            )}
                          </td>
                        );
                      })}
                      <td className="text-center py-3 px-2 bg-zinc-50 font-semibold">
                        {getTotalForProject(project.id)}h
                      </td>
                    </tr>
                  ))
                )}
                {/* Daily Totals Row */}
                {projects.length > 0 && (
                  <tr className="bg-zinc-100 font-semibold">
                    <td className="py-3 px-2 text-zinc-700">Daily Total</td>
                    {weekDays.map(day => {
                      const total = getTotalForDay(day);
                      return (
                        <td key={day.toISOString()} className={`text-center py-3 px-2 ${isToday(day) ? 'bg-blue-100' : ''}`}>
                          <span className={total > 8 ? 'text-amber-600' : total > 0 ? 'text-zinc-900' : 'text-zinc-400'}>
                            {total}h
                          </span>
                        </td>
                      );
                    })}
                    <td className="text-center py-3 px-2 bg-emerald-100 text-emerald-700 font-bold">
                      {getWeekTotal()}h
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Notes Section */}
      {projects.length > 0 && isEditable && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Notes (Optional)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {projects.map(project => (
                <div key={project.id} className="flex gap-4 items-start">
                  <Label className="w-48 pt-2 text-sm font-medium">{project.name}</Label>
                  <Input
                    placeholder="Add notes for this project..."
                    value={notes[project.id] || ''}
                    onChange={(e) => handleNotesChange(project.id, e.target.value)}
                    className="flex-1"
                  />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Add Project Dialog */}
      <Dialog open={showAddProjectDialog} onOpenChange={setShowAddProjectDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Project</DialogTitle>
            <DialogDescription>Select a project to log time against</DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label>Select Project</Label>
            <select
              className="w-full mt-2 h-10 px-3 rounded-md border border-zinc-200"
              value={selectedProjectToAdd || ''}
              onChange={(e) => setSelectedProjectToAdd(e.target.value)}
            >
              <option value="">Select a project...</option>
              {allProjects
                .filter(p => !projects.find(proj => proj.id === p.id))
                .map(p => (
                  <option key={p.id} value={p.id}>{p.name} - {p.client_name}</option>
                ))
              }
            </select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddProjectDialog(false)}>Cancel</Button>
            <Button onClick={handleAddProject} disabled={!selectedProjectToAdd}>Add Project</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Timesheets;
