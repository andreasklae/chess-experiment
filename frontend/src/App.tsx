import { useEffect, useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { LobbyPage } from './LobbyPage';
import { BoardPage } from './BoardPage';
import { BatchPage } from './BatchPage';
import { subscribeBusy } from './api';

/** A thin top progress bar shown whenever a backend request has been pending
 *  longer than the debounce — so a slow/blocking call (e.g. the backend
 *  launching a chess.com browser, ~30s) shows activity instead of the UI
 *  looking frozen. Fast polls stay invisible thanks to the debounce. */
function GlobalLoadingBar() {
  const [busy, setBusy] = useState(false);
  useEffect(() => subscribeBusy(setBusy), []);
  if (!busy) return null;
  return (
    <div className="global-loading" role="status" aria-live="polite" aria-label="Loading">
      <div className="global-loading__bar" />
      <span className="global-loading__text">Waiting for backend…</span>
    </div>
  );
}

export function App() {
  return (
    <>
      <GlobalLoadingBar />
      <Routes>
        <Route path="/" element={<LobbyPage />} />
        <Route path="/batch" element={<BatchPage />} />
        <Route path="/games/:gameId" element={<BoardPage />} />
      </Routes>
    </>
  );
}
