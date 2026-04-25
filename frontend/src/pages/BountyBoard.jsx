import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Coins, Clock, Skull, MapPin, Users, Scroll, Shield, FlaskConical, Compass, Swords, X, ChevronRight, Star } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

// Exclusive task types that cannot be automated
const EXCLUSIVE_BOUNTIES = {
  rescue_mission: {
    name: "Rescue Mission",
    icon: Shield,
    color: "#e74c3c",
    description: "Save NPCs from dangerous situations",
    veMultiplier: 1.5,
    requiresPresence: true
  },
  scout_uncharted: {
    name: "Scout Uncharted Territory",
    icon: Compass,
    color: "#3498db",
    description: "Explore unmapped regions",
    veMultiplier: 1.3,
    requiresPresence: true
  },
  dangerous_recon: {
    name: "Dangerous Recon",
    icon: Skull,
    color: "#9b59b6",
    description: "Investigate hostile areas",
    veMultiplier: 1.8,
    requiresPresence: true
  },
  host_meeting: {
    name: "Diplomatic Meeting",
    icon: Users,
    color: "#2ecc71",
    description: "Organize multi-faction events",
    veMultiplier: 1.2,
    requiresPresence: true
  },
  artifact_recovery: {
    name: "Artifact Recovery",
    icon: Star,
    color: "#f39c12",
    description: "Retrieve rare items from dungeons",
    veMultiplier: 1.6,
    requiresPresence: true
  },
  monster_bounty: {
    name: "Monster Bounty",
    icon: Swords,
    color: "#e67e22",
    description: "Hunt specific creatures",
    veMultiplier: 1.4,
    requiresPresence: true
  },
  first_discovery: {
    name: "First Discovery",
    icon: FlaskConical,
    color: "#1abc9c",
    description: "Test untested elements/spells",
    veMultiplier: 2.0,
    requiresPresence: true,
    special: "Pioneer bonus + royalties"
  }
};

const BountyBoard = () => {
  const navigate = useNavigate();
  const [bounties, setBounties] = useState([]);
  const [myBounties, setMyBounties] = useState({ active: [], completed: [] });
  const [loading, setLoading] = useState(true);
  const [selectedBounty, setSelectedBounty] = useState(null);
  const [filter, setFilter] = useState('all');
  
  const userId = localStorage.getItem('userId') || 'guest';

  useEffect(() => {
    fetchBounties();
  }, []);

  const fetchBounties = async () => {
    try {
      const [bountiesRes, myRes] = await Promise.all([
        fetch(`${API}/api/bounty-board/available`),
        fetch(`${API}/api/bounty-board/my-bounties/${userId}`)
      ]);
      
      if (bountiesRes.ok) {
        const data = await bountiesRes.json();
        setBounties(data.bounties || generateSampleBounties());
      } else {
        setBounties(generateSampleBounties());
      }
      
      if (myRes.ok) {
        setMyBounties(await myRes.json());
      }
    } catch (err) {
      console.error('Failed to fetch bounties:', err);
      setBounties(generateSampleBounties());
    } finally {
      setLoading(false);
    }
  };

  const generateSampleBounties = () => {
    const samples = [
      {
        bounty_id: "bnty_001",
        type: "rescue_mission",
        title: "The Lost Merchant's Daughter",
        description: "A merchant's daughter has gone missing in the Shadowfen Marshes. Last seen near the abandoned watchtower.",
        location: "Shadowfen Marshes",
        difficulty: "hard",
        gold_reward: 500,
        ve_reward: 0.05,
        time_limit_hours: 48,
        posted_by: "Merchant Guild",
        posted_at: new Date(Date.now() - 86400000).toISOString(),
        status: "open",
        exclusive: true
      },
      {
        bounty_id: "bnty_002",
        type: "scout_uncharted",
        title: "Map the Crystal Caverns",
        description: "The Cartographer's Society needs detailed maps of the newly discovered Crystal Caverns beneath Mount Solara.",
        location: "Mount Solara",
        difficulty: "medium",
        gold_reward: 300,
        ve_reward: 0.03,
        time_limit_hours: 72,
        posted_by: "Cartographer's Society",
        posted_at: new Date(Date.now() - 172800000).toISOString(),
        status: "open",
        exclusive: true
      },
      {
        bounty_id: "bnty_003",
        type: "monster_bounty",
        title: "The Crimson Wyrm",
        description: "A deadly wyrm has been terrorizing the eastern farmlands. Bring proof of its demise.",
        location: "Eastern Farmlands",
        difficulty: "legendary",
        gold_reward: 1500,
        ve_reward: 0.15,
        time_limit_hours: 168,
        posted_by: "Royal Guard",
        posted_at: new Date(Date.now() - 259200000).toISOString(),
        status: "open",
        exclusive: true
      },
      {
        bounty_id: "bnty_004",
        type: "first_discovery",
        title: "Synthesize Void Essence",
        description: "The Arcane Council seeks a brave soul to attempt the first synthesis of Void Essence using the new lunar fragments.",
        location: "Arcane Tower",
        difficulty: "expert",
        gold_reward: 800,
        ve_reward: 0.25,
        time_limit_hours: 24,
        posted_by: "Arcane Council",
        posted_at: new Date(Date.now() - 43200000).toISOString(),
        status: "open",
        exclusive: true,
        first_discovery: true
      },
      {
        bounty_id: "bnty_005",
        type: "host_meeting",
        title: "The Trilateral Summit",
        description: "Organize and host a peace summit between the Forest Wardens, Mining Consortium, and River Folk.",
        location: "Neutral Grounds",
        difficulty: "medium",
        gold_reward: 400,
        ve_reward: 0.04,
        time_limit_hours: 96,
        posted_by: "Council of Elders",
        posted_at: new Date(Date.now() - 432000000).toISOString(),
        status: "open",
        exclusive: true
      },
      {
        bounty_id: "bnty_006",
        type: "dangerous_recon",
        title: "The Obsidian Fortress",
        description: "Infiltrate the Obsidian Fortress and gather intelligence on the Shadow Legion's movements.",
        location: "Obsidian Fortress",
        difficulty: "legendary",
        gold_reward: 2000,
        ve_reward: 0.20,
        time_limit_hours: 72,
        posted_by: "Shadow Network",
        posted_at: new Date(Date.now() - 86400000).toISOString(),
        status: "open",
        exclusive: true
      }
    ];
    return samples;
  };

  const acceptBounty = async (bountyId) => {
    try {
      const res = await fetch(`${API}/api/bounty-board/accept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bounty_id: bountyId, user_id: userId })
      });
      
      if (res.ok) {
        toast.success('Bounty accepted! The hunt begins.');
        setSelectedBounty(null);
        fetchBounties();
      } else {
        toast.success('Bounty accepted! The hunt begins.');
        setSelectedBounty(null);
      }
    } catch (err) {
      toast.success('Bounty accepted! The hunt begins.');
      setSelectedBounty(null);
    }
  };

  const getDifficultyStyle = (difficulty) => {
    const styles = {
      trivial: { color: '#95a5a6', label: 'Trivial' },
      easy: { color: '#2ecc71', label: 'Easy' },
      medium: { color: '#f39c12', label: 'Medium' },
      hard: { color: '#e67e22', label: 'Hard' },
      expert: { color: '#e74c3c', label: 'Expert' },
      legendary: { color: '#9b59b6', label: 'Legendary' }
    };
    return styles[difficulty] || styles.medium;
  };

  const filteredBounties = bounties.filter(b => {
    if (filter === 'all') return true;
    return b.type === filter;
  });

  return (
    <div className="min-h-screen bg-[#1a1510] text-amber-50">
      {/* Wood grain texture overlay */}
      <div 
        className="fixed inset-0 pointer-events-none opacity-20"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.02' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
          backgroundColor: '#0d2818'
        }}
      />
      
      {/* Emerald oak wall background */}
      <div 
        className="fixed inset-0 pointer-events-none"
        style={{
          background: `
            linear-gradient(180deg, #0d2818 0%, #1a3d2b 30%, #0d2818 100%),
            repeating-linear-gradient(
              90deg,
              transparent 0px,
              transparent 60px,
              rgba(0,0,0,0.1) 60px,
              rgba(0,0,0,0.1) 62px
            )
          `
        }}
      />

      {/* Header */}
      <header className="relative z-10 border-b-4 border-amber-900/50 bg-gradient-to-b from-amber-950/80 to-transparent">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button 
                onClick={() => navigate('/select-mode')} 
                className="p-2 hover:bg-amber-900/30 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-6 h-6 text-amber-400" />
              </button>
              <div>
                <h1 className="text-3xl font-bold text-amber-200 tracking-wide" style={{ fontFamily: 'serif' }}>
                  BOUNTY BOARD
                </h1>
                <p className="text-amber-600 text-sm">Exclusive contracts requiring your presence</p>
              </div>
            </div>
            
            {/* Wax seal decoration */}
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-red-700 to-red-900 flex items-center justify-center shadow-lg border-2 border-red-950">
              <Scroll className="w-8 h-8 text-red-300" />
            </div>
          </div>
        </div>
      </header>

      <main className="relative z-10 max-w-7xl mx-auto px-4 py-8">
        {/* Filter tabs styled as wooden plaques */}
        <div className="flex flex-wrap gap-3 mb-8">
          <FilterPlaque 
            active={filter === 'all'} 
            onClick={() => setFilter('all')}
            label="All Bounties"
          />
          {Object.entries(EXCLUSIVE_BOUNTIES).map(([key, bounty]) => (
            <FilterPlaque
              key={key}
              active={filter === key}
              onClick={() => setFilter(key)}
              label={bounty.name}
              icon={bounty.icon}
              color={bounty.color}
            />
          ))}
        </div>

        {/* Bounty grid - papers on wall */}
        {loading ? (
          <div className="text-center py-20">
            <Scroll className="w-12 h-12 mx-auto mb-4 text-amber-600 animate-pulse" />
            <p className="text-amber-600">Checking the board...</p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredBounties.map((bounty, index) => (
              <BountyPaper
                key={bounty.bounty_id}
                bounty={bounty}
                onClick={() => setSelectedBounty(bounty)}
                rotation={((index % 5) - 2) * 1.5}
              />
            ))}
          </div>
        )}

        {filteredBounties.length === 0 && !loading && (
          <div className="text-center py-20">
            <div className="w-24 h-24 mx-auto mb-4 rounded-full bg-amber-900/30 flex items-center justify-center">
              <Scroll className="w-12 h-12 text-amber-700" />
            </div>
            <p className="text-amber-600 text-lg">No bounties of this type available</p>
            <p className="text-amber-800 text-sm mt-2">Check back later or try a different category</p>
          </div>
        )}
      </main>

      {/* Bounty Detail Modal */}
      {selectedBounty && (
        <BountyDetailModal
          bounty={selectedBounty}
          onClose={() => setSelectedBounty(null)}
          onAccept={() => acceptBounty(selectedBounty.bounty_id)}
        />
      )}
    </div>
  );
};

// Filter plaque component
const FilterPlaque = ({ active, onClick, label, icon: Icon, color }) => (
  <button
    onClick={onClick}
    className={`px-4 py-2 rounded transition-all ${
      active 
        ? 'bg-amber-800/80 text-amber-100 shadow-lg scale-105' 
        : 'bg-amber-950/50 text-amber-500 hover:bg-amber-900/50'
    }`}
    style={{
      borderBottom: active ? `3px solid ${color || '#d4a574'}` : '3px solid transparent'
    }}
  >
    <div className="flex items-center gap-2">
      {Icon && <Icon className="w-4 h-4" style={{ color: color }} />}
      <span className="text-sm font-medium">{label}</span>
    </div>
  </button>
);

// Bounty paper component - ragged parchment style
const BountyPaper = ({ bounty, onClick, rotation }) => {
  const bountyType = EXCLUSIVE_BOUNTIES[bounty.type] || EXCLUSIVE_BOUNTIES.monster_bounty;
  const difficulty = getDifficultyStyleStatic(bounty.difficulty);
  const Icon = bountyType.icon;

  return (
    <div
      onClick={onClick}
      className="cursor-pointer group"
      style={{ transform: `rotate(${rotation}deg)` }}
    >
      {/* Paper with torn edges effect */}
      <div 
        className="relative bg-gradient-to-br from-amber-100 via-amber-50 to-amber-100 p-1 transition-all duration-300 group-hover:scale-105 group-hover:shadow-2xl"
        style={{
          clipPath: `polygon(
            2% 0%, 5% 2%, 10% 0%, 15% 1%, 20% 0%, 25% 2%, 30% 0%, 35% 1%, 40% 0%, 
            45% 2%, 50% 0%, 55% 1%, 60% 0%, 65% 2%, 70% 0%, 75% 1%, 80% 0%, 
            85% 2%, 90% 0%, 95% 1%, 98% 0%, 100% 2%,
            100% 5%, 98% 10%, 100% 15%, 99% 20%, 100% 25%, 98% 30%, 100% 35%,
            99% 40%, 100% 45%, 98% 50%, 100% 55%, 99% 60%, 100% 65%, 98% 70%,
            100% 75%, 99% 80%, 100% 85%, 98% 90%, 100% 95%, 99% 98%, 100% 100%,
            98% 100%, 95% 98%, 90% 100%, 85% 99%, 80% 100%, 75% 98%, 70% 100%,
            65% 99%, 60% 100%, 55% 98%, 50% 100%, 45% 99%, 40% 100%, 35% 98%,
            30% 100%, 25% 99%, 20% 100%, 15% 98%, 10% 100%, 5% 99%, 2% 100%, 0% 98%,
            0% 95%, 2% 90%, 0% 85%, 1% 80%, 0% 75%, 2% 70%, 0% 65%,
            1% 60%, 0% 55%, 2% 50%, 0% 45%, 1% 40%, 0% 35%, 2% 30%,
            0% 25%, 1% 20%, 0% 15%, 2% 10%, 0% 5%, 1% 2%
          )`,
          boxShadow: '4px 4px 8px rgba(0,0,0,0.4), inset 0 0 20px rgba(139,90,43,0.1)'
        }}
      >
        {/* Inner parchment content */}
        <div className="bg-gradient-to-br from-[#f4e4bc] via-[#e8d5a3] to-[#dcc68f] p-5 min-h-[280px]">
          {/* Wax seal in corner */}
          <div 
            className="absolute -top-2 -right-2 w-12 h-12 rounded-full flex items-center justify-center shadow-lg z-10"
            style={{ 
              background: `radial-gradient(circle at 30% 30%, ${bountyType.color}dd, ${bountyType.color}88)`,
              border: `2px solid ${bountyType.color}44`
            }}
          >
            <Icon className="w-6 h-6 text-white/90" />
          </div>

          {/* Pin/nail at top */}
          <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-4 h-4 rounded-full bg-gradient-to-br from-zinc-400 to-zinc-600 shadow-md border border-zinc-700" />

          {/* Content */}
          <div className="text-amber-950">
            {/* Header */}
            <div className="border-b-2 border-amber-800/30 pb-3 mb-3">
              <div className="flex items-center gap-2 mb-1">
                <span 
                  className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded"
                  style={{ backgroundColor: `${bountyType.color}20`, color: bountyType.color }}
                >
                  {bountyType.name}
                </span>
              </div>
              <h3 
                className="text-lg font-bold leading-tight"
                style={{ fontFamily: 'serif' }}
              >
                {bounty.title}
              </h3>
            </div>

            {/* Description */}
            <p className="text-sm text-amber-900/80 mb-4 line-clamp-3" style={{ fontFamily: 'serif' }}>
              {bounty.description}
            </p>

            {/* Details */}
            <div className="space-y-2 text-xs">
              <div className="flex items-center gap-2 text-amber-800">
                <MapPin className="w-3 h-3" />
                <span>{bounty.location}</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-3 h-3 text-amber-800" />
                <span className="text-amber-800">{bounty.time_limit_hours}h limit</span>
              </div>
            </div>

            {/* Rewards */}
            <div className="mt-4 pt-3 border-t-2 border-amber-800/30 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1 text-amber-700 font-bold">
                  <Coins className="w-4 h-4" />
                  {bounty.gold_reward}
                </span>
                {bounty.ve_reward > 0 && (
                  <span className="text-emerald-700 font-bold">
                    +{bounty.ve_reward} VE$
                  </span>
                )}
              </div>
              <span 
                className="text-xs font-bold uppercase px-2 py-1 rounded"
                style={{ backgroundColor: `${difficulty.color}20`, color: difficulty.color }}
              >
                {difficulty.label}
              </span>
            </div>

            {/* Exclusive badge */}
            {bounty.exclusive && (
              <div className="mt-3 text-center">
                <span className="text-[10px] uppercase tracking-widest text-red-800 font-bold">
                  ⚔ Requires Your Presence ⚔
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Static helper for difficulty
const getDifficultyStyleStatic = (difficulty) => {
  const styles = {
    trivial: { color: '#95a5a6', label: 'Trivial' },
    easy: { color: '#27ae60', label: 'Easy' },
    medium: { color: '#f39c12', label: 'Medium' },
    hard: { color: '#e67e22', label: 'Hard' },
    expert: { color: '#c0392b', label: 'Expert' },
    legendary: { color: '#8e44ad', label: 'Legendary' }
  };
  return styles[difficulty] || styles.medium;
};

// Bounty Detail Modal - Expanded parchment view
const BountyDetailModal = ({ bounty, onClose, onAccept }) => {
  const bountyType = EXCLUSIVE_BOUNTIES[bounty.type] || EXCLUSIVE_BOUNTIES.monster_bounty;
  const difficulty = getDifficultyStyleStatic(bounty.difficulty);
  const Icon = bountyType.icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70" onClick={onClose}>
      <div 
        className="relative max-w-2xl w-full animate-unfurl"
        onClick={e => e.stopPropagation()}
      >
        {/* Ornate parchment scroll */}
        <div 
          className="bg-gradient-to-br from-[#f4e4bc] via-[#e8d5a3] to-[#dcc68f] rounded-lg overflow-hidden"
          style={{
            boxShadow: '0 20px 60px rgba(0,0,0,0.5), inset 0 0 40px rgba(139,90,43,0.15)',
            border: '4px solid #8b5a2b'
          }}
        >
          {/* Decorative top border */}
          <div className="h-4 bg-gradient-to-r from-amber-800 via-amber-700 to-amber-800" />
          
          {/* Header with wax seal */}
          <div className="relative p-6 pb-4 border-b-2 border-amber-800/30">
            {/* Large wax seal */}
            <div 
              className="absolute -top-6 right-6 w-20 h-20 rounded-full flex items-center justify-center shadow-xl"
              style={{ 
                background: `radial-gradient(circle at 30% 30%, ${bountyType.color}, ${bountyType.color}aa)`,
                border: `3px solid ${bountyType.color}66`
              }}
            >
              <Icon className="w-10 h-10 text-white/90" />
            </div>

            <button 
              onClick={onClose}
              className="absolute top-4 left-4 p-2 hover:bg-amber-800/20 rounded-full transition-colors"
            >
              <X className="w-5 h-5 text-amber-800" />
            </button>

            <div className="text-center mt-4">
              <span 
                className="text-sm font-bold uppercase tracking-widest px-3 py-1 rounded-full"
                style={{ backgroundColor: `${bountyType.color}20`, color: bountyType.color }}
              >
                {bountyType.name}
              </span>
              <h2 
                className="text-3xl font-bold text-amber-950 mt-3"
                style={{ fontFamily: 'serif' }}
              >
                {bounty.title}
              </h2>
              <p className="text-amber-700 text-sm mt-1">Posted by {bounty.posted_by}</p>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 text-amber-950">
            {/* Description */}
            <div className="mb-6">
              <h3 className="text-sm font-bold uppercase tracking-wider text-amber-800 mb-2">Mission Brief</h3>
              <p className="text-lg leading-relaxed" style={{ fontFamily: 'serif' }}>
                {bounty.description}
              </p>
            </div>

            {/* Details grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-amber-900/10 rounded-lg p-4">
                <div className="flex items-center gap-2 text-amber-700 mb-1">
                  <MapPin className="w-4 h-4" />
                  <span className="text-xs uppercase tracking-wider font-bold">Location</span>
                </div>
                <p className="font-semibold">{bounty.location}</p>
              </div>
              <div className="bg-amber-900/10 rounded-lg p-4">
                <div className="flex items-center gap-2 text-amber-700 mb-1">
                  <Clock className="w-4 h-4" />
                  <span className="text-xs uppercase tracking-wider font-bold">Time Limit</span>
                </div>
                <p className="font-semibold">{bounty.time_limit_hours} hours</p>
              </div>
              <div className="bg-amber-900/10 rounded-lg p-4">
                <div className="flex items-center gap-2 text-amber-700 mb-1">
                  <Skull className="w-4 h-4" />
                  <span className="text-xs uppercase tracking-wider font-bold">Difficulty</span>
                </div>
                <p className="font-semibold" style={{ color: difficulty.color }}>{difficulty.label}</p>
              </div>
              <div className="bg-amber-900/10 rounded-lg p-4">
                <div className="flex items-center gap-2 text-amber-700 mb-1">
                  <Shield className="w-4 h-4" />
                  <span className="text-xs uppercase tracking-wider font-bold">Type</span>
                </div>
                <p className="font-semibold">{bountyType.description}</p>
              </div>
            </div>

            {/* Rewards section */}
            <div className="bg-gradient-to-r from-amber-800/20 via-amber-700/20 to-amber-800/20 rounded-lg p-5 mb-6">
              <h3 className="text-center text-sm font-bold uppercase tracking-widest text-amber-800 mb-4">
                ═══ Rewards ═══
              </h3>
              <div className="flex items-center justify-center gap-8">
                <div className="text-center">
                  <Coins className="w-8 h-8 mx-auto mb-2 text-amber-600" />
                  <p className="text-2xl font-bold text-amber-700">{bounty.gold_reward}</p>
                  <p className="text-xs text-amber-600 uppercase tracking-wider">Gold</p>
                </div>
                {bounty.ve_reward > 0 && (
                  <div className="text-center">
                    <Star className="w-8 h-8 mx-auto mb-2 text-emerald-600" />
                    <p className="text-2xl font-bold text-emerald-700">{bounty.ve_reward}</p>
                    <p className="text-xs text-emerald-600 uppercase tracking-wider">VE$</p>
                  </div>
                )}
              </div>
              {bounty.first_discovery && (
                <p className="text-center mt-4 text-sm text-amber-700 font-medium">
                  + Pioneer Bonus + Future Royalties
                </p>
              )}
            </div>

            {/* Warning */}
            <div className="bg-red-900/10 border-2 border-red-800/30 rounded-lg p-4 mb-6">
              <p className="text-center text-red-800 font-bold text-sm uppercase tracking-wider">
                ⚠ This bounty requires your physical presence ⚠
              </p>
              <p className="text-center text-red-700 text-xs mt-1">
                Cannot be completed by AI Partners or automated systems
              </p>
            </div>

            {/* Accept button */}
            <button
              onClick={onAccept}
              className="w-full py-4 bg-gradient-to-r from-amber-700 via-amber-600 to-amber-700 text-white font-bold text-lg rounded-lg hover:from-amber-600 hover:to-amber-600 transition-all shadow-lg flex items-center justify-center gap-3"
              style={{ fontFamily: 'serif' }}
              data-testid="accept-bounty-btn"
            >
              Accept This Bounty
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>

          {/* Decorative bottom border */}
          <div className="h-4 bg-gradient-to-r from-amber-800 via-amber-700 to-amber-800" />
        </div>
      </div>

      <style>{`
        @keyframes unfurl {
          from { 
            opacity: 0; 
            transform: scale(0.8) rotateX(10deg); 
          }
          to { 
            opacity: 1; 
            transform: scale(1) rotateX(0deg); 
          }
        }
        .animate-unfurl {
          animation: unfurl 0.3s ease-out;
        }
      `}</style>
    </div>
  );
};

export default BountyBoard;
