import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import LandingPage from "@/pages/LandingPage";
import AuthPage from "@/pages/AuthPage";
import CharacterCreation from "@/pages/CharacterCreation";
import ModeSelection from "@/pages/ModeSelection";
import VillageExplorer from "@/pages/VillageExplorer";
import FirstPersonView from "@/pages/FirstPersonView";
import FirstPersonView3D from "@/pages/FirstPersonView3D";
import DataspaceView from "@/pages/DataspaceView";
import QuestBoard from "@/pages/QuestBoard";
import UserProfilePage from "@/pages/UserProfilePage";
import BuildingPage from "@/pages/BuildingPage";
import TradingPage from "@/pages/TradingPage";
import GuildPage from "@/pages/GuildPage";
import InventoryPage from "@/pages/InventoryPage";
import TermsOfService from "@/pages/TermsOfService";
import GeographicRestrictions from "@/pages/GeographicRestrictions";
import EarningsHub from "@/pages/EarningsHub";
import JobsHub from "@/pages/JobsHub";
import UnityOffload from "@/pages/UnityOffload";

function App() {
  return (
    <div className="App min-h-screen bg-obsidian text-foreground">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/terms" element={<TermsOfService />} />
          <Route path="/geo-restrictions" element={<GeographicRestrictions />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/create-character" element={<CharacterCreation />} />
          <Route path="/select-mode" element={<ModeSelection />} />
          <Route path="/village" element={<VillageExplorer />} />
          <Route path="/play" element={<FirstPersonView3D />} />
          <Route path="/play-classic" element={<FirstPersonView />} />
          <Route path="/unity" element={<UnityOffload />} />
          <Route path="/dataspace" element={<DataspaceView />} />
          <Route path="/quests" element={<QuestBoard />} />
          <Route path="/profile" element={<UserProfilePage />} />
          <Route path="/building" element={<BuildingPage />} />
          <Route path="/trading" element={<TradingPage />} />
          <Route path="/guilds" element={<GuildPage />} />
          <Route path="/inventory" element={<InventoryPage />} />
          <Route path="/earnings" element={<EarningsHub />} />
          <Route path="/jobs" element={<JobsHub />} />
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
