import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import LandingPage from "@/pages/LandingPage";
import CharacterCreation from "@/pages/CharacterCreation";
import VillageExplorer from "@/pages/VillageExplorer";
import DataspaceView from "@/pages/DataspaceView";
import QuestBoard from "@/pages/QuestBoard";
import UserProfilePage from "@/pages/UserProfilePage";

function App() {
  return (
    <div className="App min-h-screen bg-obsidian text-foreground">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/create-character" element={<CharacterCreation />} />
          <Route path="/village" element={<VillageExplorer />} />
          <Route path="/dataspace" element={<DataspaceView />} />
          <Route path="/quests" element={<QuestBoard />} />
          <Route path="/profile" element={<UserProfilePage />} />
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
