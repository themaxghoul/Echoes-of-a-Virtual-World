import "@/App.css";
import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import LoadingScreen from "@/components/LoadingScreen";
import { PurchaseProvider } from "@/context/PurchaseContext";
import { ControlLayoutProvider } from "@/context/ControlLayoutContext";
import LandingPage from "@/pages/LandingPage";
import AuthPage from "@/pages/AuthPage";
import AuthCallback from "@/components/AuthCallback";
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
import ChatHistory from "@/pages/ChatHistory";
import SkillsPage from "@/pages/SkillsPage";
import CharacterCustomization from "@/pages/CharacterCustomization";
import TasksDashboard from "@/pages/TasksDashboard";
import ComputeMarketplace from "@/pages/ComputeMarketplace";
import BuildingGrid from "@/pages/BuildingGrid";
import WorldMapUI from "@/pages/WorldMapUI";
import UnityWebGL from "@/pages/UnityWebGL";
import ProfileSettings from "@/pages/ProfileSettings";
import SkillTrees from "@/pages/SkillTrees";
import IsometricBuilder from "@/pages/IsometricBuilder";
import TaskMarketplace from "@/pages/TaskMarketplace";
import AIPartners from "@/pages/AIPartners";
import Onboarding from "@/pages/Onboarding";
import Leaderboard from "@/pages/Leaderboard";
import DiscoveryLab from "@/pages/DiscoveryLab";
import WorldExplorer from "@/pages/WorldExplorer";
import StorePage from "@/pages/StorePage";
import NPCServices from "@/pages/NPCServices";
import TaskFactory from "@/pages/TaskFactory";
import TaskWorkbench from "@/pages/TaskWorkbench";
import AvatarStudio from "@/pages/AvatarStudio";
import VEBoutique from "@/pages/VEBoutique";

function App() {
  const [loading, setLoading] = useState(true);
  const [loadingMessage, setLoadingMessage] = useState("Initializing...");

  useEffect(() => {
    // Simulate loading sequence
    const messages = [
      "Initializing...",
      "Loading world data...",
      "Connecting to Virtual Verse...",
      "Ready!"
    ];
    
    let i = 0;
    const interval = setInterval(() => {
      i++;
      if (i < messages.length) {
        setLoadingMessage(messages[i]);
      }
    }, 600);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="App min-h-screen bg-obsidian text-foreground">
      {loading && (
        <LoadingScreen 
          message={loadingMessage}
          minDuration={2500}
          onComplete={() => setLoading(false)}
        />
      )}
      <ControlLayoutProvider>
      <PurchaseProvider>
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
          <Route path="/chat-history" element={<ChatHistory />} />
          <Route path="/skills" element={<SkillsPage />} />
          <Route path="/customize-character" element={<CharacterCustomization />} />
          <Route path="/dataspace" element={<DataspaceView />} />
          <Route path="/quests" element={<QuestBoard />} />
          <Route path="/profile" element={<UserProfilePage />} />
          <Route path="/building" element={<BuildingPage />} />
          <Route path="/trading" element={<TradingPage />} />
          <Route path="/guilds" element={<GuildPage />} />
          <Route path="/inventory" element={<InventoryPage />} />
          <Route path="/earnings" element={<EarningsHub />} />
          <Route path="/jobs" element={<JobsHub />} />
          <Route path="/tasks" element={<TasksDashboard />} />
          <Route path="/compute" element={<ComputeMarketplace />} />
          <Route path="/build" element={<BuildingGrid />} />
          <Route path="/world-map" element={<WorldMapUI />} />
          <Route path="/webgl" element={<UnityWebGL />} />
          <Route path="/settings" element={<ProfileSettings />} />
          <Route path="/skill-trees" element={<SkillTrees />} />
          <Route path="/isometric-builder" element={<IsometricBuilder />} />
          <Route path="/marketplace" element={<TaskMarketplace />} />
          <Route path="/ai-partners" element={<AIPartners />} />
          <Route path="/quest-board" element={<QuestBoard />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/discovery-lab" element={<DiscoveryLab />} />
          <Route path="/world-explorer" element={<WorldExplorer />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route path="/store" element={<StorePage />} />
          <Route path="/npc-services" element={<NPCServices />} />
          <Route path="/task-factory" element={<TaskFactory />} />
          <Route path="/task-workbench" element={<TaskWorkbench />} />
          <Route path="/avatar-studio" element={<AvatarStudio />} />
          <Route path="/boutique" element={<VEBoutique />} />
        </Routes>
        </BrowserRouter>
      </PurchaseProvider>
      </ControlLayoutProvider>
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
