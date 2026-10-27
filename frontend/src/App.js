import "@/App.css";
import { useEffect } from "react";
import { BrowserRouter, HashRouter, Navigate, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import LandingPage from "@/pages/LandingPage";
import AuthPage from "@/pages/AuthPage";
import CharacterCreation from "@/pages/CharacterCreation";
import ModeSelection from "@/pages/ModeSelection";
import VillageExplorer from "@/pages/VillageExplorer";
import TermsOfService from "@/pages/TermsOfService";
import GeographicRestrictions from "@/pages/GeographicRestrictions";
import IsometricSettlement from "@/pages/IsometricSettlement";
import GameSettings from "@/pages/GameSettings";

function App() {
  const Router = window.eovDesktop ? HashRouter : BrowserRouter;
  useEffect(() => {
    try {
      const settings = JSON.parse(localStorage.getItem('eov-game-settings'));
      if (settings?.textScale) document.documentElement.style.fontSize = `${settings.textScale}%`;
      document.documentElement.classList.toggle('eov-reduce-motion', Boolean(settings?.reduceMotion));
      document.documentElement.classList.toggle('eov-high-contrast', Boolean(settings?.highContrast));
    } catch {
      // Invalid preferences fall back to the stylesheet defaults.
    }
  }, []);
  return (
    <div className="App min-h-screen bg-obsidian text-foreground">
      <Router>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/terms" element={<TermsOfService />} />
          <Route path="/geo-restrictions" element={<GeographicRestrictions />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/create-character" element={<CharacterCreation />} />
          <Route path="/select-mode" element={<ModeSelection />} />
          <Route path="/village" element={<VillageExplorer />} />
          <Route path="/play" element={<IsometricSettlement />} />
          <Route path="/play-3d" element={<Navigate to="/play" replace />} />
          <Route path="/play-classic" element={<Navigate to="/play" replace />} />
          <Route path="/unity" element={<Navigate to="/play" replace />} />
          <Route path="/chat-history" element={<Navigate to="/village" replace />} />
          <Route path="/settings" element={<GameSettings />} />
          {['/skills', '/customize-character', '/dataspace', '/quests', '/profile', '/building', '/trading', '/guilds', '/inventory', '/earnings', '/jobs'].map(path => <Route key={path} path={path} element={<Navigate to="/play" replace />} />)}
          <Route path="*" element={<Navigate to="/select-mode" replace />} />
        </Routes>
      </Router>
      <Toaster 
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#0F0F11',
            border: '1px solid #27272A',
            color: '#E1E1E3',
          },
        }}
      />
    </div>
  );
}

export default App;
