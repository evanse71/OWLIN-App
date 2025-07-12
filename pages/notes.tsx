import React, { useState } from 'react';
import Layout from '@/components/Layout';

interface Note {
  id: string;
  title: string;
  content: string;
  author: string;
  timestamp: string;
  category: 'shift' | 'general' | 'urgent';
}

const NotesPage: React.FC = () => {
  const [notes, setNotes] = useState<Note[]>([
    {
      id: '1',
      title: 'Evening Shift Handover',
      content: 'All deliveries completed. Kitchen equipment cleaned and sanitized. No issues to report.',
      author: 'Sarah Johnson',
      timestamp: '2024-07-11 22:00',
      category: 'shift'
    },
    {
      id: '2',
      title: 'Supplier Delivery Issue',
      content: 'ABC Foods delivery was 30 minutes late. Quality was acceptable but timing needs improvement.',
      author: 'Mike Chen',
      timestamp: '2024-07-11 15:30',
      category: 'urgent'
    },
    {
      id: '3',
      title: 'New Staff Training',
      content: 'Completed orientation for 2 new kitchen staff. They start tomorrow morning shift.',
      author: 'Lisa Rodriguez',
      timestamp: '2024-07-11 14:00',
      category: 'general'
    }
  ]);

  const [newNote, setNewNote] = useState({
    title: '',
    content: '',
    category: 'general' as Note['category']
  });

  const [showForm, setShowForm] = useState(false);

  const addNote = () => {
    if (newNote.title.trim() && newNote.content.trim()) {
      const note: Note = {
        id: Date.now().toString(),
        title: newNote.title,
        content: newNote.content,
        author: 'Current User',
        timestamp: new Date().toLocaleString(),
        category: newNote.category
      };
      setNotes([note, ...notes]);
      setNewNote({ title: '', content: '', category: 'general' });
      setShowForm(false);
    }
  };

  const getCategoryColor = (category: Note['category']) => {
    switch (category) {
      case 'shift': return 'bg-blue-100 text-blue-800';
      case 'urgent': return 'bg-red-100 text-red-800';
      case 'general': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getCategoryIcon = (category: Note['category']) => {
    switch (category) {
      case 'shift': return '🔄';
      case 'urgent': return '⚠️';
      case 'general': return '📝';
      default: return '📝';
    }
  };

  return (
    <Layout>
      <div className="container mx-auto py-8 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Staff Notes</h1>
            <button
              onClick={() => setShowForm(!showForm)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              {showForm ? 'Cancel' : 'Add Note'}
            </button>
          </div>

          {/* Add Note Form */}
          {showForm && (
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Add New Note</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Title
                  </label>
                  <input
                    type="text"
                    value={newNote.title}
                    onChange={(e) => setNewNote({ ...newNote, title: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter note title..."
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Category
                  </label>
                  <select
                    value={newNote.category}
                    onChange={(e) => setNewNote({ ...newNote, category: e.target.value as Note['category'] })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="general">General</option>
                    <option value="shift">Shift Handover</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Content
                  </label>
                  <textarea
                    value={newNote.content}
                    onChange={(e) => setNewNote({ ...newNote, content: e.target.value })}
                    rows={4}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter note content..."
                  />
                </div>
                <div className="flex justify-end space-x-3">
                  <button
                    onClick={() => setShowForm(false)}
                    className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={addNote}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Save Note
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Notes List */}
          <div className="space-y-4">
            {notes.map((note) => (
              <div key={note.id} className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <span className="text-2xl">{getCategoryIcon(note.category)}</span>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{note.title}</h3>
                      <div className="flex items-center space-x-4 text-sm text-gray-500">
                        <span>{note.author}</span>
                        <span>•</span>
                        <span>{note.timestamp}</span>
                      </div>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(note.category)}`}>
                    {note.category.charAt(0).toUpperCase() + note.category.slice(1)}
                  </span>
                </div>
                <p className="text-gray-700 leading-relaxed">{note.content}</p>
              </div>
            ))}
          </div>

          {/* Quick Actions */}
          <div className="mt-8 bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Actions</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-colors text-center">
                <div className="text-2xl mb-2">🔄</div>
                <div className="font-medium text-gray-900">Shift Handover</div>
                <div className="text-sm text-gray-600">Quick shift summary</div>
              </button>
              <button className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-red-400 hover:bg-red-50 transition-colors text-center">
                <div className="text-2xl mb-2">⚠️</div>
                <div className="font-medium text-gray-900">Report Issue</div>
                <div className="text-sm text-gray-600">Urgent matters</div>
              </button>
              <button className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-green-400 hover:bg-green-50 transition-colors text-center">
                <div className="text-2xl mb-2">📊</div>
                <div className="font-medium text-gray-900">Daily Summary</div>
                <div className="text-sm text-gray-600">End of day report</div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default NotesPage; 