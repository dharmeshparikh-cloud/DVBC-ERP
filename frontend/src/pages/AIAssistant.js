import React, { useState, useEffect, useRef, useCallback, useContext } from 'react';
import { Send, Bot, User, Sparkles, TrendingUp, BarChart3, Lightbulb, RefreshCw, Trash2, Clock, ChevronRight } from 'lucide-react';
import { AuthContext } from '../App';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AIAssistant = () => {
  const { user: currentUser } = useContext(AuthContext);
  const [query, setQuery] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [quickInsights, setQuickInsights] = useState([]);
  const [activeContext, setActiveContext] = useState('all');
  const messagesEndRef = useRef(null);
  
  const sessionId = `ai_${currentUser?.id || 'anon'}_${new Date().toISOString().split('T')[0]}`;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  const fetchChatHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/ai/chat-history?user_id=${currentUser.id}&limit=20`);
      const data = await res.json();
      
      // Convert to chat format
      const history = [];
      data.reverse().forEach(item => {
        history.push({ role: 'user', content: item.query, timestamp: item.created_at });
        history.push({ role: 'assistant', content: item.response, timestamp: item.created_at });
      });
      setChatHistory(history);
    } catch (error) {
      console.error('Error fetching history:', error);
    }
  }, [currentUser.id]);

  const fetchQuickInsights = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/ai/quick-insights?user_id=${currentUser.id}`);
      const data = await res.json();
      setQuickInsights(data.insights || []);
    } catch (error) {
      console.error('Error fetching insights:', error);
    }
  }, [currentUser.id]);

  const fetchSuggestions = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/ai/suggestions?user_id=${currentUser.id}&context=${activeContext}`);
      const data = await res.json();
      setSuggestions(data.suggestions || []);
    } catch (error) {
      console.error('Error fetching suggestions:', error);
    }
  }, [currentUser.id, activeContext]);

  useEffect(() => {
    fetchChatHistory();
    fetchQuickInsights();
  }, [fetchChatHistory, fetchQuickInsights]);

  const sendQuery = async (e) => {
    e?.preventDefault();
    if (!query.trim() || loading) return;

    const userMessage = { role: 'user', content: query, timestamp: new Date().toISOString() };
    setChatHistory(prev => [...prev, userMessage]);
    setQuery('');
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/ai/query?user_id=${currentUser.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: userMessage.content,
          context: activeContext,
          session_id: sessionId
        })
      });
      
      const data = await res.json();
      
      const assistantMessage = {
        role: 'assistant',
        content: data.response,
        data: data.data,
        query_type: data.query_type,
        timestamp: new Date().toISOString()
      };
      
      setChatHistory(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error:', error);
      setChatHistory(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString()
      }]);
    }
    
    setLoading(false);
  };

  const analyzeReport = async (reportType) => {
    setLoading(true);
    const userMessage = { role: 'user', content: `Analyze my ${reportType} report`, timestamp: new Date().toISOString() };
    setChatHistory(prev => [...prev, userMessage]);

    try {
      const res = await fetch(`${API_URL}/api/ai/analyze-report?user_id=${currentUser.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          report_type: reportType,
          date_range: null
        })
      });
      
      const data = await res.json();
      
      setChatHistory(prev => [...prev, {
        role: 'assistant',
        content: data.analysis,
        data: data.data,
        timestamp: new Date().toISOString()
      }]);
    } catch (error) {
      console.error('Error:', error);
    }
    
    setLoading(false);
  };

  const clearHistory = async () => {
    try {
      await fetch(`${API_URL}/api/ai/chat-history?user_id=${currentUser.id}`, { method: 'DELETE' });
      setChatHistory([]);
    } catch (error) {
      console.error('Error clearing history:', error);
    }
  };

  const quickPrompts = [
    { text: "What's my sales performance this month?", icon: TrendingUp, color: 'text-green-500' },
    { text: "Show pending approvals summary", icon: Clock, color: 'text-orange-500' },
    { text: "Analyze employee attendance trends", icon: BarChart3, color: 'text-blue-500' },
    { text: "Suggest ways to improve conversion rate", icon: Lightbulb, color: 'text-yellow-500' }
  ];

  const contextOptions = [
    { value: 'all', label: 'All Data' },
    { value: 'sales', label: 'Sales' },
    { value: 'hr', label: 'HR' },
    { value: 'finance', label: 'Finance' },
    { value: 'projects', label: 'Projects' }
  ];

  return (
    <div className="h-[calc(100vh-120px)] flex gap-6" data-testid="ai-assistant-container">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-white rounded-xl shadow-lg overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b bg-gradient-to-r from-gray-900 to-gray-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-orange-400 to-pink-500 rounded-xl flex items-center justify-center">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">NETRA AI Assistant</h2>
                <p className="text-sm text-gray-400">Powered by GPT-4o</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={activeContext}
                onChange={(e) => setActiveContext(e.target.value)}
                className="bg-gray-700 text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-orange-500"
              >
                {contextOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <button
                onClick={clearHistory}
                className="p-2 hover:bg-gray-700 rounded-lg transition"
                title="Clear History"
              >
                <Trash2 className="w-5 h-5 text-gray-400" />
              </button>
            </div>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {chatHistory.length === 0 && (
            <div className="text-center py-8">
              <Sparkles className="w-12 h-12 mx-auto text-orange-400 mb-4" />
              <h3 className="text-lg font-medium text-gray-700 mb-2">How can I help you today?</h3>
              <p className="text-gray-500 mb-6">Ask me anything about your ERP data</p>
              
              <div className="grid grid-cols-2 gap-3 max-w-lg mx-auto">
                {quickPrompts.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => { setQuery(prompt.text); }}
                    className="flex items-center gap-2 p-3 bg-gray-50 hover:bg-gray-100 rounded-lg text-left transition"
                  >
                    <prompt.icon className={`w-5 h-5 ${prompt.color}`} />
                    <span className="text-sm text-gray-700">{prompt.text}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {chatHistory.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-[80%] flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  msg.role === 'user' 
                    ? 'bg-orange-500' 
                    : 'bg-gradient-to-br from-gray-700 to-gray-900'
                }`}>
                  {msg.role === 'user' 
                    ? <User className="w-4 h-4 text-white" />
                    : <Bot className="w-4 h-4 text-white" />
                  }
                </div>
                <div className={`p-4 rounded-2xl ${
                  msg.role === 'user'
                    ? 'bg-orange-500 text-white rounded-tr-sm'
                    : 'bg-gray-100 text-gray-800 rounded-tl-sm'
                }`}>
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</div>
                  
                  {/* Data Preview */}
                  {msg.data && (
                    <div className="mt-3 p-3 bg-white/10 rounded-lg text-sm">
                      <p className="font-medium mb-2 opacity-75">Data Summary:</p>
                      {Object.entries(msg.data).map(([key, value]) => (
                        <div key={key} className="flex justify-between py-1 border-b border-white/10 last:border-0">
                          <span className="capitalize opacity-75">{key}:</span>
                          <span className="font-medium">
                            {typeof value === 'object' ? Object.keys(value).length + ' items' : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="flex gap-3">
                <div className="w-8 h-8 bg-gradient-to-br from-gray-700 to-gray-900 rounded-full flex items-center justify-center">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div className="p-4 bg-gray-100 rounded-2xl rounded-tl-sm">
                  <div className="flex items-center gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin text-gray-500" />
                    <span className="text-sm text-gray-500">Analyzing...</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={sendQuery} className="p-4 border-t bg-gray-50">
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask anything about your ERP data..."
              className="flex-1 px-4 py-3 bg-white border rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500"
              data-testid="ai-query-input"
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="p-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
              data-testid="ai-send-btn"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </form>
      </div>

      {/* Sidebar */}
      <div className="w-80 space-y-4">
        {/* Quick Insights */}
        <div className="bg-white rounded-xl shadow-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800">Quick Insights</h3>
            <button onClick={fetchQuickInsights} className="p-1 hover:bg-gray-100 rounded">
              <RefreshCw className="w-4 h-4 text-gray-400" />
            </button>
          </div>
          <div className="space-y-3">
            {quickInsights.map((insight, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-lg border-l-4 ${
                  insight.type === 'warning' ? 'bg-yellow-50 border-yellow-400' :
                  insight.type === 'success' ? 'bg-green-50 border-green-400' :
                  'bg-blue-50 border-blue-400'
                }`}
              >
                <p className="text-sm text-gray-700">{insight.message}</p>
                <button className="text-xs text-orange-600 font-medium mt-1 hover:underline">
                  {insight.action}
                </button>
              </div>
            ))}
            {quickInsights.length === 0 && (
              <p className="text-sm text-gray-500 text-center py-4">No insights available</p>
            )}
          </div>
        </div>

        {/* Quick Reports */}
        <div className="bg-white rounded-xl shadow-lg p-4">
          <h3 className="font-semibold text-gray-800 mb-4">Quick Reports</h3>
          <div className="space-y-2">
            {['sales', 'hr', 'finance', 'projects'].map((report) => (
              <button
                key={report}
                onClick={() => analyzeReport(report)}
                disabled={loading}
                className="w-full flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 rounded-lg transition disabled:opacity-50"
              >
                <span className="text-sm font-medium text-gray-700 capitalize">{report} Report</span>
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </button>
            ))}
          </div>
        </div>

        {/* AI Suggestions */}
        <div className="bg-white rounded-xl shadow-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800">AI Suggestions</h3>
            <button onClick={fetchSuggestions} className="p-1 hover:bg-gray-100 rounded">
              <Sparkles className="w-4 h-4 text-orange-400" />
            </button>
          </div>
          <div className="space-y-2">
            {suggestions.slice(0, 5).map((suggestion, idx) => (
              <div key={idx} className="p-3 bg-gradient-to-r from-orange-50 to-pink-50 rounded-lg">
                <p className="text-sm text-gray-700">{suggestion}</p>
              </div>
            ))}
            {suggestions.length === 0 && (
              <button
                onClick={fetchSuggestions}
                className="w-full text-sm text-orange-600 font-medium py-2 hover:underline"
              >
                Get AI Suggestions
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIAssistant;
