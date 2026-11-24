import React, { useEffect, useState } from 'react';
import { ArrowRight, Bot, FileText, Map, Sparkles } from 'lucide-react';
import { ScoreGauge } from './ResumePage';
import { STAGE_LABELS, useProfile } from '../context/ProfileContext';
import { useMentor } from '../context/MentorContext';
import { getGuidance } from '../services/api';

function Card({ title, icon: Icon, children, action, onAction }) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="flex items-center gap-2 font-black text-slate-900"><Icon className="w-4 h-4 text-indigo-500" />{title}</h3>
        {action && <button onClick={onAction} className="flex items-center gap-1 text-xs font-bold text-indigo-600 hover:underline">{action}<ArrowRight className="w-3 h-3" /></button>}
      </div>
      {children}
    </section>
  );
}

export default function StudentDashboard({ go, openWizard }) {
  const { name, profile, guidance, resume, roadmapDone, checklist, patch } = useProfile();
  const { setWidgetOpen } = useMentor();
  const [retrying, setRetrying] = useState(false);

  // Retry recommendations if the profile was saved while the server was unreachable.
  useEffect(() => {
    if (profile && !guidance && !retrying) {
      setRetrying(true);
      getGuidance({ ...profile, name }).then((g) => patch({ guidance: g })).catch(() => {}).finally(() => setRetrying(false));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile, guidance]);

  if (!profile) {
    return (
      <div className="pt-10 text-center">
        <Sparkles className="w-10 h-10 text-indigo-400 mx-auto mb-3" />
        <h3 className="text-xl font-black text-slate-900">Let's personalise your dashboard</h3>
        <p className="text-sm text-slate-500 mt-1 mb-5">Answer 5 quick questions to get a roadmap, careers and next steps.</p>
        <button onClick={openWizard} className="px-6 py-3 rounded-2xl text-sm font-bold text-white bg-indigo-600">Start the quiz</button>
      </div>
    );
  }

  const g = guidance;
  const doneNodes = Object.values(roadmapDone).filter(Boolean).length;
  const doneTasks = Object.values(checklist).filter(Boolean).length;

  return (
    <div className="pt-4 space-y-4">
      <div className="rounded-3xl p-6 text-white flex flex-wrap items-center justify-between gap-4" style={{ background: 'linear-gradient(135deg, #4f46e5, #7c3aed)' }}>
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-indigo-200">{STAGE_LABELS[profile.stage]}{profile.stream ? ` · ${profile.stream.replace(/_/g, ' ')}` : ''}</p>
          <h3 className="text-2xl font-black mt-1">Goal: {profile.career_goal}</h3>
          <p className="text-sm text-indigo-100 mt-1">{doneNodes} roadmap {doneNodes === 1 ? 'step' : 'steps'} explored · {doneTasks} learning {doneTasks === 1 ? 'task' : 'tasks'} done</p>
        </div>
        <button onClick={openWizard} className="px-4 py-2 rounded-xl bg-white/15 hover:bg-white/25 text-xs font-bold">Edit profile</button>
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        <Card title="Your roadmap" icon={Map} action="Open explorer" onAction={() => go('roadmap')}>
          {g?.recommended_roadmap.paths.length ? (
            <ul className="space-y-2">
              {g.recommended_roadmap.paths.map((p) => (
                <li key={p.id} className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <p className="text-sm font-bold text-slate-800">{roadmapDone[p.id] ? '✓ ' : ''}{p.title}</p>
                  <p className="text-xs text-slate-500">
                    {[p.duration && p.duration !== '-' ? p.duration : null, p.entrance_exams.slice(0, 2).join(', ') || null].filter(Boolean).join(' · ')}
                  </p>
                </li>
              ))}
            </ul>
          ) : <p className="text-sm text-slate-400">{retrying ? 'Loading recommendations...' : 'Open the explorer to browse paths.'}</p>}
        </Card>

        <Card title="AI Mentor" icon={Bot} action="Open chat" onAction={() => go('mentor')}>
          <p className="text-sm text-slate-600 mb-3">Ask anything about your path. Answers use your stage, stream and goal.</p>
          <button onClick={() => setWidgetOpen(true)} className="mt-auto py-2.5 rounded-xl bg-orange-50 text-orange-700 text-sm font-bold hover:bg-orange-100">Quick question</button>
        </Card>

        <Card title="Resume score" icon={FileText} action="Resume Studio" onAction={() => go('resume')}>
          {resume ? (
            <div className="flex items-center gap-4"><ScoreGauge score={resume.score} size={110} /><p className="text-xs text-slate-500">For {resume.role}<br />{new Date(resume.at).toLocaleDateString()}</p></div>
          ) : (
            <p className="text-sm text-slate-500">Upload your resume to get an ATS score{g?.suggested_resume_role ? ` for ${g.suggested_resume_role}` : ''} and a learning plan.</p>
          )}
        </Card>
      </div>

      {g && (
        <div className="grid lg:grid-cols-2 gap-4">
          <Card title="Top matching careers" icon={Sparkles}>
            <ul className="space-y-2.5">
              {g.top_careers.slice(0, 5).map((c) => (
                <li key={c.soc}>
                  <div className="flex justify-between text-sm font-bold text-slate-800"><span>{c.title}</span><span className="text-indigo-600">{c.match}%</span></div>
                  <div className="h-1.5 rounded-full bg-slate-100 mt-1"><div className="h-1.5 rounded-full bg-indigo-500" style={{ width: `${c.match}%` }} /></div>
                </li>
              ))}
            </ul>
            <p className="text-[11px] text-slate-400 mt-3">Matched using RIASEC interest codes from O*NET.</p>
          </Card>
          <div className="space-y-4">
            <Card title="Skills to build" icon={Sparkles}>
              <div className="flex flex-wrap gap-2">
                {g.skill_gap_summary.skills_to_build.map((s) => <span key={s} className="px-3 py-1 rounded-full bg-amber-50 text-amber-800 text-xs font-bold">{s}</span>)}
              </div>
            </Card>
            <Card title="Next actions" icon={ArrowRight}>
              <ol className="list-decimal pl-5 space-y-1.5 text-sm text-slate-700">{g.next_actions.map((a) => <li key={a}>{a}</li>)}</ol>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
