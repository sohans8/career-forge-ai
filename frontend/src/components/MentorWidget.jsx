import React from 'react';
import { Bot, X } from 'lucide-react';
import MentorChat from './MentorChat';
import { useMentor } from '../context/MentorContext';

export default function MentorWidget({ hidden }) {
  const { widgetOpen, setWidgetOpen } = useMentor();
  if (hidden) return null;
  return (
    <>
      {widgetOpen && (
        <div className="fixed z-40 bottom-24 right-4 w-[min(92vw,380px)] h-[min(70vh,560px)] bg-white rounded-3xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-scale-in"
          role="dialog" aria-label="AI Mentor">
          <div className="px-4 py-3 flex items-center justify-between text-white" style={{ background: 'linear-gradient(135deg, #4f46e5, #7c3aed)' }}>
            <div className="flex items-center gap-2 font-bold text-sm"><Bot className="w-5 h-5" /> AI Mentor</div>
            <button onClick={() => setWidgetOpen(false)} aria-label="Close mentor" className="w-7 h-7 rounded-lg bg-white/15 hover:bg-white/25 flex items-center justify-center">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 min-h-0"><MentorChat compact /></div>
        </div>
      )}
      <button
        onClick={() => setWidgetOpen(!widgetOpen)}
        aria-label={widgetOpen ? 'Close AI Mentor' : 'Open AI Mentor'}
        className="fixed z-40 bottom-5 right-5 w-14 h-14 rounded-full text-white flex items-center justify-center shadow-xl hover:scale-105 transition-transform"
        style={{ background: 'linear-gradient(135deg, #f97316, #ef4444)', boxShadow: '0 8px 24px rgba(249,115,22,0.45)' }}
      >
        {widgetOpen ? <X className="w-6 h-6" /> : <Bot className="w-6 h-6" />}
      </button>
    </>
  );
}
