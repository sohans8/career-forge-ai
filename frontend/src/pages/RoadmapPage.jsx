import React, { useCallback, useEffect, useMemo, useState } from 'react';
import ReactFlow, { Background, Controls, MarkerType } from 'reactflow';
import 'reactflow/dist/style.css';
import { Bot, CheckCircle2, ExternalLink, Loader2, MapPin, X } from 'lucide-react';
import { getRoadmap, getStates, searchColleges } from '../services/api';
import { QUIZ_FALLBACK } from '../data/quizFallback';
import { useProfile } from '../context/ProfileContext';
import { useMentor } from '../context/MentorContext';

const TABS = [
  { id: 'after_10th', label: 'After 10th (with Diploma)' },
  { id: 'after_12th', label: 'After 12th' },
  { id: 'after_diploma', label: 'After Diploma (DSE & Jobs)' },
];

const STAGE_BY_PREFIX = { a10: 'after_10th', a12: 'after_12th', ad: 'after_diploma' };

const LEVEL_X = 300;
const ROW_Y = 92;

/** Layered left-to-right layout from the stage root. */
function layout(graph, done, selectedId) {
  const { nodes, edges, root } = graph;
  const level = { [root]: 0 };
  const queue = [root];
  while (queue.length) {
    const cur = queue.shift();
    edges.filter((e) => e.source === cur).forEach((e) => {
      if (level[e.target] === undefined) { level[e.target] = level[cur] + 1; queue.push(e.target); }
    });
  }
  const cols = {};
  nodes.forEach((n) => {
    const l = level[n.id] ?? 1;
    (cols[l] = cols[l] || []).push(n);
  });
  const rfNodes = [];
  Object.entries(cols).forEach(([l, list]) => {
    const offset = (-(list.length - 1) * ROW_Y) / 2;
    list.forEach((n, i) => {
      const isRoot = n.kind === 'root';
      const isDone = done[n.id];
      rfNodes.push({
        id: n.id,
        position: { x: Number(l) * LEVEL_X, y: offset + i * ROW_Y },
        data: { label: (isDone ? '✓ ' : '') + n.title, raw: n },
        style: {
          width: 240, padding: 10, borderRadius: 16, fontSize: 12, fontWeight: 700, textAlign: 'center',
          background: isRoot ? 'linear-gradient(135deg,#4f46e5,#7c3aed)' : n.external ? '#f8fafc' : isDone ? '#ecfdf5' : '#fff',
          color: isRoot ? '#fff' : '#1e293b',
          border: selectedId === n.id ? '2px solid #f97316' : n.external ? '1.5px dashed #94a3b8' : '1.5px solid #c7d2fe',
          boxShadow: '0 4px 14px rgba(15,23,42,0.08)', cursor: 'pointer',
        },
      });
    });
  });
  const rfEdges = edges.map((e) => ({
    ...e, type: 'smoothstep', animated: !e.external,
    style: { stroke: e.external ? '#94a3b8' : '#818cf8', strokeWidth: 1.5, strokeDasharray: e.external ? '5 4' : undefined },
    markerEnd: { type: MarkerType.ArrowClosed, color: e.external ? '#94a3b8' : '#818cf8' },
  }));
  return { rfNodes, rfEdges };
}

function Row({ label, children }) {
  return (
    <div>
      <p className="text-[11px] font-black text-slate-400 uppercase tracking-wider mb-1">{label}</p>
      <div className="text-sm text-slate-700 font-medium">{children}</div>
    </div>
  );
}

const TONES = { indigo: 'bg-indigo-50 text-indigo-700', emerald: 'bg-emerald-50 text-emerald-700' };

function Pills({ items, tone = 'indigo' }) {
  if (!items?.length) return <span className="text-slate-400">None</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((i) => (
        <span key={i} className={`px-2.5 py-1 rounded-full text-xs font-bold ${TONES[tone]}`}>{i}</span>
      ))}
    </div>
  );
}

function Colleges({ node }) {
  const { profile } = useProfile();
  const [states, setStates] = useState([]);
  const [state, setState] = useState('Maharashtra');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { getStates().then((r) => setStates(r.states)).catch(() => setStates(['Maharashtra'])); }, []);
  useEffect(() => {
    let live = true;
    setLoading(true);
    const params = { state, type: node.college_type, limit: 5 };
    if (node.college_type === 'diploma' && node.branch_keywords?.length) params.branch = node.branch_keywords[0];
    searchColleges(params).then((r) => live && setData(r)).catch(() => live && setData({ results: [], total: 0 })).finally(() => live && setLoading(false));
    return () => { live = false; };
  }, [node.id, node.college_type, node.branch_keywords, state]);

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-[11px] font-black text-slate-400 uppercase tracking-wider">Matching colleges</p>
        <select value={state} onChange={(e) => setState(e.target.value)} aria-label="State" className="text-xs font-bold border border-slate-200 rounded-lg px-2 py-1">
          {states.map((s) => <option key={s}>{s}</option>)}
        </select>
      </div>
      {loading ? <Loader2 className="w-4 h-4 animate-spin text-indigo-500" /> : (
        <>
          <ul className="space-y-2">
            {data?.results.map((c) => (
              <li key={c.id} className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                <p className="text-sm font-bold text-slate-800">{c.name}</p>
                <p className="text-xs text-slate-500 flex items-center gap-1"><MapPin className="w-3 h-3" />{c.district}, {c.state} · {c.ownership}</p>
              </li>
            ))}
          </ul>
          {data && <p className="text-[11px] text-slate-400 mt-2">{data.total} AICTE-listed institutions match. Confirm approval status on aicte-india.org.</p>}
          {data?.results.length === 0 && <p className="text-xs text-slate-400">No institutions found for this filter.</p>}
        </>
      )}
    </div>
  );
}

const prettyId = (id) => id.replace(/^[a-z]+\d*_/, '').replace(/_/g, ' ');

function Drawer({ node, onClose, onSelect, titleOf }) {
  const { roadmapDone, toggle } = useProfile();
  const { askAboutNode } = useMentor();
  return (
    <aside className="absolute z-10 top-0 right-0 h-full w-full sm:w-[380px] bg-white border-l border-slate-200 shadow-2xl overflow-y-auto animate-scale-in" aria-label="Node details">
      <div className="p-5 space-y-5">
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-lg font-black text-slate-900 leading-tight">{node.title}</h3>
          <button onClick={onClose} aria-label="Close details" className="w-8 h-8 rounded-lg bg-slate-100 hover:bg-slate-200 flex items-center justify-center shrink-0"><X className="w-4 h-4" /></button>
        </div>
        {node.summary && <p className="text-sm text-slate-500">{node.summary}</p>}
        <button
          onClick={() => askAboutNode(node)}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl text-sm font-bold text-white"
          style={{ background: 'linear-gradient(135deg, #f97316, #ef4444)' }}
        >
          <Bot className="w-4 h-4" /> Ask AI Mentor about this path
        </button>
        {node.duration && node.duration !== '-' && <Row label="Duration">{node.duration}</Row>}
        <Row label="Eligibility">{node.eligibility}</Row>
        <Row label="Entrance exams / admission"><Pills items={node.entrance_exams} /></Row>
        <Row label="Top branches / roles"><Pills items={node.top_branches_or_roles} tone="emerald" /></Row>
        <Row label="Indicative salary">{node.avg_salary_range}</Row>
        {node.next_nodes.length > 0 && (
          <Row label="Where it leads">
            <div className="flex flex-col gap-1.5">
              {node.next_nodes.map((id) => (
                <button key={id} onClick={() => onSelect(id)} className="text-left text-xs font-bold text-indigo-600 hover:underline">→ {titleOf(id) || prettyId(id)}</button>
              ))}
            </div>
          </Row>
        )}
        {node.college_type && <Colleges node={node} />}
        {node.official_links?.length > 0 && (
          <Row label="Official sources">
            {node.official_links.map((l) => (
              <a key={l} href={l} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs font-bold text-indigo-600 hover:underline break-all">
                <ExternalLink className="w-3 h-3 shrink-0" />{l}
              </a>
            ))}
          </Row>
        )}
        <p className="text-[11px] text-slate-400">Last updated {node.last_updated}. Always verify on the official portal.</p>
        {node.kind !== 'root' && (
          <button onClick={() => toggle('roadmapDone', node.id)} className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-bold border ${roadmapDone[node.id] ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-white text-slate-600 border-slate-200'}`}>
            <CheckCircle2 className="w-4 h-4" /> {roadmapDone[node.id] ? 'Marked as explored' : 'Mark as explored'}
          </button>
        )}
      </div>
    </aside>
  );
}

export default function RoadmapPage() {
  const { profile, roadmapDone } = useProfile();
  const [stage, setStage] = useState(profile?.stage || 'after_10th');
  const [stream, setStream] = useState(profile?.stream || '');
  const [graph, setGraph] = useState(null);
  const [error, setError] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [pendingSelect, setPendingSelect] = useState(null);

  const streamOptions = QUIZ_FALLBACK.streams[stage] || [];

  useEffect(() => {
    let live = true;
    setGraph(null);
    setError('');
    getRoadmap(stage, stream)
      .then((g) => live && setGraph(g))
      .catch(() => live && setError('Could not load the roadmap. The server may be waking up. Please retry in a few seconds.'));
    return () => { live = false; };
  }, [stage, stream]);

  useEffect(() => {
    if (graph && pendingSelect && graph.nodes.some((n) => n.id === pendingSelect)) {
      setSelectedId(pendingSelect);
      setPendingSelect(null);
    }
  }, [graph, pendingSelect]);

  const { rfNodes, rfEdges } = useMemo(
    () => (graph ? layout(graph, roadmapDone, selectedId) : { rfNodes: [], rfEdges: [] }),
    [graph, roadmapDone, selectedId]
  );
  const selected = graph?.nodes.find((n) => n.id === selectedId) || null;

  const openNode = useCallback((_, rfNode) => {
    const raw = rfNode.data.raw;
    if (raw.external) {
      setStream('');
      setStage(raw.stage);
      setPendingSelect(raw.id);
    } else {
      setSelectedId(raw.id);
    }
  }, []);

  const selectById = (id) => {
    const inGraph = graph.nodes.find((n) => n.id === id);
    if (inGraph && !inGraph.external) setSelectedId(id);
    else if (inGraph) { setStream(''); setStage(inGraph.stage); setPendingSelect(id); }
    else {
      // Hidden by the stream filter: clear it and open the node in its own stage.
      const targetStage = STAGE_BY_PREFIX[id.split('_')[0]] || stage;
      setStream(''); setStage(targetStage); setSelectedId(null); setPendingSelect(id);
    }
  };

  return (
    <div className="pt-4 flex flex-col gap-4 h-[calc(100vh-190px)] min-h-[520px]">
      <div className="flex flex-wrap items-center gap-2">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => { setStage(t.id); setStream(''); setSelectedId(null); }}
            className={`px-4 py-2.5 rounded-2xl text-sm font-bold transition-all ${stage === t.id ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/30' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
            {t.label}
          </button>
        ))}
        <select value={stream} onChange={(e) => { setStream(e.target.value); setSelectedId(null); }} aria-label="Filter by stream"
          className="ml-auto text-sm font-bold border border-slate-200 rounded-xl px-3 py-2.5 bg-white">
          <option value="">All streams</option>
          {streamOptions.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
      </div>

      <div className="relative flex-1 rounded-3xl border border-slate-200 bg-slate-50 overflow-hidden">
        {error && <div className="absolute inset-0 flex items-center justify-center p-6 text-sm font-semibold text-red-600 text-center">{error}</div>}
        {!graph && !error && <div className="absolute inset-0 flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-indigo-500" /></div>}
        {graph && (
          <ReactFlow key={`${stage}-${stream}`} nodes={rfNodes} edges={rfEdges} onNodeClick={openNode} fitView fitViewOptions={{ padding: 0.15 }}
            nodesDraggable={false} nodesConnectable={false} minZoom={0.3} proOptions={{ hideAttribution: true }}>
            <Background gap={20} color="#e2e8f0" />
            <Controls showInteractive={false} />
          </ReactFlow>
        )}
        {selected && (
          <Drawer node={selected} onClose={() => setSelectedId(null)} onSelect={selectById}
            titleOf={(id) => graph.nodes.find((n) => n.id === id)?.title} />
        )}
      </div>
      <p className="text-[11px] text-slate-400">Click any node for details. Dashed nodes continue in another stage. Data updated {graph?.last_updated || '...'}.</p>
    </div>
  );
}
