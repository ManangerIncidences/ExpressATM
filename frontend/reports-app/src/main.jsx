import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

createRoot(document.getElementById('reports-root')).render(
  <StrictMode>
    <App />
  </StrictMode>
);
