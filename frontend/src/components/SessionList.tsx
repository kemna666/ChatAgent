import { SessionResponse } from '../types';
import { FiCheck, FiEdit2, FiMoreHorizontal, FiTrash2, FiX } from 'react-icons/fi';
import { useEffect, useState } from 'react';
import { useLanguage } from '../contexts/LanguageContext';

interface SessionListProps {
  sessions: SessionResponse[];
  currentSession: SessionResponse | null;
  onSelectSession: (session: SessionResponse) => void;
  onDeleteSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, newName: string) => void;
}

export default function SessionList({
  sessions,
  currentSession,
  onSelectSession,
  onDeleteSession,
  onRenameSession,
}: SessionListProps) {
  const { t } = useLanguage();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);

  useEffect(() => {
    const handleWindowClick = () => {
      setMenuOpenId(null);
    };

    window.addEventListener('click', handleWindowClick);
    return () => window.removeEventListener('click', handleWindowClick);
  }, []);

  const startEdit = (session: SessionResponse) => {
    setEditingId(session.session_id);
    setEditingName(session.name);
    setMenuOpenId(null);
  };

  const confirmRename = async (sessionId: string) => {
    if (editingName.trim() && editingName !== sessions.find(s => s.session_id === sessionId)?.name) {
      await onRenameSession(sessionId, editingName.trim());
    }
    setEditingId(null);
    setEditingName('');
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditingName('');
  };

  const toggleMenu = (sessionId: string) => {
    setMenuOpenId(current => current === sessionId ? null : sessionId);
  };

  return (
    <div className="flex-1 overflow-y-auto">
      {sessions.length === 0 ? (
        <div className="p-4 text-center text-gray-500 text-sm">
          {t('noConversations')}
        </div>
      ) : (
        <div className="space-y-2 p-2">
          {sessions.map((session) => (
            <div key={session.session_id} className="relative flex items-center gap-2 group">
              {editingId === session.session_id ? (
                <>
                  <input
                    type="text"
                    value={editingName}
                    onChange={(e) => setEditingName(e.target.value)}
                    className="flex-1 px-2 py-1 text-sm border border-blue-500 rounded bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-400"
                    autoFocus
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        confirmRename(session.session_id);
                      }
                    }}
                  />
                  <button
                    onClick={() => confirmRename(session.session_id)}
                    className="text-green-600 hover:text-green-800 p-1.5 rounded transition"
                    title={t('confirmRename')}
                  >
                    <FiCheck size={16} />
                  </button>
                  <button
                    onClick={cancelEdit}
                    className="text-gray-600 hover:text-gray-800 p-1.5 rounded transition"
                    title={t('cancelEdit')}
                  >
                    <FiX size={16} />
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => onSelectSession(session)}
                    className={`flex-1 text-left px-3 py-2 rounded-lg transition ${
                      currentSession?.session_id === session.session_id
                        ? 'bg-blue-100 text-blue-900 font-medium'
                        : 'hover:bg-gray-100 text-gray-700'
                    }`}
                    title={session.name}
                  >
                    <p className="truncate text-sm">{session.name}</p>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleMenu(session.session_id);
                    }}
                    className="text-gray-500 hover:text-gray-700 p-1.5 hover:bg-gray-100 rounded transition opacity-100 md:opacity-0 md:group-hover:opacity-100"
                    title={t('moreOptions')}
                  >
                    <FiMoreHorizontal size={16} />
                  </button>
                  {menuOpenId === session.session_id && (
                    <div
                      onClick={(e) => e.stopPropagation()}
                      className="absolute right-0 top-11 z-20 min-w-36 rounded-xl border border-gray-200 bg-white p-1.5 shadow-lg"
                    >
                      <button
                        onClick={() => startEdit(session)}
                        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-700 transition hover:bg-gray-100"
                      >
                        <FiEdit2 size={15} />
                        {t('rename')}
                      </button>
                      <button
                        onClick={() => {
                          setMenuOpenId(null);
                          onDeleteSession(session.session_id);
                        }}
                        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-600 transition hover:bg-red-50"
                      >
                        <FiTrash2 size={15} />
                        {t('delete')}
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
