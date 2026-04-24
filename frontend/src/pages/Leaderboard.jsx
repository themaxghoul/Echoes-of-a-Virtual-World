import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Trophy, Medal, Crown, Star, Coins, TrendingUp, Users, RefreshCw, ChevronDown } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const Leaderboard = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('rank');
  const [leaderboardData, setLeaderboardData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [userRank, setUserRank] = useState(null);
  
  const userId = localStorage.getItem('userId') || 'guest';

  useEffect(() => {
    fetchLeaderboard();
  }, [activeTab]);

  const fetchLeaderboard = async () => {
    setLoading(true);
    try {
      let endpoint = '';
      switch (activeTab) {
        case 'rank':
          endpoint = '/api/ranks/leaderboard';
          break;
        case 'earnings':
          endpoint = '/api/rt-tasks/leaderboard/hourly';
          break;
        case 'compute':
          endpoint = '/api/economy/leaderboard/compute';
          break;
        default:
          endpoint = '/api/ranks/leaderboard';
      }
      
      const res = await fetch(`${API}${endpoint}`);
      if (res.ok) {
        const data = await res.json();
        setLeaderboardData(data.leaderboard || data.top_earners || data.top_investors || []);
        
        // Find user's position
        const userEntry = (data.leaderboard || data.top_earners || data.top_investors || [])
          .findIndex(entry => entry.user_id === userId || entry.entity_id === userId);
        setUserRank(userEntry >= 0 ? userEntry + 1 : null);
      }
    } catch (err) {
      console.error('Failed to fetch leaderboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const getRankBadge = (position) => {
    if (position === 1) return { icon: Crown, color: 'text-amber-400', bg: 'bg-amber-400/20' };
    if (position === 2) return { icon: Medal, color: 'text-zinc-300', bg: 'bg-zinc-300/20' };
    if (position === 3) return { icon: Medal, color: 'text-amber-600', bg: 'bg-amber-600/20' };
    return { icon: null, color: 'text-zinc-500', bg: 'bg-zinc-800' };
  };

  const formatValue = (entry) => {
    switch (activeTab) {
      case 'rank':
        return `${entry.rank || 'F'} (${(entry.experience || 0).toLocaleString()} XP)`;
      case 'earnings':
        return `${(entry.earned || entry.total_earned || 0).toFixed(4)} VE$`;
      case 'compute':
        return `${(entry.total_compute || entry.compute_power || 0).toLocaleString()} units`;
      default:
        return entry.score || 0;
    }
  };

  const tabs = [
    { id: 'rank', label: 'Adventurer Rank', icon: Trophy },
    { id: 'earnings', label: 'Top Earners', icon: Coins },
    { id: 'compute', label: 'Compute Power', icon: TrendingUp }
  ];

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-[#0f0f15]/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/select-mode')} className="p-2 hover:bg-zinc-800 rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold">Leaderboard</h1>
            <p className="text-sm text-zinc-400">Top players in the Virtual Verse</p>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-colors ${
                activeTab === tab.id 
                  ? 'bg-purple-600 text-white' 
                  : 'bg-zinc-800/50 text-zinc-400 hover:bg-zinc-800'
              }`}
              data-testid={`tab-${tab.id}`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Your Position */}
        {userRank && (
          <div className="bg-gradient-to-r from-purple-900/30 to-pink-900/30 border border-purple-500/30 rounded-xl p-4 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-500/20 rounded-full flex items-center justify-center">
                  <Users className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <div className="text-sm text-zinc-400">Your Position</div>
                  <div className="font-bold text-lg">#{userRank}</div>
                </div>
              </div>
              <button 
                onClick={fetchLeaderboard}
                className="p-2 hover:bg-zinc-800 rounded-lg"
              >
                <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        )}

        {/* Leaderboard List */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-8 h-8 animate-spin text-purple-500" />
          </div>
        ) : leaderboardData.length === 0 ? (
          <div className="text-center py-12">
            <Trophy className="w-12 h-12 mx-auto mb-4 text-zinc-600" />
            <p className="text-zinc-400">No leaderboard data available yet.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {/* Top 3 Podium */}
            <div className="grid grid-cols-3 gap-4 mb-8">
              {[1, 0, 2].map((index) => {
                const entry = leaderboardData[index];
                if (!entry) return <div key={index} />;
                
                const position = index === 1 ? 1 : index === 0 ? 2 : 3;
                const badge = getRankBadge(position);
                const heightClass = position === 1 ? 'h-32' : position === 2 ? 'h-24' : 'h-20';
                
                return (
                  <div key={index} className={`flex flex-col items-center ${index === 1 ? 'order-2' : index === 0 ? 'order-1 mt-8' : 'order-3 mt-8'}`}>
                    <div className={`w-12 h-12 rounded-full ${badge.bg} flex items-center justify-center mb-2`}>
                      {badge.icon && <badge.icon className={`w-6 h-6 ${badge.color}`} />}
                    </div>
                    <div className="text-center mb-2">
                      <div className="font-semibold truncate max-w-[100px]">
                        {entry.username || entry.display_name || entry.user_id?.slice(0, 8)}
                      </div>
                      <div className="text-sm text-zinc-400">{formatValue(entry)}</div>
                    </div>
                    <div className={`w-full ${heightClass} bg-gradient-to-t rounded-t-lg ${
                      position === 1 ? 'from-amber-500/30 to-amber-500/10' :
                      position === 2 ? 'from-zinc-400/30 to-zinc-400/10' :
                      'from-amber-700/30 to-amber-700/10'
                    }`} />
                  </div>
                );
              })}
            </div>

            {/* Rest of leaderboard */}
            {leaderboardData.slice(3).map((entry, index) => {
              const position = index + 4;
              const isCurrentUser = entry.user_id === userId || entry.entity_id === userId;
              
              return (
                <div
                  key={entry.user_id || entry.entity_id || index}
                  className={`flex items-center gap-4 p-4 rounded-xl transition-colors ${
                    isCurrentUser 
                      ? 'bg-purple-500/10 border border-purple-500/30' 
                      : 'bg-zinc-900/50 border border-zinc-800 hover:border-zinc-700'
                  }`}
                  data-testid={`leaderboard-entry-${position}`}
                >
                  <div className="w-10 text-center font-bold text-zinc-500">
                    #{position}
                  </div>
                  
                  <div className="w-10 h-10 bg-zinc-800 rounded-full flex items-center justify-center text-sm font-medium">
                    {(entry.username || entry.display_name || '?')[0].toUpperCase()}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">
                      {entry.username || entry.display_name || entry.user_id?.slice(0, 12)}
                      {isCurrentUser && <span className="ml-2 text-xs text-purple-400">(You)</span>}
                    </div>
                    {entry.rank && (
                      <div className="text-xs text-zinc-500">Rank: {entry.rank}</div>
                    )}
                  </div>
                  
                  <div className="text-right">
                    <div className={`font-semibold ${
                      activeTab === 'earnings' ? 'text-green-400' :
                      activeTab === 'compute' ? 'text-cyan-400' :
                      'text-amber-400'
                    }`}>
                      {formatValue(entry)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Load More */}
        {leaderboardData.length >= 10 && (
          <div className="text-center mt-6">
            <button className="px-6 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm font-medium flex items-center gap-2 mx-auto">
              <ChevronDown className="w-4 h-4" />
              Load More
            </button>
          </div>
        )}
      </main>
    </div>
  );
};

export default Leaderboard;
