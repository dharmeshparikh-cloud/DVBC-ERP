import React, { useState, useContext, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { AuthContext, API } from '../../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Badge } from '../../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Switch } from '../../components/ui/switch';
import { ScrollArea } from '../../components/ui/scroll-area';
import { 
  Plus, Edit, Trash2, Search, Eye, ThumbsUp, ThumbsDown, 
  BookOpen, FileText, AlertTriangle, PlayCircle, HelpCircle,
  BarChart3, TrendingUp, Loader2, Save, X, ChevronDown, ChevronUp
} from 'lucide-react';
import { toast } from 'sonner';

const HelpContentAdmin = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('topics');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterType, setFilterType] = useState('all');
  
  // Dialog states
  const [showTopicDialog, setShowTopicDialog] = useState(false);
  const [showCategoryDialog, setShowCategoryDialog] = useState(false);
  const [editingTopic, setEditingTopic] = useState(null);
  const [editingCategory, setEditingCategory] = useState(null);
  
  // Fetch topics using React Query
  const { data: topicsData = [], isLoading: topicsLoading, refetch: refetchTopics } = useQuery({
    queryKey: ['help-topics', filterCategory, filterType],
    queryFn: async () => {
      const res = await axios.get(`${API}/help/admin/topics`, {
        params: {
          category: filterCategory !== 'all' ? filterCategory : undefined,
          type: filterType !== 'all' ? filterType : undefined
        }
      });
      return res.data.topics || [];
    },
    staleTime: 2 * 60 * 1000
  });

  const topics = topicsData;

  // Fetch categories
  const { data: categories = [] } = useQuery({
    queryKey: ['help-categories'],
    queryFn: async () => {
      const res = await axios.get(`${API}/help/admin/categories`);
      return res.data || [];
    },
    staleTime: 5 * 60 * 1000
  });

  // Fetch analytics
  const { data: analytics = null } = useQuery({
    queryKey: ['help-analytics'],
    queryFn: async () => {
      const res = await axios.get(`${API}/help/admin/analytics`);
      return res.data;
    },
    staleTime: 2 * 60 * 1000
  });

  const loading = topicsLoading;

  // Seed content mutation
  const seedContentMutation = useMutation({
    mutationFn: async () => {
      const res = await axios.post(`${API}/help/admin/seed`);
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(data.message);
      queryClient.invalidateQueries({ queryKey: ['help-topics'] });
      queryClient.invalidateQueries({ queryKey: ['help-categories'] });
      queryClient.invalidateQueries({ queryKey: ['help-analytics'] });
    },
    onError: () => toast.error('Failed to seed content')
  });

  const handleSeedContent = () => seedContentMutation.mutate();

  // Delete topic mutation
  const deleteTopicMutation = useMutation({
    mutationFn: async (topicId) => {
      await axios.delete(`${API}/help/admin/topics/${topicId}`);
    },
    onSuccess: () => {
      toast.success('Topic deleted');
      queryClient.invalidateQueries({ queryKey: ['help-topics'] });
      queryClient.invalidateQueries({ queryKey: ['help-analytics'] });
    },
    onError: () => toast.error('Failed to delete topic')
  });

  const handleDeleteTopic = (topicId) => {
    if (!confirm('Are you sure you want to delete this topic?')) return;
    deleteTopicMutation.mutate(topicId);
  };
  
  const filteredTopics = Array.isArray(topics) ? (topics || []).filter(topic => 
    topic.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    topic.category?.toLowerCase().includes(searchQuery.toLowerCase())
  ) : [];
  
  const getTypeIcon = (type) => {
    switch (type) {
      case 'guide': return <FileText className="w-4 h-4 text-blue-500" />;
      case 'troubleshoot': return <AlertTriangle className="w-4 h-4 text-amber-500" />;
      case 'video': return <PlayCircle className="w-4 h-4 text-red-500" />;
      case 'faq': return <HelpCircle className="w-4 h-4 text-green-500" />;
      default: return <BookOpen className="w-4 h-4 text-zinc-500" />;
    }
  };
  
  if (!user || user?.role !== 'admin') {
    return (
      <div className="p-8 text-center">
        <h1 className="text-2xl font-bold text-red-600">Access Denied</h1>
        <p className="text-zinc-500 mt-2">Only administrators can access this page.</p>
      </div>
    );
  }
  
  return (
    <div className="space-y-6" data-testid="help-admin">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Help Content Management</h1>
          <p className="text-zinc-500">Manage help topics, categories, and view analytics</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleSeedContent}>
            Seed Default Content
          </Button>
          <Button onClick={() => { setEditingTopic(null); setShowTopicDialog(true); }}>
            <Plus className="w-4 h-4 mr-2" />
            New Topic
          </Button>
        </div>
      </div>
      
      {/* Analytics Cards */}
      {analytics && (
        <div className="grid grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-zinc-500">Total Topics</p>
                  <p className="text-3xl font-bold">{analytics.totalTopics}</p>
                </div>
                <BookOpen className="w-8 h-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-zinc-500">Total Views</p>
                  <p className="text-3xl font-bold">{analytics.totalViews?.toLocaleString()}</p>
                </div>
                <Eye className="w-8 h-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-zinc-500">Helpful Feedback</p>
                  <p className="text-3xl font-bold text-green-600">
                    {analytics.mostHelpful?.reduce((sum, t) => sum + t.helpful, 0) || 0}
                  </p>
                </div>
                <ThumbsUp className="w-8 h-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-zinc-500">Needs Improvement</p>
                  <p className="text-3xl font-bold text-amber-600">
                    {analytics.needsImprovement?.length || 0}
                  </p>
                </div>
                <ThumbsDown className="w-8 h-8 text-amber-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}
      
      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="topics">Topics ({topics.length})</TabsTrigger>
          <TabsTrigger value="categories">Categories ({categories.length})</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>
        
        {/* Topics Tab */}
        <TabsContent value="topics" className="mt-4">
          {/* Filters */}
          <div className="flex gap-4 mb-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
              <Input
                placeholder="Search topics..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={filterCategory} onValueChange={setFilterCategory}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {(categories || []).map(cat => (
                  <SelectItem key={cat.id} value={cat.slug}>{cat.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="guide">Guide</SelectItem>
                <SelectItem value="troubleshoot">Troubleshoot</SelectItem>
                <SelectItem value="video">Video</SelectItem>
                <SelectItem value="faq">FAQ</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          {/* Topics List */}
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
            </div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full">
                <thead className="bg-zinc-50">
                  <tr>
                    <th className="text-left p-3 font-medium text-sm">Topic</th>
                    <th className="text-left p-3 font-medium text-sm">Category</th>
                    <th className="text-left p-3 font-medium text-sm">Type</th>
                    <th className="text-center p-3 font-medium text-sm">Views</th>
                    <th className="text-center p-3 font-medium text-sm">Feedback</th>
                    <th className="text-center p-3 font-medium text-sm">Status</th>
                    <th className="text-right p-3 font-medium text-sm">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(filteredTopics || []).map(topic => (
                    <tr key={topic.id} className="hover:bg-zinc-50">
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          {getTypeIcon(topic.type)}
                          <div>
                            <p className="font-medium">{topic.title}</p>
                            {topic.isNew && (
                              <Badge className="text-[10px] bg-green-100 text-green-700">NEW</Badge>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="p-3 text-sm text-zinc-600">{topic.category}</td>
                      <td className="p-3">
                        <Badge variant="outline" className="text-xs capitalize">{topic.type}</Badge>
                      </td>
                      <td className="p-3 text-center text-sm">{topic.viewCount || 0}</td>
                      <td className="p-3 text-center">
                        <div className="flex items-center justify-center gap-2 text-sm">
                          <span className="text-green-600">+{topic.helpfulCount || 0}</span>
                          <span className="text-red-600">-{topic.notHelpfulCount || 0}</span>
                        </div>
                      </td>
                      <td className="p-3 text-center">
                        <Badge variant={topic.isActive ? 'default' : 'secondary'}>
                          {topic.isActive ? 'Active' : 'Inactive'}
                        </Badge>
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex justify-end gap-1">
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => { setEditingTopic(topic); setShowTopicDialog(true); }}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="sm"
                            className="text-red-500 hover:text-red-700"
                            onClick={() => handleDeleteTopic(topic.id)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredTopics.length === 0 && (
                <div className="text-center py-12 text-zinc-500">
                  No topics found. Click "New Topic" to create one.
                </div>
              )}
            </div>
          )}
        </TabsContent>
        
        {/* Categories Tab */}
        <TabsContent value="categories" className="mt-4">
          <div className="flex justify-end mb-4">
            <Button onClick={() => { setEditingCategory(null); setShowCategoryDialog(true); }}>
              <Plus className="w-4 h-4 mr-2" />
              New Category
            </Button>
          </div>
          
          <div className="grid grid-cols-3 gap-4">
            {(categories || []).map(cat => (
              <Card key={cat.id}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <span className="text-2xl">{cat.icon}</span>
                    {cat.name}
                  </CardTitle>
                  <CardDescription>{cat.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <Badge variant="secondary">{cat.slug}</Badge>
                    <div className="flex gap-1">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => { setEditingCategory(cat); setShowCategoryDialog(true); }}
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
        
        {/* Analytics Tab */}
        <TabsContent value="analytics" className="mt-4">
          {analytics && (
            <div className="grid grid-cols-2 gap-6">
              {/* Top Viewed */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-blue-500" />
                    Top Viewed Topics
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {analytics.topViewed?.map((topic, idx) => (
                      <div key={topic.id} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-zinc-400">#{idx + 1}</span>
                          <span className="text-sm">{topic.title}</span>
                        </div>
                        <Badge variant="outline">{topic.views} views</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
              
              {/* Most Helpful */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <ThumbsUp className="w-5 h-5 text-green-500" />
                    Most Helpful Topics
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {analytics.mostHelpful?.map((topic, idx) => (
                      <div key={topic.id} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-zinc-400">#{idx + 1}</span>
                          <span className="text-sm">{topic.title}</span>
                        </div>
                        <Badge className="bg-green-100 text-green-700">{topic.helpful} helpful</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
              
              {/* Needs Improvement */}
              <Card className="col-span-2">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-500" />
                    Topics Needing Improvement
                  </CardTitle>
                  <CardDescription>Topics with negative feedback that may need updates</CardDescription>
                </CardHeader>
                <CardContent>
                  {analytics.needsImprovement?.length > 0 ? (
                    <div className="space-y-2">
                      {(analytics?.needsImprovement || []).map(topic => (
                        <div key={topic.id} className="flex items-center justify-between p-3 bg-amber-50 rounded-lg">
                          <span className="text-sm">{topic.title}</span>
                          <div className="flex items-center gap-2">
                            <Badge variant="destructive">{topic.notHelpful} not helpful</Badge>
                            <Button variant="outline" size="sm" onClick={() => { setEditingTopic(topic); setShowTopicDialog(true); }}>
                              Edit
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-zinc-500 text-center py-4">All topics are performing well!</p>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>
      </Tabs>
      
      {/* Topic Dialog */}
      <TopicDialog
        open={showTopicDialog}
        onClose={() => setShowTopicDialog(false)}
        topic={editingTopic}
        categories={categories}
        queryClient={queryClient}
      />
      
      {/* Category Dialog */}
      <CategoryDialog
        open={showCategoryDialog}
        onClose={() => setShowCategoryDialog(false)}
        category={editingCategory}
        queryClient={queryClient}
      />
    </div>
  );
};

// Topic Create/Edit Dialog
const TopicDialog = ({ open, onClose, topic, categories, queryClient }) => {
  const [formData, setFormData] = useState({
    title: '',
    slug: '',
    type: 'guide',
    category: '',
    introduction: '',
    routes: '',
    roles: '',
    keywords: '',
    videoUrl: '',
    notes: '',
    isNew: false,
    requiresOnboarding: false,
    priority: 0,
    isActive: true,
    steps: [],
    troubleshooting: []
  });
  
  useEffect(() => {
    if (topic) {
      setFormData({
        title: topic.title || '',
        slug: topic.slug || '',
        type: topic.type || 'guide',
        category: topic.category || '',
        introduction: topic.introduction || '',
        routes: (topic.routes || []).join(', '),
        roles: (topic.roles || []).join(', '),
        keywords: (topic.keywords || []).join(', '),
        videoUrl: topic.videoUrl || '',
        notes: topic.notes || '',
        isNew: topic.isNew || false,
        requiresOnboarding: topic.requiresOnboarding || false,
        priority: topic.priority || 0,
        isActive: topic.isActive !== false,
        steps: topic.steps || [],
        troubleshooting: topic.troubleshooting || []
      });
    } else {
      setFormData({
        title: '', slug: '', type: 'guide', category: '', introduction: '',
        routes: '', roles: '', keywords: '', videoUrl: '', notes: '',
        isNew: false, requiresOnboarding: false, priority: 0, isActive: true,
        steps: [], troubleshooting: []
      });
    }
  }, [topic, open]);
  
  const saveTopicMutation = useMutation({
    mutationFn: async ({ isEdit, id, payload }) => {
      if (isEdit) {
        await axios.put(`${API}/help/admin/topics/${id}`, payload);
      } else {
        await axios.post(`${API}/help/admin/topics`, payload);
      }
    },
    onSuccess: (_, { isEdit }) => {
      toast.success(isEdit ? 'Topic updated' : 'Topic created');
      queryClient.invalidateQueries({ queryKey: ['help-topics'] });
      queryClient.invalidateQueries({ queryKey: ['help-analytics'] });
      onClose();
    },
    onError: () => toast.error('Failed to save topic')
  });

  const handleSave = () => {
    if (!formData.title || !formData.category) {
      toast.error('Title and category are required');
      return;
    }
    
    const payload = {
      ...formData,
      slug: formData.slug || formData.title.toLowerCase().replace(/\s+/g, '-'),
      routes: formData.routes.split(',').map(r => r.trim()).filter(Boolean),
      roles: formData.roles.split(',').map(r => r.trim()).filter(Boolean),
      keywords: formData.keywords.split(',').map(k => k.trim()).filter(Boolean)
    };
    
    saveTopicMutation.mutate({
      isEdit: !!topic?.id,
      id: topic?.id,
      payload
    });
  };

  const saving = saveTopicMutation.isPending;
  
  const addStep = () => {
    setFormData(prev => ({
      ...prev,
      steps: [...prev.steps, { title: '', description: '', tip: '' }]
    }));
  };
  
  const updateStep = (index, field, value) => {
    const newSteps = [...formData.steps];
    newSteps[index][field] = value;
    setFormData(prev => ({ ...prev, steps: newSteps }));
  };
  
  const removeStep = (index) => {
    setFormData(prev => ({
      ...prev,
      steps: (prev?.steps || []).filter((_, i) => i !== index)
    }));
  };
  
  const addTroubleshoot = () => {
    setFormData(prev => ({
      ...prev,
      troubleshooting: [...prev.troubleshooting, { problem: '', solution: '' }]
    }));
  };
  
  const updateTroubleshoot = (index, field, value) => {
    const newItems = [...formData.troubleshooting];
    newItems[index][field] = value;
    setFormData(prev => ({ ...prev, troubleshooting: newItems }));
  };
  
  const removeTroubleshoot = (index) => {
    setFormData(prev => ({
      ...prev,
      troubleshooting: (prev?.troubleshooting || []).filter((_, i) => i !== index)
    }));
  };
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>{topic ? 'Edit Topic' : 'Create New Topic'}</DialogTitle>
        </DialogHeader>
        
        <ScrollArea className="flex-1 pr-4">
          <div className="space-y-4 py-4">
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Title *</Label>
                <Input
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="How to do something"
                />
              </div>
              <div>
                <Label>Slug</Label>
                <Input
                  value={formData.slug}
                  onChange={(e) => setFormData(prev => ({ ...prev, slug: e.target.value }))}
                  placeholder="how-to-do-something"
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Category *</Label>
                <Select value={formData.category} onValueChange={(v) => setFormData(prev => ({ ...prev, category: v }))}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {(categories || []).map(cat => (
                      <SelectItem key={cat.id} value={cat.slug}>{cat.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Type</Label>
                <Select value={formData.type} onValueChange={(v) => setFormData(prev => ({ ...prev, type: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="guide">Guide</SelectItem>
                    <SelectItem value="troubleshoot">Troubleshooting</SelectItem>
                    <SelectItem value="video">Video</SelectItem>
                    <SelectItem value="faq">FAQ</SelectItem>
                    <SelectItem value="whatsnew">What's New</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div>
              <Label>Introduction</Label>
              <Textarea
                value={formData.introduction}
                onChange={(e) => setFormData(prev => ({ ...prev, introduction: e.target.value }))}
                placeholder="Brief description of this topic..."
                rows={3}
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Routes (comma-separated)</Label>
                <Input
                  value={formData.routes}
                  onChange={(e) => setFormData(prev => ({ ...prev, routes: e.target.value }))}
                  placeholder="/dashboard, /employees"
                />
              </div>
              <div>
                <Label>Roles (comma-separated, empty = all)</Label>
                <Input
                  value={formData.roles}
                  onChange={(e) => setFormData(prev => ({ ...prev, roles: e.target.value }))}
                  placeholder="hr_manager, admin"
                />
              </div>
            </div>
            
            <div>
              <Label>Keywords (comma-separated)</Label>
              <Input
                value={formData.keywords}
                onChange={(e) => setFormData(prev => ({ ...prev, keywords: e.target.value }))}
                placeholder="help, guide, how to"
              />
            </div>
            
            {/* Steps */}
            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <Label className="text-base font-semibold">Steps ({formData.steps.length})</Label>
                <Button type="button" variant="outline" size="sm" onClick={addStep}>
                  <Plus className="w-4 h-4 mr-1" /> Add Step
                </Button>
              </div>
              <div className="space-y-3">
                {(formData?.steps || []).map((step, idx) => (
                  <div key={idx} className="flex gap-2 p-3 bg-zinc-50 rounded-lg">
                    <div className="w-8 h-8 bg-orange-500 text-white rounded-full flex items-center justify-center text-sm font-bold shrink-0">
                      {idx + 1}
                    </div>
                    <div className="flex-1 space-y-2">
                      <Input
                        value={step.title}
                        onChange={(e) => updateStep(idx, 'title', e.target.value)}
                        placeholder="Step title"
                      />
                      <Textarea
                        value={step.description}
                        onChange={(e) => updateStep(idx, 'description', e.target.value)}
                        placeholder="Step description"
                        rows={2}
                      />
                      <Input
                        value={step.tip || ''}
                        onChange={(e) => updateStep(idx, 'tip', e.target.value)}
                        placeholder="Pro tip (optional)"
                      />
                    </div>
                    <Button type="button" variant="ghost" size="sm" onClick={() => removeStep(idx)}>
                      <X className="w-4 h-4 text-red-500" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Troubleshooting */}
            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <Label className="text-base font-semibold">Troubleshooting ({formData.troubleshooting.length})</Label>
                <Button type="button" variant="outline" size="sm" onClick={addTroubleshoot}>
                  <Plus className="w-4 h-4 mr-1" /> Add Issue
                </Button>
              </div>
              <div className="space-y-3">
                {(formData?.troubleshooting || []).map((item, idx) => (
                  <div key={idx} className="flex gap-2 p-3 bg-amber-50 rounded-lg">
                    <div className="flex-1 space-y-2">
                      <Input
                        value={item.problem}
                        onChange={(e) => updateTroubleshoot(idx, 'problem', e.target.value)}
                        placeholder="Problem"
                        className="border-red-200"
                      />
                      <Textarea
                        value={item.solution}
                        onChange={(e) => updateTroubleshoot(idx, 'solution', e.target.value)}
                        placeholder="Solution"
                        rows={2}
                        className="border-green-200"
                      />
                    </div>
                    <Button type="button" variant="ghost" size="sm" onClick={() => removeTroubleshoot(idx)}>
                      <X className="w-4 h-4 text-red-500" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Additional Settings */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Video URL</Label>
                <Input
                  value={formData.videoUrl}
                  onChange={(e) => setFormData(prev => ({ ...prev, videoUrl: e.target.value }))}
                  placeholder="https://youtube.com/..."
                />
              </div>
              <div>
                <Label>Priority (higher = shown first)</Label>
                <Input
                  type="number"
                  value={formData.priority}
                  onChange={(e) => setFormData(prev => ({ ...prev, priority: parseInt(e.target.value) || 0 }))}
                />
              </div>
            </div>
            
            <div>
              <Label>Additional Notes</Label>
              <Textarea
                value={formData.notes}
                onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                placeholder="Any additional notes..."
                rows={2}
              />
            </div>
            
            {/* Toggles */}
            <div className="flex gap-8">
              <div className="flex items-center gap-2">
                <Switch
                  checked={formData.isActive}
                  onCheckedChange={(v) => setFormData(prev => ({ ...prev, isActive: v }))}
                />
                <Label>Active</Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={formData.isNew}
                  onCheckedChange={(v) => setFormData(prev => ({ ...prev, isNew: v }))}
                />
                <Label>Mark as New</Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={formData.requiresOnboarding}
                  onCheckedChange={(v) => setFormData(prev => ({ ...prev, requiresOnboarding: v }))}
                />
                <Label>Requires Onboarding Tour</Label>
              </div>
            </div>
          </div>
        </ScrollArea>
        
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
            Save Topic
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// Category Create/Edit Dialog
const CategoryDialog = ({ open, onClose, category, queryClient }) => {
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    icon: '📖',
    description: '',
    order: 0,
    roles: ''
  });
  
  useEffect(() => {
    if (category) {
      setFormData({
        name: category.name || '',
        slug: category.slug || '',
        icon: category.icon || '📖',
        description: category.description || '',
        order: category.order || 0,
        roles: (category.roles || []).join(', ')
      });
    } else {
      setFormData({ name: '', slug: '', icon: '📖', description: '', order: 0, roles: '' });
    }
  }, [category, open]);
  
  const saveCategoryMutation = useMutation({
    mutationFn: async ({ isEdit, id, payload }) => {
      if (isEdit) {
        await axios.put(`${API}/help/admin/categories/${id}`, payload);
      } else {
        await axios.post(`${API}/help/admin/categories`, payload);
      }
    },
    onSuccess: (_, { isEdit }) => {
      toast.success(isEdit ? 'Category updated' : 'Category created');
      queryClient.invalidateQueries({ queryKey: ['help-categories'] });
      queryClient.invalidateQueries({ queryKey: ['help-topics'] });
      onClose();
    },
    onError: () => toast.error('Failed to save category')
  });

  const handleSave = () => {
    if (!formData.name) {
      toast.error('Name is required');
      return;
    }
    
    const payload = {
      ...formData,
      slug: formData.slug || formData.name.toLowerCase().replace(/\s+/g, '-'),
      roles: formData.roles.split(',').map(r => r.trim()).filter(Boolean)
    };
    
    saveCategoryMutation.mutate({
      isEdit: !!category?.id,
      id: category?.id,
      payload
    });
  };

  const saving = saveCategoryMutation.isPending;
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{category ? 'Edit Category' : 'Create New Category'}</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="grid grid-cols-4 gap-4">
            <div>
              <Label>Icon</Label>
              <Input
                value={formData.icon}
                onChange={(e) => setFormData(prev => ({ ...prev, icon: e.target.value }))}
                className="text-2xl text-center"
              />
            </div>
            <div className="col-span-3">
              <Label>Name *</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Category name"
              />
            </div>
          </div>
          
          <div>
            <Label>Slug</Label>
            <Input
              value={formData.slug}
              onChange={(e) => setFormData(prev => ({ ...prev, slug: e.target.value }))}
              placeholder="category-slug"
            />
          </div>
          
          <div>
            <Label>Description</Label>
            <Textarea
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Brief description..."
              rows={2}
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Order</Label>
              <Input
                type="number"
                value={formData.order}
                onChange={(e) => setFormData(prev => ({ ...prev, order: parseInt(e.target.value) || 0 }))}
              />
            </div>
            <div>
              <Label>Roles (comma-separated)</Label>
              <Input
                value={formData.roles}
                onChange={(e) => setFormData(prev => ({ ...prev, roles: e.target.value }))}
                placeholder="hr_manager, admin"
              />
            </div>
          </div>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default HelpContentAdmin;
