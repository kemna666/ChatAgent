import { SessionResponse } from '../types';
import { FiTrash2, FiEdit2, FiCheck, FiX } from 'react-icons/fi';
import { useState } from 'react';

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
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  const startEdit = (session: SessionResponse) => {
    setEditingId(session.session_id);
    setEditingName(session.name);
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

  return (
    <div className="flex-1 overflow-y-auto">
      {sessions.length === 0 ? (
        <div className="p-4 text-center text-gray-500 text-sm">
          No conversations yet
        </div>
      ) : (
        <div className="space-y-2 p-2">
          {sessions.map((session) => (
            <div key={session.session_id} className="flex items-center gap-2 group">
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
                    title="Confirm rename"
                  >
                    <FiCheck size={16} />
                  </button>
                  <button
                    onClick={cancelEdit}
                    className="text-gray-600 hover:text-gray-800 p-1.5 rounded transition"
                    title="Cancel"
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
                    onClick={() => startEdit(session)}
                    className="text-gray-500 hover:text-gray-700 p-1.5 hover:bg-gray-100 rounded transition opacity-0 group-hover:opacity-100"
                    title="Rename conversation"
                  >
                    <FiEdit2 size={16} />
                  </button>
                  <button
                    onClick={() => onDeleteSession(session.session_id)}
                    className="text-red-500 hover:text-red-700 p-1.5 hover:bg-gray-100 rounded transition opacity-0 group-hover:opacity-100"
                    title="Delete conversation"
                  >
                    <FiTrash2 size={16} />
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
