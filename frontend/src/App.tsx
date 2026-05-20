import { Routes, Route } from 'react-router-dom';
import { LobbyPage } from './LobbyPage';
import { BoardPage } from './BoardPage';
import { BatchPage } from './BatchPage';

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LobbyPage />} />
      <Route path="/batch" element={<BatchPage />} />
      <Route path="/games/:gameId" element={<BoardPage />} />
    </Routes>
  );
}
