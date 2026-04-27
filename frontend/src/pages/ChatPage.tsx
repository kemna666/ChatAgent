import { useState, useEffect, useRef } from 'react';
import { FiSend, FiTrash2, FiMenu, FiX } from 'react-icons/fi';
import { Message, SessionResponse } from '../types';
import { apiService } from '../services/api';
import MessageBubble from '../components/MessageBubble';
import SessionList from '../components/SessionList';
import { useLanguage } from '../contexts/LanguageContext';

interface ChatPageProps {
  onLogout: () => void;
}

function createLocalMessageId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  return `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function ChatPage({ onLogout }: ChatPageProps) {
  const { language, t } = useLanguage();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [currentSession, setCurrentSession] = useState<SessionResponse | null>(null);
  const [sessionPendingDeletion, setSessionPendingDeletion] = useState<SessionResponse | null>(null);
  const [messagePendingDeletion, setMessagePendingDeletion] = useState<Message | null>(null);
  const [deletingSession, setDeletingSession] = useState(false);
  const [deletingMessage, setDeletingMessage] = useState(false);
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

    const trimmedInput = input.trim();

    if (trimmedInput === '/clear') {
      setInput('');
      setLoading(true);
      try {
        await apiService.clearMemory(currentSession.session_id);
        setMessages(prev => [
          ...prev,
          {
            id: createLocalMessageId(),
            role: 'assistant',
            content: t('sessionMemoryCleared'),
            ephemeral: true,
          },
        ]);
      } catch (error) {
        console.error('Failed to clear session memory:', error);
        setMessages(prev => [
          ...prev,
          {
            id: createLocalMessageId(),
            role: 'assistant',
            content: t('sessionMemoryClearFailed'),
            ephemeral: true,
          },
        ]);
      } finally {
        setLoading(false);
      }
      return;
    }

    const userMessage: Message = {
      id: createLocalMessageId(),
      role: 'user',
      content: trimmedInput,
    };
    const uiMessages = [...messages, userMessage];
    const persistedMessages = [...messages.filter(message => !message.ephemeral), userMessage];
    setMessages(uiMessages);
    setInput('');
    setLoading(true);

    try {
      // Use streaming chat
      const response = await apiService.streamChat(persistedMessages, currentSession.session_id);
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantContent = '';
      let buffer = '';
      const assistantTempId = createLocalMessageId();

      if (reader) {
        let assistantAdded = false;
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split('\n\n');
          buffer = events.pop() || '';

          for (const event of events) {
            const line = event
              .split('\n')
              .find(part => part.startsWith('data:'));

            if (!line) {
              continue;
            }

            try {
              const jsonStr = line.slice(5).trim();
              if (!jsonStr) {
                continue;
              }

              const data = JSON.parse(jsonStr);
              if (!assistantAdded) {
                setMessages(prev => [...prev, { id: assistantTempId, role: 'assistant', content: '' }]);
                assistantAdded = true;
              }

              assistantContent = data.done ? data.content : assistantContent + data.content;

              setMessages(prev => {
                const updated = [...prev];
                if (updated.length > 0) {
                  updated[updated.length - 1] = {
                    id: data.message_id || updated[updated.length - 1].id || assistantTempId,
                    role: 'assistant',
                    content: assistantContent,
                  };
                }
                return updated;
              });
            } catch (e) {
              console.error('Parse error:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage: Message = {
        id: createLocalMessageId(),
        role: 'assistant',
        content: t('sendMessageFailed'),
        ephemeral: true,
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSession = async () => {
    const sessionName = t('sessionNameTemplate', {
      date: new Date().toLocaleDateString(language === 'zh' ? 'zh-CN' : 'en-US'),
    });
    try {
      const newSession = await apiService.createSession(sessionName);
      setSessions(prev => [...prev, newSession]);
      setCurrentSession(newSession);
      setMessages([]);
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  const promptDeleteSession = (sessionId: string) => {
    const targetSession = sessions.find(session => session.session_id === sessionId);
    if (!targetSession) {
      return;
    }

    setSessionPendingDeletion(targetSession);
  };

  const handleDeleteSession = async () => {
    if (!sessionPendingDeletion || deletingSession) return;

    const sessionId = sessionPendingDeletion.session_id;
    setDeletingSession(true);
    try {
      await apiService.deleteSession(sessionId);
      const remainingSessions = sessions.filter(session => session.session_id !== sessionId);
      setSessions(remainingSessions);

      if (currentSession?.session_id === sessionId) {
        setCurrentSession(remainingSessions.length > 0 ? remainingSessions[0] : null);
        setMessages([]);
      }
      setSessionPendingDeletion(null);
    } catch (error) {
      console.error('Failed to delete session:', error);
    } finally {
      setDeletingSession(false);
    }
  };

  const handleDeleteCurrentSession = async () => {
    if (!currentSession) return;
    promptDeleteSession(currentSession.session_id);
  };

  const promptDeleteMessage = (message: Message) => {
    if (!message.id || message.ephemeral) return;
    setMessagePendingDeletion(message);
  };

  const handleDeleteMessage = async () => {
    if (!currentSession || !messagePendingDeletion?.id || deletingMessage) return;

    setDeletingMessage(true);
    try {
      await apiService.deleteMessage(currentSession.session_id, messagePendingDeletion.id);
      setMessages(prev => prev.filter(message => message.id !== messagePendingDeletion.id));
      setMessagePendingDeletion(null);
    } catch (error) {
      console.error('Failed to delete message:', error);
    } finally {
      setDeletingMessage(false);
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
            {t('newChatButton')}
          </button>
        </div>
        <SessionList
          sessions={sessions}
          currentSession={currentSession}
          onSelectSession={setCurrentSession}
          onDeleteSession={promptDeleteSession}
          onRenameSession={handleRenameSession}
        />
        <div className="mt-auto p-4 border-t border-gray-200">
          <button
            onClick={onLogout}
            className="w-full bg-red-500 hover:bg-red-600 text-white font-semibold py-2 px-4 rounded-lg transition"
          >
            {t('logout')}
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
            <div className="flex items-center gap-2">
              <button
                onClick={handleClearHistory}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 transition hover:border-gray-400 hover:text-gray-900"
                title={t('clearHistory')}
              >
                {t('clearHistory')}
              </button>
              <button
                onClick={handleDeleteCurrentSession}
                className="flex items-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-sm font-medium text-red-500 transition hover:border-red-300 hover:text-red-700"
                title={t('deleteConversation')}
              >
                <FiTrash2 size={16} />
                {t('deleteConversation')}
              </button>
            </div>
          )}
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-500">
                <p className="text-lg mb-2">{t('welcomeTitle')}</p>
                <p className="text-sm">{t('welcomeSubtitle')}</p>
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <MessageBubble
                key={msg.id ?? idx}
                message={msg}
                onDelete={msg.id && !msg.ephemeral ? promptDeleteMessage : undefined}
                deleting={deletingMessage && messagePendingDeletion?.id === msg.id}
              />
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
              placeholder={t('inputPlaceholder')}
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
          <p className="mt-2 text-xs text-gray-500">
            {t('clearMemoryHint', { command: '/clear' })}
          </p>
        </div>
      </div>

      {sessionPendingDeletion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/45 px-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-6 shadow-2xl">
            <div className="flex items-start gap-4">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-600">
                <FiTrash2 size={18} />
              </div>
              <div className="min-w-0 flex-1">
                <h2 className="text-lg font-semibold text-gray-900">
                  {t('deleteConversationTitle')}
                </h2>
                <p className="mt-2 text-sm leading-6 text-gray-600">
                  {t('deleteConversationBody', {
                    name: sessionPendingDeletion.name || t('untitledConversation'),
                  })}
                </p>
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setSessionPendingDeletion(null)}
                disabled={deletingSession}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:border-gray-400 hover:text-gray-900 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {t('cancel')}
              </button>
              <button
                onClick={handleDeleteSession}
                disabled={deletingSession}
                className="rounded-lg bg-red-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-600 disabled:cursor-not-allowed disabled:bg-red-300"
              >
                {deletingSession ? t('deleting') : t('delete')}
              </button>
            </div>
          </div>
        </div>
      )}

      {messagePendingDeletion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/45 px-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-6 shadow-2xl">
            <div className="flex items-start gap-4">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-600">
                <FiTrash2 size={18} />
              </div>
              <div className="min-w-0 flex-1">
                <h2 className="text-lg font-semibold text-gray-900">
                  {t('deleteMessageTitle')}
                </h2>
                <p className="mt-2 text-sm leading-6 text-gray-600">
                  {t('deleteMessageBody')}
                </p>
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setMessagePendingDeletion(null)}
                disabled={deletingMessage}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:border-gray-400 hover:text-gray-900 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {t('cancel')}
              </button>
              <button
                onClick={handleDeleteMessage}
                disabled={deletingMessage}
                className="rounded-lg bg-red-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-600 disabled:cursor-not-allowed disabled:bg-red-300"
              >
                {deletingMessage ? t('deletingMessage') : t('delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
