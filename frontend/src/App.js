import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import LandingPage from "@/pages/LandingPage";
import AuthPage from "@/pages/AuthPage";
import CharacterCreation from "@/pages/CharacterCreation";
import ModeSelection from "@/pages/ModeSelection";
import VillageExplorer from "@/pages/VillageExplorer";
import FirstPersonView from "@/pages/FirstPersonView";
import DataspaceView from "@/pages/DataspaceView";
import QuestBoard from "@/pages/QuestBoard";
import UserProfilePage from "@/pages/UserProfilePage";
import BuildingPage from "@/pages/BuildingPage";
import TradingPage from "@/pages/TradingPage";

function App() {
  return (
    <div className="App min-h-screen bg-obsidian text-foreground">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/create-character" element={<CharacterCreation />} />
          <Route path="/select-mode" element={<ModeSelection />} />
          <Route path="/village" element={<VillageExplorer />} />
          <Route path="/play" element={<FirstPersonView />} />
          <Route path="/dataspace" element={<DataspaceView />} />
          <Route path="/quests" element={<QuestBoard />} />
          <Route path="/profile" element={<UserProfilePage />} />
          <Route path="/building" element={<BuildingPage />} />
          <Route path="/trading" element={<TradingPage />} />
        </Routes>
      </BrowserRouter>
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
