import React, { useEffect, useRef, useState } from 'react';
import { Bot, Loader2, Send, Trash2, User } from 'lucide-react';
import { getMentorPrompts } from '../services/api';
import { useMentor } from '../context/MentorContext';
import { useProfile } from '../context/ProfileContext';

const FALLBACK_PROMPTS = {
  after_10th: ['Compare Diploma CS vs 11th Science', 'What can I do after a polytechnic diploma?'],
  after_12th: ['JEE Main vs MHT-CET: which should I focus on?', 'What are the options after 12th Commerce?'],
  after_diploma: ['How does DSE admission work?', 'SSC JE vs RRB JE: which is better for me?'],
};

/** Minimal safe renderer: **bold** and "- " bullets. No HTML injection. */
function RichText({ text }) {
  return (
    <div className="space-y-1.5">
      {text.split('\n').map((line, i) => {
        if (!line.trim()) return null;
        const bullet = /^\s*[-*]\s+/.test(line);
        const body = line.replace(/^\s*[-*]\s+/, '');
        const parts = body.split(/(\*\*[^*]+\*\*)/g).map((p, j) =>
          p.startsWith('**') && p.endsWith('**') ? <strong key={j}>{p.slice(2, -2)}</strong> : <span key={j}>{p}</span>
        );
        return bullet ? (
          <div key={i} className="flex gap-2"><span className="text-indigo-400">&bull;</span><span>{parts}</span></div>
        ) : (
          <p key={i}>{parts}</p>
        );
      })}
    </div>
  );
}

export default function MentorChat({ compact = false }) {
  const { messages, loading, send, draft, setDraft, clear } = useMentor();
  const { profile } = useProfile();
  const [prompts, setPrompts] = useState([]);
  const endRef = useRef(null);
  const stage = profile?.stage || 'after_10th';

  useEffect(() => {
    getMentorPrompts(stage).then((r) => setPrompts(r.prompts)).catch(() => setPrompts(FALLBACK_PROMPTS[stage]));
  }, [stage]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, loading]);

  const submit = (e) => {
    e?.preventDefault();
    const text = draft;
    setDraft('');
    send(text);
  };

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex-1 overflow-y-auto space-y-4 p-4" aria-live="polite">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-8 h-8 rounded-xl shrink-0 flex items-center justify-center ${m.role === 'user' ? 'bg-orange-500' : 'bg-indigo-600'}`}>
              {m.role === 'user' ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-white" />}
            </div>
            <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
              m.role === 'user' ? 'bg-indigo-600 text-white' : m.error ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-slate-100 text-slate-800'
            }`}>
              {m.role === 'user' ? m.content : <RichText text={m.content} />}
              {m.sources?.length > 0 && (
                <p className="mt-2 text-[11px] text-slate-500 font-semibold">Sources: {m.sources.join(', ')}</p>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-xs text-slate-400 font-semibold pl-11">
            <Loader2 className="w-4 h-4 animate-spin" /> Thinking...
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="px-4 pt-2">
        <div className="flex gap-2 overflow-x-auto pb-2">
          {prompts.slice(0, compact ? 3 : 4).map((p) => (
            <button key={p} onClick={() => send(p)} disabled={loading}
              className="shrink-0 px-3 py-1.5 rounded-full bg-indigo-50 text-indigo-700 text-xs font-bold hover:bg-indigo-100 disabled:opacity-50">
              {p}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={submit} className="p-4 pt-1 flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          maxLength={2000}
          placeholder="Ask about exams, colleges, paths..."
          aria-label="Message the AI Mentor"
          className="flex-1 px-4 py-3 rounded-2xl border border-slate-200 focus:border-indigo-400 focus:outline-none text-sm"
        />
        <button type="submit" disabled={loading || !draft.trim()} aria-label="Send"
          className="w-11 h-11 rounded-2xl bg-indigo-600 text-white flex items-center justify-center disabled:opacity-40">
          <Send className="w-4 h-4" />
        </button>
        {!compact && (
          <button type="button" onClick={clear} aria-label="Clear chat" className="w-11 h-11 rounded-2xl bg-slate-100 text-slate-500 flex items-center justify-center">
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </form>
    </div>
  );
}
