import { useState, useEffect, useRef } from 'react';
import { FiSend, FiTrash2, FiMenu, FiX } from 'react-icons/fi';
import { Message, SessionResponse } from '../types';
import { apiService } from '../services/api';
import MessageBubble from '../components/MessageBubble';
import SessionList from '../components/SessionList';

interface ChatPageProps {
  onLogout: () => void;
}

export default function ChatPage({ onLogout }: ChatPageProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [currentSession, setCurrentSession] = useState<SessionResponse | null>(null);
  const [showSidebar, setShowSidebar] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  // Load messages when session changes
  useEffect(() => {
    if (currentSession) {
      loadMessages();
    }
  }, [currentSession]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadSessions = async () => {
    try {
      const data = await apiService.getSessions();
      setSessions(data);
      if (data.length > 0 && !currentSession) {
        setCurrentSession(data[0]);
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  };

  const loadMessages = async () => {
    if (!currentSession) return;
    try {
      const data = await apiService.getMessages(currentSession.session_id);
      setMessages(data.messages || []);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!input.trim() || !currentSession || loading) return;

    const userMessage: Message = { role: 'user', content: input };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    try {
      // Use streaming chat
      const response = await apiService.streamChat(newMessages, currentSession.session_id);
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantContent = '';

      if (reader) {
        let assistantAdded = false;
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data:')) {
              try {
                const jsonStr = line.slice(5).trim();
                if (jsonStr) {
                  const data = JSON.parse(jsonStr);
                  assistantContent += data.content;

                  if (!assistantAdded) {
                    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);
                    assistantAdded = true;
                  }

                  setMessages(prev => {
                    const updated = [...prev];
                    if (updated.length > 0) {
                      updated[updated.length - 1] = {
                        role: 'assistant',
                        content: assistantContent,
                      };
                    }
                    return updated;
                  });
                }
              } catch (e) {
                console.error('Parse error:', e);
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, failed to get response. Please try again.',
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSession = async () => {
    const sessionName = `Chat ${new Date().toLocaleDateString()}`;
    try {
      const newSession = await apiService.createSession(sessionName);
      setSessions(prev => [...prev, newSession]);
      setCurrentSession(newSession);
      setMessages([]);
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await apiService.deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.session_id !== sessionId));
      if (currentSession?.session_id === sessionId) {
        const remaining = sessions.filter(s => s.session_id !== sessionId);
        setCurrentSession(remaining.length > 0 ? remaining[0] : null);
        setMessages([]);
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const handleRenameSession = async (sessionId: string, newName: string) => {
    try {
      const updatedSession = await apiService.updateSessionName(sessionId, newName);
      setSessions(prev =>
        prev.map(s =>
          s.session_id === sessionId
            ? { ...s, name: updatedSession.name }
            : s
        )
      );
      if (currentSession?.session_id === sessionId) {
        setCurrentSession({ ...currentSession, name: updatedSession.name });
      }
    } catch (error) {
      console.error('Failed to rename session:', error);
    }
  };

  const handleClearHistory = async () => {
    if (!currentSession) return;
    try {
      await apiService.clearHistory(currentSession.session_id);
      setMessages([]);
    } catch (error) {
      console.error('Failed to clear history:', error);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div
        className={`${
          showSidebar ? 'w-64' : 'w-0'
        } transition-all duration-300 bg-white border-r border-gray-200 flex flex-col overflow-hidden`}
      >
        <div className="p-4 border-b border-gray-200">
          <button
            onClick={handleCreateSession}
            className="w-full bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded-lg transition"
          >
            + New Chat
          </button>
        </div>
        <SessionList
          sessions={sessions}
          currentSession={currentSession}
          onSelectSession={setCurrentSession}
          onDeleteSession={handleDeleteSession}
          onRenameSession={handleRenameSession}
        />
        <div className="mt-auto p-4 border-t border-gray-200">
          <button
            onClick={onLogout}
            className="w-full bg-red-500 hover:bg-red-600 text-white font-semibold py-2 px-4 rounded-lg transition"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 p-4 flex items-center justify-between">
          <button
            onClick={() => setShowSidebar(!showSidebar)}
            className="md:hidden text-gray-600 hover:text-gray-900 text-2xl"
          >
            {showSidebar ? <FiX /> : <FiMenu />}
          </button>
          <h1 className="text-2xl font-bold text-gray-900">
            {currentSession?.name || 'ChatAgent'}
          </h1>
          {currentSession && (
            <button
              onClick={handleClearHistory}
              className="flex items-center gap-2 text-red-500 hover:text-red-700 transition"
              title="Clear chat history"
            >
              <FiTrash2 size={20} />
            </button>
          )}
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-500">
                <p className="text-lg mb-2">Welcome to ChatAgent</p>
                <p className="text-sm">Start a conversation to get help with your questions</p>
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <MessageBubble key={idx} message={msg} />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="bg-white border-t border-gray-200 p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Type your message..."
              disabled={!currentSession || loading}
              className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            />
            <button
              onClick={handleSendMessage}
              disabled={!currentSession || loading || !input.trim()}
              className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 text-white font-semibold py-2 px-4 rounded-lg transition flex items-center gap-2"
            >
              <FiSend size={20} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
