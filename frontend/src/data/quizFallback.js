// Used while the backend is waking up (Render free tier) or unreachable.
// Must stay in sync with backend/app/services/guidance_service.py QUIZ.
export const QUIZ_FALLBACK = {
  stages: [
    { id: 'after_10th', label: 'I have passed (or am in) Class 10' },
    { id: 'after_12th', label: 'I have passed (or am in) Class 12' },
    { id: 'after_diploma', label: 'I have a Diploma / am in Diploma' },
  ],
  streams: {
    after_10th: [
      { id: 'science_pcm', label: 'Science (PCM)' }, { id: 'science_pcb', label: 'Science (PCB)' },
      { id: 'commerce', label: 'Commerce' }, { id: 'arts', label: 'Arts' },
      { id: 'diploma', label: 'Diploma / Polytechnic' }, { id: 'iti', label: 'ITI' },
      { id: 'vocational', label: 'Vocational / Skills' },
    ],
    after_12th: [
      { id: 'science_pcm', label: 'Science (PCM)' }, { id: 'science_pcb', label: 'Science (PCB)' },
      { id: 'commerce', label: 'Commerce' }, { id: 'arts', label: 'Arts' },
    ],
    after_diploma: [
      { id: 'dip_cs', label: 'Computer Engg.' }, { id: 'dip_it', label: 'Information Technology' },
      { id: 'dip_aiml', label: 'AI & ML / Data Science' }, { id: 'dip_mech', label: 'Mechanical' },
      { id: 'dip_civil', label: 'Civil' }, { id: 'dip_ece', label: 'Electronics & Telecom' },
      { id: 'dip_elec', label: 'Electrical' },
    ],
  },
  interests: [
    { id: 'R', label: 'Hands-on', hint: 'Build, repair, operate machines or tools' },
    { id: 'I', label: 'Investigative', hint: 'Analyse, research, solve puzzles' },
    { id: 'A', label: 'Creative', hint: 'Design, write, create new things' },
    { id: 'S', label: 'Social', hint: 'Teach, help and care for people' },
    { id: 'E', label: 'Enterprising', hint: 'Lead, persuade, start ventures' },
    { id: 'C', label: 'Organised', hint: 'Work with data, records and processes' },
  ],
  strengths: [
    { id: 'maths', label: 'Maths' }, { id: 'programming', label: 'Programming' },
    { id: 'problem_solving', label: 'Problem solving' }, { id: 'communication', label: 'Communication' },
    { id: 'creativity', label: 'Creativity' }, { id: 'leadership', label: 'Leadership' },
    { id: 'science', label: 'Science / Biology' }, { id: 'design', label: 'Drawing & Design' },
    { id: 'hands_on', label: 'Hands-on building' }, { id: 'numbers', label: 'Numbers & accounting' },
    { id: 'teamwork', label: 'Teamwork' },
  ],
};

export const GOAL_SUGGESTIONS = {
  after_10th: ['Software engineer', 'Doctor', 'Chartered Accountant', 'Mechanical engineer', 'Designer'],
  after_12th: ['Software engineer', 'Data scientist', 'Doctor', 'Lawyer', 'Entrepreneur'],
  after_diploma: ['Full stack developer', 'Junior Engineer (government)', 'B.Tech via DSE', 'AI/ML engineer', 'Site engineer'],
};
