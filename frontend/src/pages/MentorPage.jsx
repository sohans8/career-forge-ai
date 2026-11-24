import React from 'react';
import MentorChat from '../components/MentorChat';
import { STAGE_LABELS, useProfile } from '../context/ProfileContext';

export default function MentorPage() {
  const { profile } = useProfile();
  return (
    <div className="pt-4 h-[calc(100vh-190px)] min-h-[480px] flex flex-col gap-3">
      {profile && (
        <div className="flex flex-wrap gap-2 text-xs font-bold">
          <span className="px-3 py-1 rounded-full bg-indigo-50 text-indigo-700">{STAGE_LABELS[profile.stage]}</span>
          {profile.stream && <span className="px-3 py-1 rounded-full bg-indigo-50 text-indigo-700">{profile.stream.replace(/_/g, ' ')}</span>}
          {profile.career_goal && <span className="px-3 py-1 rounded-full bg-orange-50 text-orange-700">Goal: {profile.career_goal}</span>}
          <span className="text-slate-400 font-medium self-center">Answers are personalised to this profile.</span>
        </div>
      )}
      <div className="flex-1 min-h-0 rounded-3xl border border-slate-200 bg-white overflow-hidden"><MentorChat /></div>
      <p className="text-[11px] text-slate-400">AI can make mistakes. Confirm dates, fees and eligibility on official portals (aicte-india.org, nta.ac.in, cetcell.mahacet.org).</p>
    </div>
  );
}
