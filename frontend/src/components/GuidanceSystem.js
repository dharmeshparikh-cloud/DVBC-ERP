import React, { useState, useContext, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { useGuidance, WORKFLOWS, PAGE_TIPS } from '../contexts/GuidanceContext';
import { useApprovals } from '../contexts/ApprovalContext';
import { useTheme } from '../contexts/ThemeContext';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { 
  HelpCircle, X, ChevronRight, ChevronLeft, CheckCircle2, 
  Circle, ArrowRight, Sparkles, MessageSquare, Lightbulb,
  Navigation, List, Send, Loader2, Bot, Bell, AlertCircle,
  ClipboardCheck, Calendar, Receipt, Users, Clock, GripVertical, Move
} from 'lucide-react';

// Custom hook for drag functionality
const useDraggable = (initialPosition = { x: null, y: null }) => {
  const [position, setPosition] = useState(initialPosition);
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef(null);
  const offsetRef = useRef({ x: 0, y: 0 });

  const handleMouseDown = useCallback((e) => {
    if (!dragRef.current) return;
    
    const rect = dragRef.current.getBoundingClientRect();
    offsetRef.current = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    };
    setIsDragging(true);
    e.preventDefault();
  }, []);

  const handleMouseMove = useCallback((e) => {
    if (!isDragging) return;
    
    const newX = e.clientX - offsetRef.current.x;
    const newY = e.clientY - offsetRef.current.y;
    
    // Keep within viewport bounds
    const maxX = window.innerWidth - (dragRef.current?.offsetWidth || 0);
    const maxY = window.innerHeight - (dragRef.current?.offsetHeight || 0);
    
    setPosition({
      x: Math.max(0, Math.min(newX, maxX)),
      y: Math.max(0, Math.min(newY, maxY))
    });
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleTouchStart = useCallback((e) => {
    if (!dragRef.current) return;
    
    const touch = e.touches[0];
    const rect = dragRef.current.getBoundingClientRect();
    offsetRef.current = {
      x: touch.clientX - rect.left,
      y: touch.clientY - rect.top
    };
    setIsDragging(true);
  }, []);

  const handleTouchMove = useCallback((e) => {
    if (!isDragging) return;
    
    const touch = e.touches[0];
    const newX = touch.clientX - offsetRef.current.x;
    const newY = touch.clientY - offsetRef.current.y;
    
    const maxX = window.innerWidth - (dragRef.current?.offsetWidth || 0);
    const maxY = window.innerHeight - (dragRef.current?.offsetHeight || 0);
    
    setPosition({
      x: Math.max(0, Math.min(newX, maxX)),
      y: Math.max(0, Math.min(newY, maxY))
    });
  }, [isDragging]);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.addEventListener('touchmove', handleTouchMove);
      document.addEventListener('touchend', handleMouseUp);
    }
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleMouseUp);
    };
  }, [isDragging, handleMouseMove, handleMouseUp, handleTouchMove]);

  return {
    position,
    isDragging,
    dragRef,
    handleMouseDown,
    handleTouchStart,
    resetPosition: () => setPosition(initialPosition)
  };
};

// Floating Help Button Component with Smart Badge - Now Draggable
export const FloatingHelpButton = () => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const { setShowHelpPanel, showHelpPanel, smartRecommendations } = useGuidance();
  const [pulse, setPulse] = useState(true);
  
  // Draggable functionality
  const { position, isDragging, dragRef, handleMouseDown, handleTouchStart } = useDraggable();

  // Calculate total pending items for badge
  const totalPending = smartRecommendations?.totalPending || 0;

  // Stop pulsing after first interaction
  useEffect(() => {
    if (showHelpPanel) {
      setPulse(false);
    }
  }, [showHelpPanel]);

  // Calculate position styles
  const positionStyle = position.x !== null && position.y !== null
    ? { left: position.x, top: position.y, right: 'auto', bottom: 'auto' }
    : { right: 24, bottom: 24 };

  return (
    <div
      ref={dragRef}
      style={positionStyle}
      className={`
        fixed z-50
        ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}
      `}
    >
      <button
        onClick={() => !isDragging && setShowHelpPanel(true)}
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
        data-testid="floating-help-btn"
        className={`
          w-14 h-14 rounded-full shadow-lg
          flex items-center justify-center
          transition-all duration-300 hover:scale-110
          ${isDark 
            ? 'bg-gradient-to-br from-orange-500 to-orange-600 hover:from-orange-400 hover:to-orange-500' 
            : 'bg-gradient-to-br from-orange-500 to-orange-600 hover:from-orange-400 hover:to-orange-500'
          }
          ${pulse && totalPending === 0 ? 'animate-pulse' : ''}
          ${isDragging ? 'scale-105 shadow-2xl' : ''}
        `}
        title={totalPending > 0 ? `${totalPending} items need attention - Drag to move` : "Need help? Click here! Drag to move"}
      >
        <HelpCircle className="w-7 h-7 text-white" />
        
        {/* Smart Badge - shows pending items count */}
        {totalPending > 0 && (
          <span className="absolute -top-1 -right-1 w-6 h-6 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center shadow-md animate-bounce">
            {totalPending > 9 ? '9+' : totalPending}
          </span>
        )}
        
        {/* Ripple effect when no pending items */}
        {pulse && totalPending === 0 && (
          <span className="absolute inset-0 rounded-full bg-orange-400 animate-ping opacity-30" />
        )}
      </button>
    </div>
  );
};

// Help Panel Component
export const HelpPanel = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const { pendingCounts } = useApprovals();
  
  const { 
    showHelpPanel, 
    setShowHelpPanel, 
    startWorkflow,
    getWorkflowsForPage,
    PAGE_TIPS,
    smartRecommendations
  } = useGuidance();

  const [activeTab, setActiveTab] = useState('smart');
  const [aiQuery, setAiQuery] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResponse, setAiResponse] = useState(null);
  const [suggestedRoute, setSuggestedRoute] = useState(null);
  
  // Help Articles state (from backend API)
  const [helpSearchQuery, setHelpSearchQuery] = useState('');
  const [helpSearchResults, setHelpSearchResults] = useState([]);
  const [contextTopics, setContextTopics] = useState([]);
  const [helpCategories, setHelpCategories] = useState([]);
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [categoryTopics, setCategoryTopics] = useState([]);
  const [helpLoading, setHelpLoading] = useState(false);
  const [whatsNew, setWhatsNew] = useState([]);

  const currentPageTips = PAGE_TIPS[location.pathname];
  const relevantWorkflows = getWorkflowsForPage(location.pathname);
  
  // Fetch context-aware help topics when panel opens
  useEffect(() => {
    if (showHelpPanel && user) {
      fetchContextTopics();
      fetchCategories();
      fetchWhatsNew();
    }
  }, [showHelpPanel, location.pathname, user]);
  
  const fetchContextTopics = async () => {
    try {
      const res = await axios.get(`${API}/help/context`, {
        params: { route: location.pathname, role: user?.role }
      });
      setContextTopics(res.data.topics || []);
    } catch (err) {
      console.error('Failed to fetch context topics:', err);
    }
  };
  
  const fetchCategories = async () => {
    try {
      const res = await axios.get(`${API}/help/categories`, {
        params: { role: user?.role }
      });
      setHelpCategories(res.data || []);
    } catch (err) {
      console.error('Failed to fetch categories:', err);
    }
  };
  
  const fetchWhatsNew = async () => {
    try {
      const res = await axios.get(`${API}/help/whats-new`, {
        params: { role: user?.role, limit: 5 }
      });
      setWhatsNew(res.data.items || []);
    } catch (err) {
      console.error('Failed to fetch whats new:', err);
    }
  };
  
  const handleHelpSearch = async (query) => {
    if (!query.trim()) {
      setHelpSearchResults([]);
      return;
    }
    setHelpLoading(true);
    try {
      const res = await axios.get(`${API}/help/search`, {
        params: { q: query, role: user?.role }
      });
      setHelpSearchResults(res.data.results || []);
    } catch (err) {
      console.error('Help search failed:', err);
    } finally {
      setHelpLoading(false);
    }
  };
  
  const openHelpTopic = async (topicId) => {
    setHelpLoading(true);
    try {
      const res = await axios.get(`${API}/help/topics/${topicId}`, {
        params: { role: user?.role }
      });
      setSelectedTopic(res.data);
      setSelectedCategory(null);
      // Track view
      axios.post(`${API}/help/topics/${topicId}/view`).catch(() => {});
    } catch (err) {
      console.error('Failed to load topic:', err);
    } finally {
      setHelpLoading(false);
    }
  };
  
  const openCategory = async (category) => {
    setHelpLoading(true);
    setSelectedCategory(category);
    setSelectedTopic(null);
    try {
      const res = await axios.get(`${API}/help/categories/${category.id}/topics`, {
        params: { role: user?.role }
      });
      setCategoryTopics(res.data || []);
    } catch (err) {
      console.error('Failed to load category topics:', err);
    } finally {
      setHelpLoading(false);
    }
  };
  
  const sendHelpFeedback = async (topicId, helpful) => {
    try {
      await axios.post(`${API}/help/topics/${topicId}/feedback`, { helpful });
    } catch (err) {
      console.error('Failed to send feedback:', err);
    }
  };
  
  const goBackInHelp = () => {
    if (selectedTopic) {
      setSelectedTopic(null);
    } else if (selectedCategory) {
      setSelectedCategory(null);
      setCategoryTopics([]);
    }
  };

  // Get all workflows grouped by category
  const workflowCategories = {
    'Daily Tasks': ['attendance_checkin', 'attendance_regularize', 'leave_request', 'expense_submit'],
    'Sales Flow': ['sales_lead_to_quotation', 'sales_quotation_to_agreement', 'sales_agreement_to_kickoff'],
    'HR & Onboarding': ['employee_onboarding', 'permission_change', 'approval_process'],
    'Meetings & Tasks': ['schedule_meeting', 'create_task', 'create_followup'],
    'Administration': ['manage_masters']
  };

  // Handle AI query
  const handleAskAI = async () => {
    if (!aiQuery.trim()) return;
    
    setAiLoading(true);
    setAiResponse(null);
    setSuggestedRoute(null);

    try {
      const token = localStorage.getItem('token');
      const res = await axios.post(`${API}/ai/guidance-help`, {
        query: aiQuery,
        current_page: location.pathname,
        user_role: user?.role
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      setAiResponse(res.data.response);
      
      // Check if AI suggested a route
      if (res.data.suggested_route) {
        setSuggestedRoute(res.data.suggested_route);
      }
      
      // Auto-navigate if configured
      if (res.data.auto_navigate && res.data.suggested_route) {
        setTimeout(() => {
          navigate(res.data.suggested_route);
          setShowHelpPanel(false);
        }, 2000);
      }
    } catch (error) {
      console.error('AI help error:', error);
      setAiResponse('Sorry, I encountered an error. Please try again or navigate manually.');
    } finally {
      setAiLoading(false);
    }
  };

  // Start workflow and navigate
  const handleStartWorkflow = (workflowId) => {
    const workflow = WORKFLOWS[workflowId];
    if (workflow) {
      startWorkflow(workflowId);
      const firstStep = workflow.steps[0];
      if (firstStep.route) {
        navigate(firstStep.route);
      }
      setShowHelpPanel(false);
    }
  };

  // Navigate to suggested route
  const handleNavigateToSuggested = () => {
    if (suggestedRoute) {
      navigate(suggestedRoute);
      setShowHelpPanel(false);
    }
  };

  // Navigate and close panel
  const handleNavigateTo = (route) => {
    navigate(route);
    setShowHelpPanel(false);
  };

  // Quick action suggestions based on role
  const getQuickActions = () => {
    const baseActions = [
      { label: 'Check my attendance', query: 'How do I check in for today?' },
      { label: 'Apply for leave', query: 'How do I apply for leave?' },
      { label: 'Submit an expense', query: 'How do I submit an expense claim?' }
    ];

    if (['admin', 'hr_manager', 'hr_executive'].includes(user?.role)) {
      baseActions.push(
        { label: 'Onboard an employee', query: 'How do I onboard a new employee?' },
        { label: 'Approve pending items', query: 'Take me to pending approvals' }
      );
    }

    if (['admin', 'manager', 'sales_manager', 'executive'].includes(user?.role)) {
      baseActions.push(
        { label: 'Create a quotation', query: 'How do I create a quotation?' },
        { label: 'Convert lead to client', query: 'How do I convert a lead to quotation?' }
      );
    }

    return baseActions.slice(0, 5);
  };

  // Determine which tabs to show based on role and pending items
  const hasPendingItems = smartRecommendations?.totalPending > 0;

  return (
    <Dialog open={showHelpPanel} onOpenChange={setShowHelpPanel}>
      <DialogContent className={`${isDark ? 'bg-zinc-900 border-zinc-700' : ''} max-w-2xl max-h-[85vh] overflow-hidden flex flex-col`}>
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className={`text-xl font-semibold flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            How can I help you?
          </DialogTitle>
        </DialogHeader>

        {/* Tabs */}
        <div className={`flex border-b ${isDark ? 'border-zinc-700' : 'border-zinc-200'} -mx-6 px-6 overflow-x-auto`}>
          {[
            { id: 'smart', label: 'Smart Suggestions', icon: Bell, badge: smartRecommendations?.totalPending },
            { id: 'help', label: 'Help Articles', icon: HelpCircle, badge: whatsNew.length > 0 ? whatsNew.length : null },
            { id: 'ai', label: 'Ask AI', icon: Bot },
            { id: 'workflows', label: 'Guides', icon: List },
            { id: 'tips', label: 'Tips', icon: Lightbulb }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-orange-500 text-orange-600'
                  : `border-transparent ${isDark ? 'text-zinc-400 hover:text-zinc-200' : 'text-zinc-500 hover:text-zinc-700'}`
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
              {tab.badge > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-xs font-bold bg-red-500 text-white rounded-full">
                  {tab.badge > 9 ? '9+' : tab.badge}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto py-4 -mx-6 px-6">
          
          {/* Smart Suggestions Tab */}
          {activeTab === 'smart' && (
            <div className="space-y-4">
              {smartRecommendations?.totalPending > 0 ? (
                <>
                  {/* Summary Banner */}
                  <div className={`p-4 rounded-lg ${isDark ? 'bg-orange-900/30 border border-orange-700' : 'bg-orange-50 border border-orange-200'}`}>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-orange-500 flex items-center justify-center">
                        <AlertCircle className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <p className={`font-semibold ${isDark ? 'text-orange-200' : 'text-orange-800'}`}>
                          {smartRecommendations.totalPending} items need your attention
                        </p>
                        <p className={`text-sm ${isDark ? 'text-orange-300' : 'text-orange-600'}`}>
                          Review and take action on pending items
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Pending Items List */}
                  <div className="space-y-3">
                    {smartRecommendations.items.map((item, idx) => (
                      <div
                        key={idx}
                        onClick={() => handleNavigateTo(item.route)}
                        className={`p-4 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
                          isDark 
                            ? 'bg-zinc-800 border-zinc-700 hover:border-orange-600' 
                            : 'bg-white border-zinc-200 hover:border-orange-400'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                              item.priority === 'high' 
                                ? 'bg-red-100 text-red-600' 
                                : item.priority === 'medium'
                                  ? 'bg-amber-100 text-amber-600'
                                  : 'bg-blue-100 text-blue-600'
                            }`}>
                              {item.icon === 'leaves' && <Calendar className="w-5 h-5" />}
                              {item.icon === 'expenses' && <Receipt className="w-5 h-5" />}
                              {item.icon === 'attendance' && <Clock className="w-5 h-5" />}
                              {item.icon === 'ctc' && <Users className="w-5 h-5" />}
                              {item.icon === 'bank' && <ClipboardCheck className="w-5 h-5" />}
                              {!['leaves', 'expenses', 'attendance', 'ctc', 'bank'].includes(item.icon) && <ClipboardCheck className="w-5 h-5" />}
                            </div>
                            <div>
                              <p className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                                {item.title}
                              </p>
                              <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                                {item.description}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                              item.priority === 'high'
                                ? 'bg-red-100 text-red-700'
                                : item.priority === 'medium'
                                  ? 'bg-amber-100 text-amber-700'
                                  : 'bg-blue-100 text-blue-700'
                            }`}>
                              {item.count} pending
                            </span>
                            <ChevronRight className={`w-5 h-5 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`} />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Quick Action */}
                  <Button
                    onClick={() => handleNavigateTo('/approvals')}
                    className="w-full bg-orange-500 hover:bg-orange-600 text-white"
                  >
                    <ClipboardCheck className="w-4 h-4 mr-2" />
                    Go to Approval Center
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                </>
              ) : (
                /* All caught up state */
                <div className={`text-center py-12 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-100 flex items-center justify-center">
                    <CheckCircle2 className="w-8 h-8 text-emerald-600" />
                  </div>
                  <p className={`text-lg font-medium ${isDark ? 'text-zinc-200' : 'text-zinc-700'}`}>
                    You're all caught up!
                  </p>
                  <p className="mt-1">No pending items need your attention.</p>
                  <Button
                    onClick={() => setActiveTab('ai')}
                    variant="outline"
                    className="mt-4"
                  >
                    <Bot className="w-4 h-4 mr-2" />
                    Ask AI for help
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Help Articles Tab */}
          {activeTab === 'help' && (
            <div className="space-y-4">
              {/* Back Button */}
              {(selectedTopic || selectedCategory) && (
                <button
                  onClick={goBackInHelp}
                  className={`flex items-center gap-2 text-sm ${isDark ? 'text-zinc-400 hover:text-zinc-200' : 'text-zinc-500 hover:text-zinc-700'}`}
                >
                  <ChevronLeft className="w-4 h-4" />
                  Back
                </button>
              )}
              
              {/* Topic Detail View */}
              {selectedTopic && (
                <HelpTopicDetail 
                  topic={selectedTopic} 
                  isDark={isDark} 
                  onFeedback={sendHelpFeedback}
                  onOpenRelated={openHelpTopic}
                />
              )}
              
              {/* Category Topics View */}
              {selectedCategory && !selectedTopic && (
                <div className="space-y-3">
                  <h3 className={`font-semibold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                    {selectedCategory.name}
                  </h3>
                  {helpLoading ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-orange-500" />
                    </div>
                  ) : categoryTopics.length > 0 ? (
                    <div className="space-y-2">
                      {categoryTopics.map(topic => (
                        <button
                          key={topic.id}
                          onClick={() => openHelpTopic(topic.id)}
                          className={`w-full text-left p-3 rounded-lg border transition-colors ${
                            isDark ? 'bg-zinc-800 border-zinc-700 hover:border-orange-600' : 'bg-white border-zinc-200 hover:border-orange-400'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <HelpTopicIcon type={topic.type} />
                            <span className={`text-sm font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{topic.title}</span>
                            {topic.isNew && <span className="px-1.5 py-0.5 text-[10px] font-bold bg-green-500 text-white rounded">NEW</span>}
                          </div>
                          {topic.excerpt && (
                            <p className={`text-xs mt-1 ml-6 line-clamp-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>{topic.excerpt}</p>
                          )}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className={`text-center py-4 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>No topics in this category</p>
                  )}
                </div>
              )}
              
              {/* Main Help View */}
              {!selectedTopic && !selectedCategory && (
                <>
                  {/* Search */}
                  <div className={`flex gap-2 p-3 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                    <input
                      type="text"
                      value={helpSearchQuery}
                      onChange={(e) => {
                        setHelpSearchQuery(e.target.value);
                        handleHelpSearch(e.target.value);
                      }}
                      placeholder="Search help articles..."
                      className={`flex-1 bg-transparent border-none outline-none text-sm ${
                        isDark ? 'text-zinc-100 placeholder:text-zinc-500' : 'text-zinc-900 placeholder:text-zinc-400'
                      }`}
                    />
                    {helpLoading && <Loader2 className="w-4 h-4 animate-spin text-orange-500" />}
                  </div>
                  
                  {/* Search Results */}
                  {helpSearchQuery && helpSearchResults.length > 0 && (
                    <div className="space-y-2">
                      <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                        {helpSearchResults.length} results for "{helpSearchQuery}"
                      </p>
                      {helpSearchResults.map(result => (
                        <button
                          key={result.id}
                          onClick={() => openHelpTopic(result.id)}
                          className={`w-full text-left p-3 rounded-lg border transition-colors ${
                            isDark ? 'bg-zinc-800 border-zinc-700 hover:border-orange-600' : 'bg-white border-zinc-200 hover:border-orange-400'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <HelpTopicIcon type={result.type} />
                            <span className={`text-sm font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{result.title}</span>
                          </div>
                          {result.excerpt && (
                            <p className={`text-xs mt-1 ml-6 line-clamp-2 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>{result.excerpt}</p>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                  
                  {/* Context-Aware Topics */}
                  {!helpSearchQuery && contextTopics.length > 0 && (
                    <div>
                      <p className={`text-sm font-medium mb-2 flex items-center gap-2 ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>
                        <Lightbulb className="w-4 h-4" />
                        Help for this page
                      </p>
                      <div className="space-y-2">
                        {contextTopics.slice(0, 4).map(topic => (
                          <button
                            key={topic.id}
                            onClick={() => openHelpTopic(topic.id)}
                            className={`w-full text-left p-3 rounded-lg transition-colors ${
                              isDark ? 'bg-amber-900/30 hover:bg-amber-900/50' : 'bg-amber-50 hover:bg-amber-100'
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <HelpTopicIcon type={topic.type} />
                              <span className={`text-sm ${isDark ? 'text-amber-100' : 'text-amber-900'}`}>{topic.title}</span>
                              {topic.isNew && <span className="px-1.5 py-0.5 text-[10px] font-bold bg-green-500 text-white rounded">NEW</span>}
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* What's New */}
                  {!helpSearchQuery && whatsNew.length > 0 && (
                    <div>
                      <p className={`text-sm font-medium mb-2 flex items-center gap-2 ${isDark ? 'text-green-400' : 'text-green-600'}`}>
                        <Sparkles className="w-4 h-4" />
                        What's New
                      </p>
                      <div className="space-y-2">
                        {whatsNew.slice(0, 3).map(item => (
                          <button
                            key={item.id}
                            onClick={() => openHelpTopic(item.id)}
                            className={`w-full text-left p-3 rounded-lg border transition-colors ${
                              isDark ? 'bg-green-900/20 border-green-800 hover:border-green-600' : 'bg-green-50 border-green-200 hover:border-green-400'
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <span className={`text-sm font-medium ${isDark ? 'text-green-100' : 'text-green-900'}`}>{item.title}</span>
                              <span className="px-1.5 py-0.5 text-[10px] font-bold bg-green-500 text-white rounded">NEW</span>
                            </div>
                            <p className={`text-xs mt-1 line-clamp-1 ${isDark ? 'text-green-300' : 'text-green-700'}`}>{item.introduction}</p>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Browse Categories */}
                  {!helpSearchQuery && helpCategories.length > 0 && (
                    <div>
                      <p className={`text-sm font-medium mb-2 ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                        Browse by Module
                      </p>
                      <div className="grid grid-cols-2 gap-2">
                        {helpCategories.map(cat => (
                          <button
                            key={cat.id}
                            onClick={() => openCategory(cat)}
                            className={`p-3 rounded-lg border text-left transition-colors ${
                              isDark ? 'bg-zinc-800 border-zinc-700 hover:border-orange-600' : 'bg-white border-zinc-200 hover:border-orange-400'
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-lg">{cat.icon}</span>
                              <div className="flex-1 min-w-0">
                                <p className={`text-sm font-medium truncate ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{cat.name}</p>
                                <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>{cat.topicCount} topics</p>
                              </div>
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Empty State */}
                  {!helpSearchQuery && contextTopics.length === 0 && helpCategories.length === 0 && (
                    <div className={`text-center py-8 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                      <HelpCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>No help content available yet.</p>
                      <p className="text-sm mt-1">Try asking the AI assistant!</p>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* AI Tab */}
          {activeTab === 'ai' && (
            <div className="space-y-4">
              {/* Quick Actions */}
              <div>
                <p className={`text-sm font-medium mb-2 ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                  Quick actions:
                </p>
                <div className="flex flex-wrap gap-2">
                  {getQuickActions().map((action, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setAiQuery(action.query);
                        handleAskAI();
                      }}
                      className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
                        isDark 
                          ? 'border-zinc-600 hover:bg-zinc-800 text-zinc-300' 
                          : 'border-zinc-200 hover:bg-zinc-50 text-zinc-600'
                      }`}
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* AI Input */}
              <div className={`flex gap-2 p-3 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                <input
                  type="text"
                  value={aiQuery}
                  onChange={(e) => setAiQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAskAI()}
                  placeholder="Ask me anything... (e.g., 'How do I create a quotation?')"
                  className={`flex-1 bg-transparent border-none outline-none text-sm ${
                    isDark ? 'text-zinc-100 placeholder:text-zinc-500' : 'text-zinc-900 placeholder:text-zinc-400'
                  }`}
                />
                <Button
                  size="sm"
                  onClick={handleAskAI}
                  disabled={aiLoading || !aiQuery.trim()}
                  className="bg-orange-500 hover:bg-orange-600 text-white"
                >
                  {aiLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </Button>
              </div>

              {/* AI Response */}
              {aiResponse && (
                <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-blue-50'}`}>
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center flex-shrink-0">
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex-1">
                      <p className={`text-sm whitespace-pre-wrap ${isDark ? 'text-zinc-200' : 'text-zinc-700'}`}>
                        {aiResponse}
                      </p>
                      
                      {/* Navigation suggestion */}
                      {suggestedRoute && (
                        <Button
                          size="sm"
                          onClick={handleNavigateToSuggested}
                          className="mt-3 bg-blue-600 hover:bg-blue-700 text-white"
                        >
                          <Navigation className="w-4 h-4 mr-2" />
                          Take me there
                          <ArrowRight className="w-4 h-4 ml-2" />
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Workflows Tab */}
          {activeTab === 'workflows' && (
            <div className="space-y-6">
              {/* Relevant workflows for current page */}
              {relevantWorkflows.length > 0 && (
                <div>
                  <p className={`text-sm font-medium mb-2 flex items-center gap-2 ${isDark ? 'text-orange-400' : 'text-orange-600'}`}>
                    <Sparkles className="w-4 h-4" />
                    Suggested for this page
                  </p>
                  <div className="space-y-2">
                    {relevantWorkflows.map(workflow => (
                      <WorkflowCard
                        key={workflow.id}
                        workflow={workflow}
                        onStart={() => handleStartWorkflow(workflow.id)}
                        isDark={isDark}
                        highlighted
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* All workflows by category */}
              {Object.entries(workflowCategories).map(([category, workflowIds]) => (
                <div key={category}>
                  <p className={`text-sm font-medium mb-2 ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                    {category}
                  </p>
                  <div className="space-y-2">
                    {workflowIds.map(id => {
                      const workflow = WORKFLOWS[id];
                      if (!workflow) return null;
                      return (
                        <WorkflowCard
                          key={id}
                          workflow={workflow}
                          onStart={() => handleStartWorkflow(id)}
                          isDark={isDark}
                        />
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Tips Tab */}
          {activeTab === 'tips' && (
            <div className="space-y-4">
              {currentPageTips ? (
                <>
                  <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-amber-50'}`}>
                    <div className="flex items-start gap-3">
                      <Lightbulb className={`w-5 h-5 flex-shrink-0 ${isDark ? 'text-amber-400' : 'text-amber-500'}`} />
                      <div>
                        <p className={`text-sm font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                          About this page
                        </p>
                        <p className={`text-sm mt-1 ${isDark ? 'text-zinc-300' : 'text-zinc-600'}`}>
                          {currentPageTips.firstVisit}
                        </p>
                      </div>
                    </div>
                  </div>

                  {currentPageTips.tips && currentPageTips.tips.length > 0 && (
                    <div>
                      <p className={`text-sm font-medium mb-2 ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                        Pro Tips:
                      </p>
                      <ul className="space-y-2">
                        {currentPageTips.tips.map((tip, idx) => (
                          <li
                            key={idx}
                            className={`flex items-center gap-2 text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}
                          >
                            <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                            {tip}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              ) : (
                <div className={`text-center py-8 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                  <Lightbulb className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No specific tips for this page.</p>
                  <p className="text-sm mt-1">Try the AI assistant for help!</p>
                </div>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

// Workflow Card Component
const WorkflowCard = ({ workflow, onStart, isDark, highlighted = false }) => (
  <div
    className={`p-3 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
      highlighted
        ? isDark ? 'border-orange-600 bg-orange-900/20' : 'border-orange-300 bg-orange-50'
        : isDark ? 'border-zinc-700 hover:border-zinc-600' : 'border-zinc-200 hover:border-zinc-300'
    }`}
    onClick={onStart}
  >
    <div className="flex items-center justify-between">
      <div>
        <h4 className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          {workflow.title}
        </h4>
        <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
          {workflow.description}
        </p>
        <p className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
          {workflow.steps.length} steps
        </p>
      </div>
      <ChevronRight className={`w-5 h-5 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`} />
    </div>
  </div>
);

// Active Workflow Overlay - Now Draggable
export const WorkflowOverlay = () => {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const { activeWorkflow, closeWorkflow, guidanceState, completeWorkflowStep } = useGuidance();
  
  // Draggable functionality
  const { position, isDragging, dragRef, handleMouseDown, handleTouchStart, resetPosition } = useDraggable();

  if (!activeWorkflow) return null;

  const currentStepIndex = (guidanceState.workflow_progress[activeWorkflow.id] || 1) - 1;
  const currentStep = activeWorkflow.steps[currentStepIndex];
  const isLastStep = currentStepIndex >= activeWorkflow.steps.length - 1;

  const handleNext = () => {
    if (isLastStep) {
      closeWorkflow();
    } else {
      completeWorkflowStep(activeWorkflow.id, currentStepIndex + 1);
      const nextStep = activeWorkflow.steps[currentStepIndex + 1];
      if (nextStep?.route) {
        navigate(nextStep.route);
      }
    }
  };

  const handlePrev = () => {
    if (currentStepIndex > 0) {
      const prevStepIndex = currentStepIndex - 1;
      completeWorkflowStep(activeWorkflow.id, prevStepIndex);
      const prevStep = activeWorkflow.steps[prevStepIndex];
      if (prevStep?.route) {
        navigate(prevStep.route);
      }
    }
  };

  // Calculate position styles
  const positionStyle = position.x !== null && position.y !== null
    ? { left: position.x, top: position.y, right: 'auto', bottom: 'auto' }
    : { right: 24, bottom: 96 };

  return (
    <div 
      ref={dragRef}
      style={positionStyle}
      className={`
        fixed z-50 w-80
        rounded-xl shadow-2xl border overflow-hidden
        ${isDark ? 'bg-zinc-900 border-zinc-700' : 'bg-white border-zinc-200'}
        ${isDragging ? 'shadow-[0_20px_50px_rgba(0,0,0,0.3)]' : ''}
      `}
    >
      {/* Draggable Header */}
      <div 
        className={`px-4 py-3 ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'} ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Move className={`w-4 h-4 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`} />
            <List className="w-4 h-4 text-orange-500" />
            <span className={`text-sm font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
              {activeWorkflow.title}
            </span>
          </div>
          <button onClick={closeWorkflow} className={isDark ? 'text-zinc-400 hover:text-zinc-200' : 'text-zinc-500 hover:text-zinc-700'}>
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="flex items-center gap-1 mt-2">
          {activeWorkflow.steps.map((_, idx) => (
            <div
              key={idx}
              className={`h-1 flex-1 rounded-full ${
                idx < currentStepIndex 
                  ? 'bg-emerald-500' 
                  : idx === currentStepIndex 
                    ? 'bg-orange-500' 
                    : isDark ? 'bg-zinc-700' : 'bg-zinc-200'
              }`}
            />
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="flex items-start gap-3">
          <div className={`
            w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
            ${isDark ? 'bg-orange-900/50 text-orange-400' : 'bg-orange-100 text-orange-600'}
          `}>
            {currentStepIndex + 1}
          </div>
          <div className="flex-1">
            <h4 className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
              {currentStep.title}
            </h4>
            {currentStep.action && (
              <p className={`text-sm mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                {currentStep.action}
              </p>
            )}
          </div>
        </div>

        {/* Steps preview */}
        <div className="mt-4 space-y-2">
          {activeWorkflow.steps.map((step, idx) => (
            <div
              key={idx}
              className={`flex items-center gap-2 text-sm ${
                idx < currentStepIndex 
                  ? isDark ? 'text-emerald-400' : 'text-emerald-600'
                  : idx === currentStepIndex
                    ? isDark ? 'text-orange-400 font-medium' : 'text-orange-600 font-medium'
                    : isDark ? 'text-zinc-500' : 'text-zinc-400'
              }`}
            >
              {idx < currentStepIndex ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : idx === currentStepIndex ? (
                <Circle className="w-4 h-4 fill-current" />
              ) : (
                <Circle className="w-4 h-4" />
              )}
              <span className="truncate">{step.title}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className={`px-4 py-3 flex items-center justify-between ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
        <Button
          variant="outline"
          size="sm"
          onClick={handlePrev}
          disabled={currentStepIndex === 0}
          className={isDark ? 'border-zinc-600' : ''}
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          Back
        </Button>
        <Button
          size="sm"
          onClick={handleNext}
          className="bg-orange-500 hover:bg-orange-600 text-white"
        >
          {isLastStep ? (
            <>
              <CheckCircle2 className="w-4 h-4 mr-1" />
              Done
            </>
          ) : (
            <>
              Next
              <ChevronRight className="w-4 h-4 ml-1" />
            </>
          )}
        </Button>
      </div>
    </div>
  );
};

// Smart Tip Component
export const SmartTip = ({ tipId, children, position = 'bottom' }) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const { isTipDismissed, dismissTip, guidanceState } = useGuidance();
  const [show, setShow] = useState(false);

  useEffect(() => {
    // Show tip after a short delay if not dismissed
    if (!isTipDismissed(tipId) && !guidanceState.dont_show_tips) {
      const timer = setTimeout(() => setShow(true), 1500);
      return () => clearTimeout(timer);
    }
  }, [tipId, isTipDismissed, guidanceState.dont_show_tips]);

  if (!show) return null;

  const handleDismiss = () => {
    setShow(false);
    dismissTip(tipId);
  };

  const positionClasses = {
    top: 'bottom-full mb-2',
    bottom: 'top-full mt-2',
    left: 'right-full mr-2',
    right: 'left-full ml-2'
  };

  return (
    <div className={`absolute ${positionClasses[position]} z-50 animate-in fade-in slide-in-from-bottom-2`}>
      <div className={`
        p-3 rounded-lg shadow-lg max-w-xs
        ${isDark ? 'bg-amber-900/90 border border-amber-700' : 'bg-amber-50 border border-amber-200'}
      `}>
        <div className="flex items-start gap-2">
          <Lightbulb className={`w-4 h-4 flex-shrink-0 mt-0.5 ${isDark ? 'text-amber-400' : 'text-amber-500'}`} />
          <div className="flex-1">
            <p className={`text-sm ${isDark ? 'text-amber-100' : 'text-amber-900'}`}>
              {children}
            </p>
          </div>
          <button onClick={handleDismiss} className={isDark ? 'text-amber-400 hover:text-amber-200' : 'text-amber-500 hover:text-amber-700'}>
            <X className="w-4 h-4" />
          </button>
        </div>
        <button
          onClick={handleDismiss}
          className={`text-xs mt-2 ${isDark ? 'text-amber-400' : 'text-amber-600'} hover:underline`}
        >
          Don't show this again
        </button>
      </div>
    </div>
  );
};

// New Feature Badge
export const NewFeatureBadge = ({ featureId }) => {
  const { isFeatureNew, markFeatureSeen } = useGuidance();

  useEffect(() => {
    // Mark as seen after 3 seconds of being visible
    if (isFeatureNew(featureId)) {
      const timer = setTimeout(() => markFeatureSeen(featureId), 3000);
      return () => clearTimeout(timer);
    }
  }, [featureId, isFeatureNew, markFeatureSeen]);

  if (!isFeatureNew(featureId)) return null;

  return (
    <span className="ml-2 px-1.5 py-0.5 text-[10px] font-bold uppercase bg-orange-500 text-white rounded animate-pulse">
      New
    </span>
  );
};

export default { FloatingHelpButton, HelpPanel, WorkflowOverlay, SmartTip, NewFeatureBadge };
