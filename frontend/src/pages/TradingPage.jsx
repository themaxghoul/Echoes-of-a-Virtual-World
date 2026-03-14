import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { 
  ArrowLeft, ArrowLeftRight, Plus, Coins, Package,
  Loader2, CheckCircle, X
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const MATERIAL_COLORS = {
  wood: '#8B4513',
  stone: '#696969',
  iron: '#434343',
  crystal: '#00CED1',
  obsidian: '#1a1a2e'
};

const TradingPage = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [trades, setTrades] = useState([]);
  const [inventory, setInventory] = useState(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  
  const [newTrade, setNewTrade] = useState({
    offering: { type: 'wood', amount: 5 },
    requesting: { type: 'gold', amount: 25 }
  });

  const userId = localStorage.getItem('userId');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    if (!userId) {
      navigate('/auth');
      return;
    }

    try {
      const [tradesRes, invRes] = await Promise.all([
        axios.get(`${API}/trade/offers`),
        axios.get(`${API}/inventory/${userId}`)
      ]);

      setTrades(tradesRes.data);
      setInventory(invRes.data);
    } catch (error) {
      console.error('Failed to load:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateTrade = async () => {
    try {
      const offering = {};
      const requesting = {};
      
      offering[newTrade.offering.type] = newTrade.offering.amount;
      requesting[newTrade.requesting.type] = newTrade.requesting.amount;

      await axios.post(`${API}/trade/offer`, {
        seller_id: userId,
        offering,
        requesting
      });

      toast.success('Trade offer posted!');
      setShowCreateDialog(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create trade');
    }
  };

  const handleAcceptTrade = async (tradeId) => {
    try {
      await axios.put(`${API}/trade/${tradeId}/accept?buyer_id=${userId}`);
      toast.success('Trade completed!');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to accept trade');
    }
  };

  const handleCancelTrade = async (tradeId) => {
    try {
      await axios.put(`${API}/trade/${tradeId}/cancel?user_id=${userId}`);
      toast.success('Trade cancelled');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to cancel trade');
    }
  };

  const materials = ['wood', 'stone', 'iron', 'crystal', 'obsidian', 'gold'];

  if (isLoading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-gold animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-obsidian">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/30">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-muted-foreground hover:text-gold transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="font-manrope text-sm">Back</span>
          </button>
          <h1 className="font-cinzel text-lg text-gold tracking-wider flex items-center gap-2">
            <ArrowLeftRight className="w-5 h-5" />
            Trading Post
          </h1>
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button className="bg-gold text-black hover:bg-gold-light font-cinzel text-sm rounded-sm">
                <Plus className="w-4 h-4 mr-2" />
                New Trade
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-surface border-border/50 rounded-sm">
              <DialogHeader>
                <DialogTitle className="font-cinzel text-gold">Create Trade Offer</DialogTitle>
              </DialogHeader>
              <div className="space-y-6 pt-4">
                {/* Offering */}
                <div className="p-4 bg-obsidian/50 rounded-sm">
                  <h4 className="font-cinzel text-sm text-foreground mb-3">You Offer</h4>
                  <div className="flex gap-3">
                    <select
                      value={newTrade.offering.type}
                      onChange={(e) => setNewTrade(prev => ({
                        ...prev,
                        offering: { ...prev.offering, type: e.target.value }
                      }))}
                      className="flex-1 bg-surface border border-border/50 rounded-sm px-3 py-2 text-foreground"
                    >
                      {materials.filter(m => m !== 'gold').map(mat => (
                        <option key={mat} value={mat}>
                          {mat.charAt(0).toUpperCase() + mat.slice(1)} 
                          ({inventory?.materials[mat]?.amount || 0} owned)
                        </option>
                      ))}
                    </select>
                    <Input
                      type="number"
                      min="1"
                      value={newTrade.offering.amount}
                      onChange={(e) => setNewTrade(prev => ({
                        ...prev,
                        offering: { ...prev.offering, amount: parseInt(e.target.value) || 1 }
                      }))}
                      className="w-24 bg-surface border-border/50 rounded-sm"
                    />
                  </div>
                </div>

                <div className="flex justify-center">
                  <ArrowLeftRight className="w-6 h-6 text-gold" />
                </div>

                {/* Requesting */}
                <div className="p-4 bg-obsidian/50 rounded-sm">
                  <h4 className="font-cinzel text-sm text-foreground mb-3">You Want</h4>
                  <div className="flex gap-3">
                    <select
                      value={newTrade.requesting.type}
                      onChange={(e) => setNewTrade(prev => ({
                        ...prev,
                        requesting: { ...prev.requesting, type: e.target.value }
                      }))}
                      className="flex-1 bg-surface border border-border/50 rounded-sm px-3 py-2 text-foreground"
                    >
                      {materials.map(mat => (
                        <option key={mat} value={mat}>
                          {mat.charAt(0).toUpperCase() + mat.slice(1)}
                        </option>
                      ))}
                    </select>
                    <Input
                      type="number"
                      min="1"
                      value={newTrade.requesting.amount}
                      onChange={(e) => setNewTrade(prev => ({
                        ...prev,
                        requesting: { ...prev.requesting, amount: parseInt(e.target.value) || 1 }
                      }))}
                      className="w-24 bg-surface border-border/50 rounded-sm"
                    />
                  </div>
                </div>

                <Button
                  onClick={handleCreateTrade}
                  className="w-full bg-gold text-black hover:bg-gold-light font-cinzel rounded-sm"
                >
                  Post Trade Offer
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </header>

      {/* Main Content */}
      <main className="pt-24 pb-12 px-6">
        <div className="max-w-5xl mx-auto">
          {/* Your Inventory Summary */}
          <Card className="bg-surface/80 border-border/50 rounded-sm mb-8">
            <CardHeader>
              <CardTitle className="font-cinzel text-lg text-foreground flex items-center gap-2">
                <Package className="w-5 h-5 text-gold" />
                Your Resources
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4">
                <div className="flex items-center gap-2 px-3 py-2 bg-obsidian/50 rounded-sm">
                  <Coins className="w-4 h-4 text-gold" />
                  <span className="font-mono text-gold">{inventory?.gold || 0}</span>
                  <span className="text-xs text-muted-foreground">Gold</span>
                </div>
                {inventory?.materials && Object.entries(inventory.materials).map(([mat, data]) => (
                  <div 
                    key={mat}
                    className="flex items-center gap-2 px-3 py-2 bg-obsidian/50 rounded-sm"
                  >
                    <div 
                      className="w-4 h-4 rounded-sm"
                      style={{ backgroundColor: MATERIAL_COLORS[mat] }}
                    />
                    <span className="font-mono" style={{ color: MATERIAL_COLORS[mat] }}>
                      {data.amount}
                    </span>
                    <span className="text-xs text-muted-foreground capitalize">{mat}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Active Trades */}
          <h2 className="font-cinzel text-xl text-foreground mb-6">Active Trade Offers</h2>
          
          {trades.length === 0 ? (
            <Card className="bg-surface/80 border-border/50 rounded-sm">
              <CardContent className="p-12 text-center">
                <ArrowLeftRight className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="font-cinzel text-lg text-foreground mb-2">No Active Trades</h3>
                <p className="font-manrope text-sm text-muted-foreground">
                  Be the first to post a trade offer!
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {trades.map((trade) => {
                const isOwner = trade.seller_id === userId;
                const offeringItems = Object.entries(trade.offering);
                const requestingItems = Object.entries(trade.requesting);

                return (
                  <Card 
                    key={trade.id}
                    className={`bg-surface/80 border-border/50 rounded-sm ${
                      isOwner ? 'border-gold/30' : ''
                    }`}
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="font-cinzel text-base text-foreground">
                          {trade.seller_name}
                        </CardTitle>
                        {isOwner && (
                          <Badge className="bg-gold/20 text-gold rounded-sm text-xs">
                            Your Offer
                          </Badge>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center gap-4 mb-4">
                        {/* Offering */}
                        <div className="flex-1 p-3 bg-emerald-500/10 rounded-sm border border-emerald-500/30">
                          <div className="font-mono text-xs text-emerald-400 mb-1">OFFERING</div>
                          {offeringItems.map(([mat, amount]) => (
                            <div key={mat} className="flex items-center gap-2">
                              <div 
                                className="w-3 h-3 rounded-sm"
                                style={{ backgroundColor: MATERIAL_COLORS[mat] || '#D4AF37' }}
                              />
                              <span className="font-mono text-foreground">{amount}</span>
                              <span className="text-xs text-muted-foreground capitalize">{mat}</span>
                            </div>
                          ))}
                        </div>

                        <ArrowLeftRight className="w-5 h-5 text-muted-foreground" />

                        {/* Requesting */}
                        <div className="flex-1 p-3 bg-amber-500/10 rounded-sm border border-amber-500/30">
                          <div className="font-mono text-xs text-amber-400 mb-1">WANTS</div>
                          {requestingItems.map(([mat, amount]) => (
                            <div key={mat} className="flex items-center gap-2">
                              <div 
                                className="w-3 h-3 rounded-sm"
                                style={{ backgroundColor: MATERIAL_COLORS[mat] || '#D4AF37' }}
                              />
                              <span className="font-mono text-foreground">{amount}</span>
                              <span className="text-xs text-muted-foreground capitalize">{mat}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {isOwner ? (
                        <Button
                          onClick={() => handleCancelTrade(trade.id)}
                          variant="outline"
                          className="w-full border-red-500/30 text-red-400 hover:bg-red-500/10 rounded-sm"
                        >
                          <X className="w-4 h-4 mr-2" />
                          Cancel Offer
                        </Button>
                      ) : (
                        <Button
                          onClick={() => handleAcceptTrade(trade.id)}
                          className="w-full bg-gold text-black hover:bg-gold-light rounded-sm"
                        >
                          <CheckCircle className="w-4 h-4 mr-2" />
                          Accept Trade
                        </Button>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default TradingPage;
