import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './App';
import { ErrorBoundary } from './components/ErrorBoundary';
import { registerSW } from 'virtual:pwa-register';
import './styles.css';
// Second, so the merged design wins where both stylesheets touch the same
// element. The five class names that existed in both carry a ts- prefix here.
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><ErrorBoundary><BrowserRouter><App /></BrowserRouter></ErrorBoundary></React.StrictMode>,
);
registerSW({ immediate: true });
