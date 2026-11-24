import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, CheckCircle2, ExternalLink, FileText, Loader2, UploadCloud } from 'lucide-react';
import { analyzeResume, getResumeRoles } from '../services/api';
import { useProfile } from '../context/ProfileContext';

const FALLBACK_ROLES = ['Software Developer', 'Full Stack Developer', 'AI/ML Engineer', 'Data Scientist', 'Data Analyst',
  'Mechanical Engineer', 'Civil Engineer', 'Electrical Engineer', 'Electronics Engineer', 'Finance / Accounting', 'Diploma Engineer (Fresher)'];
const MAX_MB = 5;

export function ScoreGauge({ score, size = 160 }) {
  const r = 54;
  const c = 2 * Math.PI * r;
  const color = score >= 75 ? '#10b981' : score >= 55 ? '#f59e0b' : '#ef4444';
  return (
    <div className="relative" style={{ width: size, height: size }} role="img" aria-label={`ATS score ${score} out of 100`}>
      <svg viewBox="0 0 120 120" className="-rotate-90 w-full h-full">
        <circle cx="60" cy="60" r={r} fill="none" stroke="#e2e8f0" strokeWidth="10" />
        <circle cx="60" cy="60" r={r} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c - (c * score) / 100} style={{ transition: 'stroke-dashoffset 1s ease' }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-black text-slate-900">{score}</span>
        <span className="text-[11px] font-bold text-slate-400 uppercase">ATS score</span>
      </div>
    </div>
  );
}

function Bar({ label, value }) {
  const color = value >= 70 ? 'bg-emerald-500' : value >= 45 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div>
      <div className="flex justify-between text-xs font-bold text-slate-600 mb-1"><span>{label}</span><span>{value}</span></div>
      <div className="h-2 rounded-full bg-slate-100"><div className={`h-2 rounded-full ${color}`} style={{ width: `${value}%`, transition: 'width 1s' }} /></div>
    </div>
  );
}

export default function ResumePage() {
  const { guidance, resume, patch, checklist, toggle } = useProfile();
  const [roles, setRoles] = useState(FALLBACK_ROLES);
  const [role, setRole] = useState(guidance?.suggested_resume_role || resume?.role || 'Software Developer');
  const [file, setFile] = useState(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const input = useRef(null);

  useEffect(() => { getResumeRoles().then((r) => setRoles(r.roles)).catch(() => {}); }, []);

  const pick = useCallback((f) => {
    setError('');
    if (!f) return;
    if (!/\.(pdf|docx)$/i.test(f.name)) return setError('Please upload a PDF or DOCX file.');
    if (f.size > MAX_MB * 1024 * 1024) return setError(`File is larger than ${MAX_MB} MB.`);
    setFile(f);
  }, []);

  const run = async () => {
    if (!file) return;
    setBusy(true);
    setError('');
    try {
      const res = await analyzeResume(file, role);
      setResult(res);
      patch({ resume: { score: res.ats_score, role: res.target_role, at: new Date().toISOString() } });
    } catch (e) {
      setError(e.response?.data?.detail || 'Analysis failed. The server may be waking up. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  const key = (id) => `${result?.target_role}:${id}`;
  const done = result ? result.learning_checklist.filter((i) => checklist[key(i.id)]).length : 0;

  return (
    <div className="pt-4 space-y-6">
      <div className="grid lg:grid-cols-[1fr_320px] gap-4">
        <div
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]); }}
          onClick={() => input.current?.click()}
          onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && input.current?.click()}
          role="button" tabIndex={0} aria-label="Upload resume"
          className={`cursor-pointer rounded-3xl border-2 border-dashed p-8 text-center transition-all ${drag ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 bg-slate-50 hover:border-indigo-300'}`}
        >
          <input ref={input} type="file" accept=".pdf,.docx" className="hidden" onChange={(e) => pick(e.target.files?.[0])} />
          {file ? (
            <div className="flex flex-col items-center gap-2"><FileText className="w-10 h-10 text-indigo-500" /><p className="font-bold text-slate-800">{file.name}</p><p className="text-xs text-slate-400">{(file.size / 1024).toFixed(0)} KB · click to replace</p></div>
          ) : (
            <div className="flex flex-col items-center gap-2"><UploadCloud className="w-10 h-10 text-indigo-400" /><p className="font-bold text-slate-800">Drag and drop your resume here</p><p className="text-xs text-slate-400">PDF or DOCX, up to {MAX_MB} MB. Use a text-based file, not a scan.</p></div>
          )}
        </div>
        <div className="rounded-3xl border border-slate-200 p-5 space-y-4 bg-white">
          <label className="block text-xs font-black text-slate-400 uppercase tracking-wider" htmlFor="role">Target role</label>
          <select id="role" value={role} onChange={(e) => setRole(e.target.value)} className="w-full border border-slate-200 rounded-xl px-3 py-3 text-sm font-semibold">
            {roles.map((r) => <option key={r}>{r}</option>)}
          </select>
          <button onClick={run} disabled={!file || busy}
            className="w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl text-sm font-bold text-white disabled:opacity-40"
            style={{ background: 'linear-gradient(135deg, #4f46e5, #7c3aed)' }}>
            {busy && <Loader2 className="w-4 h-4 animate-spin" />}{busy ? 'Analysing...' : 'Analyse my resume'}
          </button>
          {error && <p role="alert" className="flex gap-2 text-xs font-semibold text-red-600 bg-red-50 border border-red-200 rounded-xl p-3"><AlertCircle className="w-4 h-4 shrink-0" />{error}</p>}
          <p className="text-[11px] text-slate-400">Your file is analysed in memory and not stored.</p>
        </div>
      </div>

      {result && (
        <div className="space-y-6">
          <div className="grid md:grid-cols-[200px_1fr] gap-6 items-center rounded-3xl border border-slate-200 p-6 bg-white">
            <div className="flex justify-center"><ScoreGauge score={result.ats_score} /></div>
            <div className="space-y-3">
              <p className="text-sm text-slate-600 font-medium">{result.summary}</p>
              <div className="grid sm:grid-cols-2 gap-3">
                <Bar label="Keywords" value={result.breakdown.keywords} />
                <Bar label="Impact" value={result.breakdown.impact} />
                <Bar label="Formatting" value={result.breakdown.formatting} />
                <Bar label="Completeness" value={result.breakdown.completeness} />
              </div>
              <p className="text-[11px] text-slate-400">{result.llm_used ? 'Rewrites enhanced by AI.' : 'Rule-based analysis. Add an LLM API key on the server for AI-written rewrites.'}</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="rounded-3xl border border-emerald-200 bg-emerald-50/50 p-5">
              <h4 className="font-black text-emerald-800 mb-3">Matched skills ({result.matched_skills.length})</h4>
              <div className="flex flex-wrap gap-2">{result.matched_skills.length ? result.matched_skills.map((s) => <span key={s} className="px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold">{s}</span>) : <span className="text-xs text-slate-400">None found</span>}</div>
            </div>
            <div className="rounded-3xl border border-red-200 bg-red-50/50 p-5">
              <h4 className="font-black text-red-800 mb-3">Missing skills ({result.missing_skills.length})</h4>
              <div className="flex flex-wrap gap-2">{result.missing_skills.length ? result.missing_skills.map((s) => <span key={s} className="px-3 py-1 rounded-full bg-red-100 text-red-800 text-xs font-bold">{s}</span>) : <span className="text-xs text-slate-400">No gaps found</span>}</div>
            </div>
          </div>

          <div className="space-y-4">
            <h4 className="font-black text-slate-900 text-lg">Section feedback</h4>
            {result.section_feedback.map((s) => (
              <div key={s.section} className="rounded-3xl border border-slate-200 p-5 bg-white">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`w-2.5 h-2.5 rounded-full ${s.status === 'good' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                  <h5 className="font-bold text-slate-800">{s.section}</h5>
                </div>
                <ul className="list-disc pl-5 text-sm text-slate-600 space-y-1">{s.feedback.map((f) => <li key={f}>{f}</li>)}</ul>
                {s.rewrites.length > 0 && (
                  <div className="mt-4 space-y-3">
                    {s.rewrites.map((r, i) => (
                      <div key={i} className="grid md:grid-cols-2 gap-3 text-sm">
                        <div className="rounded-2xl bg-red-50 border border-red-100 p-3"><p className="text-[10px] font-black text-red-500 uppercase mb-1">Before</p>{r.before}</div>
                        <div className="rounded-2xl bg-emerald-50 border border-emerald-100 p-3"><p className="text-[10px] font-black text-emerald-600 uppercase mb-1">After</p>{r.after}</div>
                      </div>
                    ))}
                    <p className="text-[11px] text-slate-400">Replace bracketed placeholders with your real numbers. Do not invent results.</p>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="rounded-3xl border border-indigo-200 bg-indigo-50/40 p-5">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-black text-slate-900 text-lg">Learning &amp; project roadmap</h4>
              <span className="text-xs font-bold text-indigo-700">{done}/{result.learning_checklist.length} done</span>
            </div>
            <div className="h-2 rounded-full bg-white mb-4"><div className="h-2 rounded-full bg-indigo-600" style={{ width: `${result.learning_checklist.length ? (done / result.learning_checklist.length) * 100 : 0}%`, transition: 'width .5s' }} /></div>
            <div className="space-y-3">
              {result.learning_checklist.map((item) => {
                const checked = !!checklist[key(item.id)];
                return (
                  <div key={item.id} className={`rounded-2xl bg-white border p-4 ${checked ? 'border-emerald-300 opacity-70' : 'border-slate-200'}`}>
                    <label className="flex items-start gap-3 cursor-pointer">
                      <input type="checkbox" checked={checked} onChange={() => toggle('checklist', key(item.id))} className="mt-1 w-4 h-4 accent-indigo-600" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`font-bold text-slate-900 ${checked ? 'line-through' : ''}`}>Learn {item.skill}</span>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-black uppercase ${item.priority === 'high' ? 'bg-red-100 text-red-700' : item.priority === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'}`}>{item.priority}</span>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">{item.why} {item.learn}</p>
                        <p className="text-xs text-slate-700 mt-2"><strong>Mini-project:</strong> {item.mini_project}</p>
                      </div>
                    </label>
                    <div className="flex flex-wrap gap-2 mt-3 pl-7">
                      {item.resources.map((res) => (
                        <a key={res.url} href={res.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-indigo-100 text-[11px] font-bold text-slate-700">
                          <ExternalLink className="w-3 h-3" />{res.title} <span className="text-slate-400">({res.cost})</span>
                        </a>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
            {done === result.learning_checklist.length && result.learning_checklist.length > 0 && (
              <p className="mt-4 flex items-center gap-2 text-sm font-bold text-emerald-700"><CheckCircle2 className="w-4 h-4" /> Checklist complete. Update your resume and upload it again to see your new score.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
