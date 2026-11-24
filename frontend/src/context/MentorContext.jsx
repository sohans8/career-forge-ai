import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import { sendMentorMessage } from '../services/api';
import { useProfile } from './ProfileContext';

const Ctx = createContext(null);

const WELCOME = {
  role: 'assistant',
  content: "Hi! I'm your Career Forge AI Mentor. Ask me about diplomas, DSE, entrance exams, colleges or your career path.",
};

export function MentorProvider({ children }) {
  const { name, profile } = useProfile();
  const [messages, setMessages] = useState([WELCOME]);
  const [loading, setLoading] = useState(false);
  const [widgetOpen, setWidgetOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const busy = useRef(false);
  const pendingNode = useRef(null); // roadmap node the next question is about

  const send = useCallback(
    async (text, explicitNode = null) => {
      const message = text.trim();
      if (!message || busy.current) return;
      busy.current = true;
      const nodeId = explicitNode || pendingNode.current;
      pendingNode.current = null;
      const history = messages.filter((m) => m !== WELCOME && !m.error).map(({ role, content }) => ({ role, content }));
      setMessages((m) => [...m, { role: 'user', content: message }]);
      setLoading(true);
      try {
        const res = await sendMentorMessage({
          message,
          history,
          node_id: nodeId,
          profile: {
            stage: profile?.stage || null,
            stream: profile?.stream || null,
            target_goal: profile?.career_goal || null,
            name: name || null,
          },
        });
        setMessages((m) => [...m, { role: 'assistant', content: res.reply, sources: res.sources, llm: res.llm_used }]);
      } catch {
        setMessages((m) => [
          ...m,
          { role: 'assistant', error: true, content: 'I could not reach the server. If it was idle, wait a few seconds and try again.' },
        ]);
      } finally {
        busy.current = false;
        setLoading(false);
      }
    },
    [messages, profile, name]
  );

  /** Open the floating widget with a question prepared for a roadmap node. */
  const askAboutNode = useCallback((node) => {
    setDraft(`Tell me about "${node.title}": eligibility, exams, colleges and whether it suits my profile.`);
    pendingNode.current = node.id;
    setWidgetOpen(true);
  }, []);

  const value = useMemo(
    () => ({ messages, loading, send, widgetOpen, setWidgetOpen, draft, setDraft, askAboutNode, clear: () => setMessages([WELCOME]) }),
    [messages, loading, send, widgetOpen, draft, askAboutNode]
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useMentor = () => {
  const v = useContext(Ctx);
  if (!v) throw new Error('useMentor must be used inside MentorProvider');
  return v;
};
