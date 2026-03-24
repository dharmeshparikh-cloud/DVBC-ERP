import React, { useState, useEffect, useContext, useCallback, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import axios from 'axios';
import { AuthContext, API } from '../../App';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import { Separator } from '../ui/separator';
import { 
  HelpCircle, X, Search, ChevronRight, ChevronLeft, BookOpen, 
  Lightbulb, AlertTriangle, PlayCircle, Image, FileText, 
  ExternalLink, ThumbsUp, ThumbsDown, MessageCircle, Loader2,
  Home, ArrowLeft, Clock, Star, Bookmark, CheckCircle2
} from 'lucide-react';

// Help Widget Context for global state
const HelpContext = React.createContext();

export const useHelp = () => useContext(HelpContext);

// Main Help Widget Provider
export const HelpProvider = ({ children }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  
  const openHelp = (topicId = null) => {
    setIsOpen(true);
    setMinimized(false);
  };
  
  const closeHelp = () => setIsOpen(false);
  const toggleMinimize = () => setMinimized(!minimized);
  
  return (
    <HelpContext.Provider value={{ isOpen, openHelp, closeHelp, minimized, toggleMinimize }}>
      {children}
      <HelpWidget />
    </HelpContext.Provider>
  );
};

// Floating Help Button
const FloatingHelpButton = ({ onClick, hasUnread }) => (
  <button
    onClick={onClick}
    className="fixed bottom-6 right-6 z-50 w-14 h-14 bg-gradient-to-br from-orange-500 to-orange-600 
               text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-300 
               hover:scale-110 flex items-center justify-center group"
    data-testid="help-widget-btn"
    aria-label="Open Help"
  >
    <HelpCircle className="w-6 h-6 group-hover:scale-110 transition-transform" />
    {hasUnread && (
      <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full animate-pulse" />
    )}
  </button>
);

// Main Help Widget Component
const HelpWidget = () => {
  const { isOpen, closeHelp, minimized, toggleMinimize } = useHelp();
  const { user } = useContext(AuthContext);
  const location = useLocation();
  
  const [view, setView] = useState('home'); // home, search, topic, category
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [contextTopics, setContextTopics] = useState([]);
  const [categories, setCategories] = useState([]);
  const [currentTopic, setCurrentTopic] = useState(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [bookmarks, setBookmarks] = useState([]);
  const [recentTopics, setRecentTopics] = useState([]);
  
  // Get current route context
  const currentRoute = location.pathname;
  
  // Fetch context-aware topics when route changes
  useEffect(() => {
    if (isOpen && user) {
      fetchContextTopics();
      fetchCategories();
    }
  }, [currentRoute, isOpen, user]);
  
  // Load bookmarks and recent from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('help_bookmarks');
    const recent = localStorage.getItem('help_recent');
    if (saved) setBookmarks(JSON.parse(saved));
    if (recent) setRecentTopics(JSON.parse(recent));
  }, []);
  
  const fetchContextTopics = async () => {
    try {
      const res = await axios.get(`${API}/help/context`, {
        params: { route: currentRoute, role: user?.role }
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
      setCategories(res.data || []);
    } catch (err) {
      console.error('Failed to fetch categories:', err);
    }
  };
  
  const handleSearch = useCallback(async (query) => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }
    
    setLoading(true);
    try {
      const res = await axios.get(`${API}/help/search`, {
        params: { q: query, role: user?.role }
      });
      setSearchResults(res.data.results || []);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setLoading(false);
    }
  }, [user?.role]);
  
  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchQuery) {
        handleSearch(searchQuery);
        setView('search');
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, handleSearch]);
  
  const openTopic = async (topicId) => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/help/topics/${topicId}`, {
        params: { role: user?.role }
      });
      setCurrentTopic(res.data);
      setHistory(prev => [...prev, view]);
      setView('topic');
      
      // Track view
      axios.post(`${API}/help/topics/${topicId}/view`).catch(() => {});
      
      // Add to recent
      const recent = JSON.parse(localStorage.getItem('help_recent') || '[]');
      const updated = [{ id: topicId, title: res.data.title, viewedAt: new Date() }, 
                       ...(recent || []).filter(r => r.id !== topicId)].slice(0, 10);
      localStorage.setItem('help_recent', JSON.stringify(updated));
      setRecentTopics(updated);
    } catch (err) {
      console.error('Failed to load topic:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const goBack = () => {
    if (history.length > 0) {
      const prevView = history[history.length - 1];
      setHistory(prev => prev.slice(0, -1));
      setView(prevView);
      setCurrentTopic(null);
    } else {
      setView('home');
    }
  };
  
  const toggleBookmark = (topic) => {
    const isBookmarked = (bookmarks || []).some(b => b.id === topic.id);
    let updated;
    if (isBookmarked) {
      updated = (bookmarks || []).filter(b => b.id !== topic.id);
    } else {
      updated = [...bookmarks, { id: topic.id, title: topic.title }];
    }
    setBookmarks(updated);
    localStorage.setItem('help_bookmarks', JSON.stringify(updated));
  };
  
  const sendFeedback = async (topicId, helpful) => {
    try {
      await axios.post(`${API}/help/topics/${topicId}/feedback`, { helpful });
    } catch (err) {
      console.error('Failed to send feedback:', err);
    }
  };
  
  if (!isOpen) {
    return <FloatingHelpButton onClick={() => { setView('home'); setSearchQuery(''); }} hasUnread={false} />;
  }
  
  if (minimized) {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        <button
          onClick={toggleMinimize}
          className="bg-white border shadow-lg rounded-full px-4 py-2 flex items-center gap-2 hover:shadow-xl transition-shadow"
        >
          <HelpCircle className="w-5 h-5 text-orange-500" />
          <span className="text-sm font-medium">Help</span>
        </button>
      </div>
    );
  }
  
  return (
    <div 
      className="fixed bottom-6 right-6 z-50 w-96 h-[600px] bg-white rounded-2xl shadow-2xl 
                 border border-zinc-200 flex flex-col overflow-hidden animate-in slide-in-from-bottom-4"
      data-testid="help-widget-panel"
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-orange-500 to-orange-600 text-white p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            {view !== 'home' && (
              <button onClick={goBack} className="hover:bg-white/20 p-1 rounded">
                <ArrowLeft className="w-5 h-5" />
              </button>
            )}
            <BookOpen className="w-5 h-5" />
            <span className="font-semibold">Help Center</span>
          </div>
          <div className="flex items-center gap-1">
            <button onClick={toggleMinimize} className="hover:bg-white/20 p-1.5 rounded">
              <span className="text-lg">−</span>
            </button>
            <button onClick={closeHelp} className="hover:bg-white/20 p-1.5 rounded">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        
        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-orange-200" />
          <Input
            placeholder="Search help topics..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-white/20 border-white/30 text-white placeholder:text-orange-100 
                       focus:bg-white/30 focus:border-white"
          />
        </div>
      </div>
      
      {/* Content */}
      <ScrollArea className="flex-1">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
          </div>
        ) : (
          <>
            {view === 'home' && (
              <HomeView 
                contextTopics={contextTopics}
                categories={categories}
                recentTopics={recentTopics}
                bookmarks={bookmarks}
                currentRoute={currentRoute}
                onOpenTopic={openTopic}
                onSelectCategory={(cat) => { setView('category'); setCurrentTopic(cat); }}
              />
            )}
            
            {view === 'search' && (
              <SearchResults 
                results={searchResults}
                query={searchQuery}
                onOpenTopic={openTopic}
              />
            )}
            
            {view === 'topic' && currentTopic && (
              <TopicView 
                topic={currentTopic}
                isBookmarked={(bookmarks || []).some(b => b.id === currentTopic.id)}
                onToggleBookmark={() => toggleBookmark(currentTopic)}
                onFeedback={(helpful) => sendFeedback(currentTopic.id, helpful)}
                onOpenRelated={openTopic}
              />
            )}
            
            {view === 'category' && currentTopic && (
              <CategoryView 
                category={currentTopic}
                onOpenTopic={openTopic}
                userRole={user?.role}
              />
            )}
          </>
        )}
      </ScrollArea>
      
      {/* Footer */}
      <div className="border-t p-3 bg-zinc-50">
        <div className="flex items-center justify-between text-xs text-zinc-500">
          <span>Need more help?</span>
          <a 
            href="mailto:support@dvconsulting.co.in" 
            className="text-orange-500 hover:underline flex items-center gap-1"
          >
            <MessageCircle className="w-3 h-3" />
            Contact Support
          </a>
        </div>
      </div>
    </div>
  );
};

// Home View Component
const HomeView = ({ contextTopics, categories, recentTopics, bookmarks, currentRoute, onOpenTopic, onSelectCategory }) => {
  const routeLabels = {
    '/dashboard': 'Dashboard',
    '/employees': 'Employee Management',
    '/onboarding-hub': 'Onboarding Hub',
    '/go-live': 'Go-Live Dashboard',
    '/leave': 'Leave Management',
    '/attendance': 'Attendance',
    '/payroll': 'Payroll & CTC',
  };
  
  const currentPageLabel = Object.entries(routeLabels || {}).find(([route]) => 
    currentRoute.startsWith(route)
  )?.[1] || 'Current Page';
  
  return (
    <div className="p-4 space-y-6">
      {/* Context-Aware Section */}
      {contextTopics.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb className="w-4 h-4 text-amber-500" />
            <h3 className="font-semibold text-sm">Help for {currentPageLabel}</h3>
          </div>
          <div className="space-y-2">
            {(contextTopics || []).slice(0, 4).map(topic => (
              <button
                key={topic.id}
                onClick={() => onOpenTopic(topic.id)}
                className="w-full text-left p-3 bg-amber-50 hover:bg-amber-100 rounded-lg 
                           transition-colors group flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  {topic.type === 'guide' && <FileText className="w-4 h-4 text-amber-600" />}
                  {topic.type === 'troubleshoot' && <AlertTriangle className="w-4 h-4 text-amber-600" />}
                  {topic.type === 'video' && <PlayCircle className="w-4 h-4 text-amber-600" />}
                  <span className="text-sm">{topic.title}</span>
                </div>
                <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:text-amber-600" />
              </button>
            ))}
          </div>
        </div>
      )}
      
      {/* Quick Actions */}
      <div>
        <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
          <Star className="w-4 h-4 text-orange-500" />
          Quick Actions
        </h3>
        <div className="grid grid-cols-2 gap-2">
          <QuickActionButton icon={BookOpen} label="Getting Started" onClick={() => onOpenTopic('getting-started')} />
          <QuickActionButton icon={AlertTriangle} label="Troubleshooting" onClick={() => onSelectCategory({ id: 'troubleshooting', name: 'Troubleshooting' })} />
          <QuickActionButton icon={PlayCircle} label="Video Guides" onClick={() => onSelectCategory({ id: 'videos', name: 'Video Guides' })} />
          <QuickActionButton icon={FileText} label="All Topics" onClick={() => onSelectCategory({ id: 'all', name: 'All Help Topics' })} />
        </div>
      </div>
      
      {/* Categories */}
      <div>
        <h3 className="font-semibold text-sm mb-3">Browse by Module</h3>
        <div className="space-y-1">
          {(categories || []).map(cat => (
            <button
              key={cat.id}
              onClick={() => onSelectCategory(cat)}
              className="w-full text-left p-2.5 hover:bg-zinc-100 rounded-lg transition-colors 
                         flex items-center justify-between group"
            >
              <div className="flex items-center gap-2">
                <span className="text-lg">{cat.icon}</span>
                <span className="text-sm">{cat.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="text-xs">{cat.topicCount}</Badge>
                <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:text-zinc-600" />
              </div>
            </button>
          ))}
        </div>
      </div>
      
      {/* Recent & Bookmarks */}
      {(recentTopics.length > 0 || bookmarks.length > 0) && (
        <div>
          <Separator className="my-4" />
          
          {bookmarks.length > 0 && (
            <div className="mb-4">
              <h3 className="font-semibold text-sm mb-2 flex items-center gap-2">
                <Bookmark className="w-4 h-4 text-orange-500" />
                Bookmarked
              </h3>
              <div className="space-y-1">
                {(bookmarks || []).slice(0, 3).map(b => (
                  <button
                    key={b.id}
                    onClick={() => onOpenTopic(b.id)}
                    className="w-full text-left p-2 text-sm hover:bg-zinc-100 rounded transition-colors"
                  >
                    {b.title}
                  </button>
                ))}
              </div>
            </div>
          )}
          
          {recentTopics.length > 0 && (
            <div>
              <h3 className="font-semibold text-sm mb-2 flex items-center gap-2">
                <Clock className="w-4 h-4 text-zinc-400" />
                Recently Viewed
              </h3>
              <div className="space-y-1">
                {(recentTopics || []).slice(0, 3).map(r => (
                  <button
                    key={r.id}
                    onClick={() => onOpenTopic(r.id)}
                    className="w-full text-left p-2 text-sm text-zinc-600 hover:bg-zinc-100 rounded transition-colors"
                  >
                    {r.title}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Quick Action Button
const QuickActionButton = ({ icon: Icon, label, onClick }) => (
  <button
    onClick={onClick}
    className="p-3 bg-zinc-50 hover:bg-zinc-100 rounded-lg transition-colors text-center"
  >
    <Icon className="w-5 h-5 mx-auto mb-1 text-zinc-600" />
    <span className="text-xs text-zinc-600">{label}</span>
  </button>
);

// Search Results Component
const SearchResults = ({ results, query, onOpenTopic }) => (
  <div className="p-4">
    <p className="text-sm text-zinc-500 mb-4">
      {results.length} results for "{query}"
    </p>
    {results.length === 0 ? (
      <div className="text-center py-8">
        <Search className="w-12 h-12 mx-auto text-zinc-300 mb-3" />
        <p className="text-zinc-500">No results found</p>
        <p className="text-xs text-zinc-400 mt-1">Try different keywords</p>
      </div>
    ) : (
      <div className="space-y-2">
        {(results || []).map(result => (
          <button
            key={result.id}
            onClick={() => onOpenTopic(result.id)}
            className="w-full text-left p-3 bg-zinc-50 hover:bg-zinc-100 rounded-lg transition-colors"
          >
            <div className="flex items-start gap-2">
              <div className="flex-1">
                <p className="font-medium text-sm">{result.title}</p>
                <p className="text-xs text-zinc-500 mt-1 line-clamp-2">{result.excerpt}</p>
              </div>
              <Badge variant="outline" className="text-[10px] shrink-0">
                {result.category}
              </Badge>
            </div>
          </button>
        ))}
      </div>
    )}
  </div>
);

// Topic View Component
const TopicView = ({ topic, isBookmarked, onToggleBookmark, onFeedback, onOpenRelated }) => {
  const [feedbackGiven, setFeedbackGiven] = useState(null);
  
  const handleFeedback = (helpful) => {
    setFeedbackGiven(helpful);
    onFeedback(helpful);
  };
  
  return (
    <div className="p-4">
      {/* Topic Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Badge variant={topic.type === 'troubleshoot' ? 'destructive' : 'default'} className="text-[10px]">
              {topic.type === 'guide' && 'Guide'}
              {topic.type === 'troubleshoot' && 'Troubleshooting'}
              {topic.type === 'video' && 'Video'}
              {topic.type === 'faq' && 'FAQ'}
            </Badge>
            <span className="text-xs text-zinc-400">{topic.category}</span>
          </div>
          <h2 className="font-bold text-lg">{topic.title}</h2>
        </div>
        <button 
          onClick={onToggleBookmark}
          className={`p-2 rounded-lg transition-colors ${isBookmarked ? 'bg-orange-100 text-orange-600' : 'hover:bg-zinc-100'}`}
        >
          <Bookmark className={`w-5 h-5 ${isBookmarked ? 'fill-current' : ''}`} />
        </button>
      </div>
      
      {/* Content */}
      <div className="prose prose-sm max-w-none">
        {/* Introduction */}
        {topic.introduction && (
          <p className="text-zinc-600 mb-4">{topic.introduction}</p>
        )}
        
        {/* Video */}
        {topic.videoUrl && (
          <div className="mb-4 rounded-lg overflow-hidden bg-zinc-900 aspect-video flex items-center justify-center">
            <a href={topic.videoUrl} target="_blank" rel="noopener noreferrer" className="text-white flex items-center gap-2">
              <PlayCircle className="w-12 h-12" />
              <span>Watch Video</span>
            </a>
          </div>
        )}
        
        {/* Steps */}
        {topic.steps && topic.steps.length > 0 && (
          <div className="space-y-4 mb-6">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              Step-by-Step Instructions
            </h3>
            {(topic?.steps || []).map((step, idx) => (
              <div key={idx} className="flex gap-3 p-3 bg-zinc-50 rounded-lg">
                <div className="w-6 h-6 bg-orange-500 text-white rounded-full flex items-center justify-center text-sm font-bold shrink-0">
                  {idx + 1}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-sm">{step.title}</p>
                  <p className="text-xs text-zinc-600 mt-1">{step.description}</p>
                  {step.imageUrl && (
                    <img src={step.imageUrl} alt={step.title} className="mt-2 rounded border max-h-40 object-cover" />
                  )}
                  {step.tip && (
                    <div className="mt-2 p-2 bg-amber-50 rounded text-xs text-amber-700 flex items-start gap-1">
                      <Lightbulb className="w-3 h-3 mt-0.5 shrink-0" />
                      <span>{step.tip}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* Troubleshooting */}
        {topic.troubleshooting && topic.troubleshooting.length > 0 && (
          <div className="space-y-3 mb-6">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              Common Issues & Solutions
            </h3>
            {(topic?.troubleshooting || []).map((item, idx) => (
              <details key={idx} className="group bg-zinc-50 rounded-lg">
                <summary className="p-3 cursor-pointer font-medium text-sm flex items-center justify-between">
                  <span className="text-red-600">{item.problem}</span>
                  <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" />
                </summary>
                <div className="px-3 pb-3 text-sm text-zinc-600">
                  <p className="font-medium text-green-600 mb-1">Solution:</p>
                  <p>{item.solution}</p>
                </div>
              </details>
            ))}
          </div>
        )}
        
        {/* Additional Notes */}
        {topic.notes && (
          <div className="p-3 bg-blue-50 rounded-lg text-sm text-blue-700 mb-4">
            <p className="font-medium mb-1">Note:</p>
            <p>{topic.notes}</p>
          </div>
        )}
      </div>
      
      {/* Related Topics */}
      {topic.relatedTopics && topic.relatedTopics.length > 0 && (
        <div className="mt-6">
          <h3 className="font-semibold text-sm mb-2">Related Topics</h3>
          <div className="space-y-1">
            {(topic?.relatedTopics || []).map(related => (
              <button
                key={related.id}
                onClick={() => onOpenRelated(related.id)}
                className="w-full text-left p-2 text-sm hover:bg-zinc-100 rounded flex items-center gap-2"
              >
                <ChevronRight className="w-4 h-4 text-zinc-400" />
                {related.title}
              </button>
            ))}
          </div>
        </div>
      )}
      
      {/* Feedback */}
      <Separator className="my-6" />
      <div className="text-center">
        <p className="text-sm text-zinc-500 mb-3">Was this helpful?</p>
        {feedbackGiven === null ? (
          <div className="flex justify-center gap-3">
            <Button variant="outline" size="sm" onClick={() => handleFeedback(true)}>
              <ThumbsUp className="w-4 h-4 mr-1" />
              Yes
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleFeedback(false)}>
              <ThumbsDown className="w-4 h-4 mr-1" />
              No
            </Button>
          </div>
        ) : (
          <p className="text-sm text-green-600">Thanks for your feedback!</p>
        )}
      </div>
    </div>
  );
};

// Category View Component
const CategoryView = ({ category, onOpenTopic, userRole }) => {
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const fetchTopics = async () => {
      try {
        const res = await axios.get(`${API}/help/categories/${category.id}/topics`, {
          params: { role: userRole }
        });
        setTopics(res.data || []);
      } catch (err) {
        console.error('Failed to fetch topics:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchTopics();
  }, [category.id, userRole]);
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    );
  }
  
  return (
    <div className="p-4">
      <h2 className="font-bold text-lg mb-4">{category.name}</h2>
      {topics.length === 0 ? (
        <p className="text-zinc-500 text-center py-8">No topics in this category</p>
      ) : (
        <div className="space-y-2">
          {(topics || []).map(topic => (
            <button
              key={topic.id}
              onClick={() => onOpenTopic(topic.id)}
              className="w-full text-left p-3 bg-zinc-50 hover:bg-zinc-100 rounded-lg transition-colors group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {topic.type === 'guide' && <FileText className="w-4 h-4 text-blue-500" />}
                  {topic.type === 'troubleshoot' && <AlertTriangle className="w-4 h-4 text-amber-500" />}
                  {topic.type === 'video' && <PlayCircle className="w-4 h-4 text-red-500" />}
                  {topic.type === 'faq' && <HelpCircle className="w-4 h-4 text-green-500" />}
                  <span className="font-medium text-sm">{topic.title}</span>
                </div>
                <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:text-zinc-600" />
              </div>
              {topic.excerpt && (
                <p className="text-xs text-zinc-500 mt-1 ml-6 line-clamp-1">{topic.excerpt}</p>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default HelpWidget;
