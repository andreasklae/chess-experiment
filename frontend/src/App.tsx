import { Routes, Route } from 'react-router-dom';
import { LobbyPage } from './LobbyPage';
import { BoardPage } from './BoardPage';

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LobbyPage />} />
      <Route path="/games/:gameId" element={<BoardPage />} />
    </Routes>
  );
}
