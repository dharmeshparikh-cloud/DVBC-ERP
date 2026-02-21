import React, { useState, useEffect, useRef, useCallback, useContext } from 'react';
import { Send, Search, Plus, Users, MessageCircle, Pin, Check, CheckCheck, Paperclip, MoreVertical, X, FileText, ExternalLink } from 'lucide-react';
import { AuthContext } from '../App';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Chat = () => {
  const { user: currentUser } = useContext(AuthContext);
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [users, setUsers] = useState([]);
  const [searchUsers, setSearchUsers] = useState('');
  const [showNewChat, setShowNewChat] = useState(false);
  const [showNewGroup, setShowNewGroup] = useState(false);
  const [groupName, setGroupName] = useState('');
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchConversations = useCallback(async () => {
    if (!currentUser.id) return;
    try {
      const res = await fetch(`${API_URL}/api/chat/conversations?user_id=${currentUser.id}`);
      const data = await res.json();
      setConversations(data);
    } catch (error) {
      console.error('Error fetching conversations:', error);
    }
  }, [currentUser.id]);

  const fetchMessages = useCallback(async (conversationId) => {
    try {
      const res = await fetch(`${API_URL}/api/chat/conversations/${conversationId}/messages`);
      const data = await res.json();
      setMessages(data);
      
      // Mark all as read
      await fetch(`${API_URL}/api/chat/conversations/${conversationId}/read-all?user_id=${currentUser.id}`, {
        method: 'POST'
      });
    } catch (error) {
      console.error('Error fetching messages:', error);
    }
  }, [currentUser.id]);

  const fetchUsers = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/chat/users?search=${searchUsers}`);
      const data = await res.json();
      setUsers(data.filter(u => u.id !== currentUser.id));
    } catch (error) {
      console.error('Error fetching users:', error);
    }
  }, [searchUsers, currentUser.id]);

  useEffect(() => {
    fetchConversations();
    const interval = setInterval(fetchConversations, 10000);
    return () => clearInterval(interval);
  }, [fetchConversations]);

  useEffect(() => {
    if (selectedConversation) {
      fetchMessages(selectedConversation.id);
      const interval = setInterval(() => fetchMessages(selectedConversation.id), 5000);
      return () => clearInterval(interval);
    }
  }, [selectedConversation, fetchMessages]);

  useEffect(() => {
    if (showNewChat || showNewGroup) {
      fetchUsers();
    }
  }, [showNewChat, showNewGroup, searchUsers, fetchUsers]);

  const startDMConversation = async (user) => {
    try {
      const res = await fetch(`${API_URL}/api/chat/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'dm',
          participant_ids: [currentUser.id, user.id]
        })
      });
      const conv = await res.json();
      setSelectedConversation(conv);
      setShowNewChat(false);
      fetchConversations();
    } catch (error) {
      console.error('Error starting conversation:', error);
    }
  };

  const createGroupConversation = async () => {
    if (!groupName || selectedUsers.length === 0) return;
    try {
      const res = await fetch(`${API_URL}/api/chat/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'group',
          name: groupName,
          participant_ids: [currentUser.id, ...selectedUsers.map(u => u.id)]
        })
      });
      const conv = await res.json();
      setSelectedConversation(conv);
      setShowNewGroup(false);
      setGroupName('');
      setSelectedUsers([]);
      fetchConversations();
    } catch (error) {
      console.error('Error creating group:', error);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedConversation) return;
    
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/chat/conversations/${selectedConversation.id}/messages?sender_id=${currentUser.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: newMessage,
          message_type: 'text'
        })
      });
      
      if (res.ok) {
        setNewMessage('');
        fetchMessages(selectedConversation.id);
      }
    } catch (error) {
      console.error('Error sending message:', error);
    }
    setLoading(false);
  };

  const executeAction = async (messageId, action) => {
    try {
      const res = await fetch(`${API_URL}/api/chat/messages/${messageId}/action?user_id=${currentUser.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      });
      
      if (res.ok) {
        fetchMessages(selectedConversation.id);
      }
    } catch (error) {
      console.error('Error executing action:', error);
    }
  };

  const getConversationName = (conv) => {
    if (conv.type === 'group') return conv.name;
    const other = conv.participants?.find(p => p.id !== currentUser.id);
    return other?.name || 'Unknown';
  };

  const getConversationAvatar = (conv) => {
    if (conv.type === 'group') {
      return (
        <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
          <Users className="w-6 h-6 text-white" />
        </div>
      );
    }
    const other = conv.participants?.find(p => p.id !== currentUser.id);
    const initials = other?.name?.split(' ').map(n => n[0]).join('').slice(0, 2) || '?';
    return (
      <div className="w-12 h-12 bg-gradient-to-br from-orange-400 to-pink-500 rounded-full flex items-center justify-center">
        <span className="text-white font-semibold">{initials}</span>
      </div>
    );
  };

  const formatTime = (dateStr) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 86400000) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    if (diff < 604800000) {
      return date.toLocaleDateString([], { weekday: 'short' });
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  return (
    <div className="h-[calc(100vh-120px)] flex bg-gray-50 rounded-xl overflow-hidden shadow-lg" data-testid="chat-container">
      {/* Sidebar */}
      <div className="w-80 bg-white border-r flex flex-col">
        {/* Header */}
        <div className="p-4 border-b">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-800">Messages</h2>
            <div className="flex gap-2">
              <button
                onClick={() => setShowNewChat(true)}
                className="p-2 hover:bg-gray-100 rounded-lg transition"
                title="New Chat"
                data-testid="new-chat-btn"
              >
                <MessageCircle className="w-5 h-5 text-gray-600" />
              </button>
              <button
                onClick={() => setShowNewGroup(true)}
                className="p-2 hover:bg-gray-100 rounded-lg transition"
                title="New Group"
                data-testid="new-group-btn"
              >
                <Users className="w-5 h-5 text-gray-600" />
              </button>
            </div>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search conversations..."
              className="w-full pl-10 pr-4 py-2 bg-gray-100 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
            />
          </div>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => setSelectedConversation(conv)}
              className={`flex items-center gap-3 p-4 cursor-pointer hover:bg-gray-50 transition ${
                selectedConversation?.id === conv.id ? 'bg-orange-50 border-r-2 border-orange-500' : ''
              }`}
              data-testid={`conversation-${conv.id}`}
            >
              {getConversationAvatar(conv)}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-800 truncate">{getConversationName(conv)}</span>
                  {conv.last_message && (
                    <span className="text-xs text-gray-400">{formatTime(conv.last_message.created_at)}</span>
                  )}
                </div>
                {conv.last_message && (
                  <p className="text-sm text-gray-500 truncate">{conv.last_message.content}</p>
                )}
              </div>
              {conv.unread_count > 0 && (
                <span className="bg-orange-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                  {conv.unread_count}
                </span>
              )}
            </div>
          ))}
          
          {conversations.length === 0 && (
            <div className="p-8 text-center text-gray-500">
              <MessageCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No conversations yet</p>
              <p className="text-sm">Start a new chat!</p>
            </div>
          )}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        {selectedConversation ? (
          <>
            {/* Chat Header */}
            <div className="p-4 bg-white border-b flex items-center justify-between">
              <div className="flex items-center gap-3">
                {getConversationAvatar(selectedConversation)}
                <div>
                  <h3 className="font-semibold text-gray-800">{getConversationName(selectedConversation)}</h3>
                  <p className="text-sm text-gray-500">
                    {selectedConversation.type === 'group' 
                      ? `${selectedConversation.participants?.length || 0} members`
                      : 'Direct Message'}
                  </p>
                </div>
              </div>
              <button className="p-2 hover:bg-gray-100 rounded-lg">
                <MoreVertical className="w-5 h-5 text-gray-600" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((msg) => {
                const isOwn = msg.sender_id === currentUser.id;
                return (
                  <div
                    key={msg.id}
                    className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-[70%] ${isOwn ? 'order-2' : ''}`}>
                      {!isOwn && (
                        <span className="text-xs text-gray-500 ml-2">{msg.sender_name}</span>
                      )}
                      <div
                        className={`p-3 rounded-2xl ${
                          isOwn 
                            ? 'bg-orange-500 text-white rounded-tr-sm' 
                            : 'bg-white shadow-sm rounded-tl-sm'
                        }`}
                      >
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                        
                        {/* ERP Record Card */}
                        {msg.erp_record && (
                          <div className={`mt-2 p-3 rounded-lg ${isOwn ? 'bg-orange-600' : 'bg-gray-100'}`}>
                            <div className="flex items-center gap-2 mb-2">
                              <FileText className="w-4 h-4" />
                              <span className="font-medium capitalize">
                                {msg.erp_record.type?.replace('_', ' ')}
                              </span>
                            </div>
                            {msg.erp_record.data && (
                              <div className="text-sm space-y-1">
                                {Object.entries(msg.erp_record.data).slice(0, 3).map(([key, value]) => (
                                  <div key={key} className="flex justify-between">
                                    <span className="opacity-75 capitalize">{key.replace('_', ' ')}:</span>
                                    <span>{String(value)}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Action Buttons */}
                        {msg.action_buttons && !msg.action_taken && (
                          <div className="flex gap-2 mt-3">
                            {msg.action_buttons.map((btn, idx) => (
                              <button
                                key={idx}
                                onClick={() => executeAction(msg.id, btn.action)}
                                className={`px-4 py-1.5 rounded-full text-sm font-medium transition ${
                                  btn.action === 'approve' 
                                    ? 'bg-green-500 hover:bg-green-600 text-white'
                                    : btn.action === 'reject'
                                    ? 'bg-red-500 hover:bg-red-600 text-white'
                                    : 'bg-blue-500 hover:bg-blue-600 text-white'
                                }`}
                              >
                                {btn.label}
                              </button>
                            ))}
                          </div>
                        )}

                        {/* Action Taken */}
                        {msg.action_taken && (
                          <div className={`mt-2 p-2 rounded text-sm ${
                            msg.action_taken.action === 'approve' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}>
                            <Check className="w-4 h-4 inline mr-1" />
                            {msg.action_taken.action === 'approve' ? 'Approved' : 'Rejected'} by {msg.action_taken.executed_by_name}
                          </div>
                        )}
                      </div>
                      
                      <div className={`flex items-center gap-1 mt-1 text-xs text-gray-400 ${isOwn ? 'justify-end' : ''}`}>
                        <span>{formatTime(msg.created_at)}</span>
                        {isOwn && (
                          msg.read_by?.length > 1 
                            ? <CheckCheck className="w-4 h-4 text-blue-500" />
                            : <Check className="w-4 h-4" />
                        )}
                        {msg.is_pinned && <Pin className="w-3 h-3 text-orange-500" />}
                      </div>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Message Input */}
            <form onSubmit={sendMessage} className="p-4 bg-white border-t">
              <div className="flex items-center gap-3">
                <button type="button" className="p-2 hover:bg-gray-100 rounded-lg">
                  <Paperclip className="w-5 h-5 text-gray-500" />
                </button>
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  placeholder="Type a message..."
                  className="flex-1 px-4 py-2 bg-gray-100 rounded-full focus:outline-none focus:ring-2 focus:ring-orange-500"
                  data-testid="message-input"
                />
                <button
                  type="submit"
                  disabled={loading || !newMessage.trim()}
                  className="p-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
                  data-testid="send-message-btn"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </form>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center bg-gray-50">
            <div className="text-center">
              <MessageCircle className="w-16 h-16 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-gray-600">Select a conversation</h3>
              <p className="text-gray-400">or start a new chat</p>
            </div>
          </div>
        )}
      </div>

      {/* New Chat Modal */}
      {showNewChat && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl w-full max-w-md p-6" data-testid="new-chat-modal">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">New Chat</h3>
              <button onClick={() => setShowNewChat(false)} className="p-1 hover:bg-gray-100 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchUsers}
                onChange={(e) => setSearchUsers(e.target.value)}
                placeholder="Search users..."
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
              />
            </div>
            <div className="max-h-64 overflow-y-auto space-y-2">
              {users.map((user) => (
                <div
                  key={user.id}
                  onClick={() => startDMConversation(user)}
                  className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg cursor-pointer"
                >
                  <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center">
                    <span className="text-white text-sm font-medium">
                      {user.full_name?.split(' ').map(n => n[0]).join('').slice(0, 2)}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-800">{user.full_name}</p>
                    <p className="text-sm text-gray-500">{user.department}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* New Group Modal */}
      {showNewGroup && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl w-full max-w-md p-6" data-testid="new-group-modal">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">New Group</h3>
              <button onClick={() => { setShowNewGroup(false); setSelectedUsers([]); setGroupName(''); }} className="p-1 hover:bg-gray-100 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <input
              type="text"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              placeholder="Group name..."
              className="w-full px-4 py-2 border rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-orange-500"
            />

            {selectedUsers.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-4">
                {selectedUsers.map((user) => (
                  <span key={user.id} className="inline-flex items-center gap-1 px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-sm">
                    {user.full_name}
                    <X 
                      className="w-4 h-4 cursor-pointer" 
                      onClick={() => setSelectedUsers(selectedUsers.filter(u => u.id !== user.id))}
                    />
                  </span>
                ))}
              </div>
            )}

            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchUsers}
                onChange={(e) => setSearchUsers(e.target.value)}
                placeholder="Add members..."
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
              />
            </div>

            <div className="max-h-48 overflow-y-auto space-y-2 mb-4">
              {users.filter(u => !selectedUsers.find(s => s.id === u.id)).map((user) => (
                <div
                  key={user.id}
                  onClick={() => setSelectedUsers([...selectedUsers, user])}
                  className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg cursor-pointer"
                >
                  <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center">
                    <span className="text-white text-sm font-medium">
                      {user.full_name?.split(' ').map(n => n[0]).join('').slice(0, 2)}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-800">{user.full_name}</p>
                    <p className="text-sm text-gray-500">{user.department}</p>
                  </div>
                  <Plus className="w-5 h-5 text-gray-400 ml-auto" />
                </div>
              ))}
            </div>

            <button
              onClick={createGroupConversation}
              disabled={!groupName || selectedUsers.length === 0}
              className="w-full py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              Create Group
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Chat;
