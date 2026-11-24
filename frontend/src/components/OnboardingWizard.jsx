import React, { useEffect, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, Loader2, Sparkles, X } from 'lucide-react';
import { getGuidance, getQuiz } from '../services/api';
import { GOAL_SUGGESTIONS, QUIZ_FALLBACK } from '../data/quizFallback';
import { useProfile } from '../context/ProfileContext';

const STEPS = ['Education stage', 'Stream', 'Interests', 'Strengths', 'Career goal'];

function Chip({ active, onClick, children, hint }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={hint}
      className={`px-4 py-2.5 rounded-2xl text-sm font-semibold border transition-all text-left ${
        active
          ? 'bg-indigo-600 text-white border-indigo-600 shadow-lg shadow-indigo-500/30'
          : 'bg-white text-slate-700 border-slate-200 hover:border-indigo-300'
      }`}
    >
      {children}
    </button>
  );
}

export default function OnboardingWizard({ onClose, dismissible }) {
  const { name, profile, patch } = useProfile();
  const [quiz, setQuiz] = useState(QUIZ_FALLBACK);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({
    stage: profile?.stage || '',
    stream: profile?.stream || '',
    interests: profile?.interests || [],
    strengths: profile?.strengths || [],
    career_goal: profile?.career_goal || '',
  });
  const [saving, setSaving] = useState(false);
  const [warn, setWarn] = useState('');

  useEffect(() => {
    getQuiz().then(setQuiz).catch(() => setQuiz(QUIZ_FALLBACK));
  }, []);

  const set = (k, v) => setAnswers((a) => ({ ...a, [k]: v }));
  const toggleIn = (k, id, max) =>
    setAnswers((a) => {
      const has = a[k].includes(id);
      if (!has && max && a[k].length >= max) return a;
      return { ...a, [k]: has ? a[k].filter((x) => x !== id) : [...a[k], id] };
    });

  const canNext = [
    !!answers.stage,
    !!answers.stream,
    answers.interests.length >= 1,
    answers.strengths.length >= 1,
    answers.career_goal.trim().length >= 2,
  ][step];

  const finish = async () => {
    setSaving(true);
    setWarn('');
    const saved = { ...answers, career_goal: answers.career_goal.trim() };
    let guidance = null;
    try {
      guidance = await getGuidance({ ...saved, name });
    } catch {
      setWarn('Saved your profile. Personalised recommendations will load when the server is reachable.');
    }
    patch({ profile: saved, guidance });
    setSaving(false);
    if (guidance) onClose();
  };

  const streams = quiz.streams[answers.stage] || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 bg-slate-950/70 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Onboarding">
      <div className="relative w-full max-w-2xl bg-white rounded-[28px] shadow-2xl overflow-hidden animate-scale-in max-h-[94vh] flex flex-col">
        <div className="px-6 pt-6 pb-4 border-b border-slate-100">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-xs font-bold text-indigo-600 uppercase tracking-wider">
              <Sparkles className="w-4 h-4" /> Personalise your dashboard
            </div>
            {dismissible && (
              <button onClick={onClose} aria-label="Close" className="w-8 h-8 rounded-lg bg-slate-100 hover:bg-slate-200 flex items-center justify-center">
                <X className="w-4 h-4 text-slate-500" />
              </button>
            )}
          </div>
          <div className="flex gap-1.5">
            {STEPS.map((s, i) => (
              <div key={s} className={`h-1.5 flex-1 rounded-full ${i <= step ? 'bg-indigo-600' : 'bg-slate-200'}`} />
            ))}
          </div>
          <p className="text-xs text-slate-400 font-semibold mt-2">Step {step + 1} of {STEPS.length}: {STEPS[step]}</p>
        </div>

        <div className="p-6 overflow-y-auto flex-1">
          {step === 0 && (
            <>
              <h3 className="text-xl font-black text-slate-900 mb-4">Where are you right now?</h3>
              <div className="grid gap-2.5">
                {quiz.stages.map((s) => (
                  <Chip key={s.id} active={answers.stage === s.id} onClick={() => setAnswers({ ...answers, stage: s.id, stream: '' })}>
                    {s.label}
                  </Chip>
                ))}
              </div>
            </>
          )}
          {step === 1 && (
            <>
              <h3 className="text-xl font-black text-slate-900 mb-1">
                {answers.stage === 'after_diploma' ? 'Which diploma branch?' : answers.stage === 'after_10th' ? 'Which path interests you most?' : 'Which stream are you from?'}
              </h3>
              <p className="text-sm text-slate-500 mb-4">You can change this later.</p>
              <div className="flex flex-wrap gap-2.5">
                {streams.map((s) => (
                  <Chip key={s.id} active={answers.stream === s.id} onClick={() => set('stream', s.id)}>{s.label}</Chip>
                ))}
              </div>
            </>
          )}
          {step === 2 && (
            <>
              <h3 className="text-xl font-black text-slate-900 mb-1">What kind of work excites you?</h3>
              <p className="text-sm text-slate-500 mb-4">Pick up to 3. Based on the RIASEC interest model.</p>
              <div className="grid sm:grid-cols-2 gap-2.5">
                {quiz.interests.map((i) => (
                  <Chip key={i.id} active={answers.interests.includes(i.id)} onClick={() => toggleIn('interests', i.id, 3)}>
                    <div>{i.label}</div>
                    <div className={`text-xs font-medium ${answers.interests.includes(i.id) ? 'text-indigo-100' : 'text-slate-400'}`}>{i.hint}</div>
                  </Chip>
                ))}
              </div>
            </>
          )}
          {step === 3 && (
            <>
              <h3 className="text-xl font-black text-slate-900 mb-1">What are you good at?</h3>
              <p className="text-sm text-slate-500 mb-4">Pick up to 5.</p>
              <div className="flex flex-wrap gap-2.5">
                {quiz.strengths.map((s) => (
                  <Chip key={s.id} active={answers.strengths.includes(s.id)} onClick={() => toggleIn('strengths', s.id, 5)}>{s.label}</Chip>
                ))}
              </div>
            </>
          )}
          {step === 4 && (
            <>
              <h3 className="text-xl font-black text-slate-900 mb-1">What is your career goal?</h3>
              <p className="text-sm text-slate-500 mb-4">A job title or dream is fine. It can be rough.</p>
              <input
                value={answers.career_goal}
                onChange={(e) => set('career_goal', e.target.value)}
                maxLength={200}
                placeholder="e.g. Full stack developer"
                className="w-full px-4 py-3.5 rounded-2xl border border-slate-200 focus:border-indigo-400 focus:outline-none text-sm font-medium"
              />
              <div className="flex flex-wrap gap-2 mt-3">
                {(GOAL_SUGGESTIONS[answers.stage] || []).map((g) => (
                  <button key={g} type="button" onClick={() => set('career_goal', g)} className="px-3 py-1.5 rounded-full bg-indigo-50 text-indigo-700 text-xs font-bold hover:bg-indigo-100">
                    {g}
                  </button>
                ))}
              </div>
              {warn && <p className="mt-4 text-xs font-semibold text-amber-600 bg-amber-50 border border-amber-200 rounded-xl p-3">{warn}</p>}
            </>
          )}
        </div>

        <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between">
          <button
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
            className="flex items-center gap-1.5 text-sm font-bold text-slate-500 disabled:opacity-30"
          >
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          {warn ? (
            <button onClick={onClose} className="px-6 py-3 rounded-2xl text-sm font-bold text-white bg-indigo-600">Continue</button>
          ) : step < STEPS.length - 1 ? (
            <button
              onClick={() => setStep((s) => s + 1)}
              disabled={!canNext}
              className="flex items-center gap-2 px-6 py-3 rounded-2xl text-sm font-bold text-white bg-indigo-600 disabled:opacity-40 hover:bg-indigo-700"
            >
              Next <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={finish}
              disabled={!canNext || saving}
              className="flex items-center gap-2 px-6 py-3 rounded-2xl text-sm font-bold text-white disabled:opacity-40"
              style={{ background: 'linear-gradient(135deg, #f97316, #ef4444)' }}
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              {saving ? 'Building your dashboard...' : 'Build my dashboard'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
