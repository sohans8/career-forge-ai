import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://career-copilot-api-9591.onrender.com';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,
});

export const checkHealth = async () => {
  try {
    const response = await api.get('/api/v1/health');
    return response.data;
  } catch (error) {
    console.error('API Health Check Error:', error);
    throw error;
  }
};

export const getRecommendations = async (profileData) => {
  try {
    const payload = {
      name: profileData.name || 'Student',
      subjects: profileData.subjects || [],
      skills: profileData.skills || [],
      interests: profileData.interests || [],
    };
    const response = await api.post('/api/v1/recommend', payload);
    return response.data;
  } catch (error) {
    console.error('API Recommendation Error:', error);
    throw error;
  }
};

// ── Career Forge AI platform endpoints ─────────────────────────────────────
const data = (p) => p.then((r) => r.data);

export const getQuiz = () => data(api.get('/api/guidance/quiz'));
export const getGuidance = (payload) => data(api.post('/api/guidance/recommend', payload));
export const getRoadmap = (stage, stream) =>
  data(api.get('/api/roadmaps', { params: { stage, ...(stream ? { stream } : {}) } }));
export const searchColleges = (params) => data(api.get('/api/colleges', { params }));
export const getStates = () => data(api.get('/api/colleges/states'));
export const getMentorPrompts = (stage) => data(api.get('/api/mentor/prompts', { params: { stage } }));
export const sendMentorMessage = (payload) => data(api.post('/api/mentor/chat', payload));
export const getResumeRoles = () => data(api.get('/api/resume/roles'));
export const analyzeResume = (file, targetRole) => {
  const form = new FormData();
  form.append('file', file);
  form.append('target_role', targetRole);
  return data(api.post('/api/resume/analyze', form, { headers: { 'Content-Type': 'multipart/form-data' } }));
};

export default api;
