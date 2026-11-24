import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

const KEY = 'cf_state_v1';

export const STAGE_LABELS = {
  after_10th: 'Class 10 student',
  after_12th: 'Class 12 student',
  after_diploma: 'Diploma student',
};

const EMPTY = {
  name: '',
  profile: null,      // {stage, stream, interests, strengths, career_goal}
  guidance: null,     // last /guidance/recommend payload
  resume: null,       // {score, role, at}
  checklist: {},      // learning checklist id -> true
  roadmapDone: {},    // roadmap node id -> true
};

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? { ...EMPTY, ...JSON.parse(raw) } : EMPTY;
  } catch {
    return EMPTY;
  }
}

const Ctx = createContext(null);

export function ProfileProvider({ children }) {
  const [state, setState] = useState(load);

  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
    } catch {
      /* storage full or blocked: keep working in memory */
    }
  }, [state]);

  const patch = useCallback((p) => setState((s) => ({ ...s, ...p })), []);
  const toggle = useCallback(
    (field, id) => setState((s) => ({ ...s, [field]: { ...s[field], [id]: !s[field][id] } })),
    []
  );
  const reset = useCallback(() => setState(EMPTY), []);

  const value = useMemo(() => ({ ...state, patch, toggle, reset }), [state, patch, toggle, reset]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useProfile = () => {
  const v = useContext(Ctx);
  if (!v) throw new Error('useProfile must be used inside ProfileProvider');
  return v;
};
