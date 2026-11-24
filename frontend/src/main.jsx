import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { ProfileProvider } from './context/ProfileContext'
import { MentorProvider } from './context/MentorContext'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ProfileProvider>
      <MentorProvider>
        <App />
      </MentorProvider>
    </ProfileProvider>
  </React.StrictMode>,
)
