import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { 
  X, Settings, RotateCcw, Save, Smartphone, 
  Monitor, Move, Hand, Swords, Shield, Sparkles, Zap
} from 'lucide-react';
import { toast } from 'sonner';

const DEFAULT_LAYOUT = {
  buttonSize: 45,
  buttonSpacing: 20,
  edgeMargin: 30,
  dpadPosition: { x: 30, y: 70 },
  actionButtonsPosition: { x: 85, y: 50 },
  combatButtonsPosition: { x: 85, y: 75 },
  showDpad: true,
  showCombatButtons: true,
  landscapeOptimized: true,
};

const LayoutCustomization = ({ isOpen, onClose, onSave }) => {
  const [layout, setLayout] = useState(DEFAULT_LAYOUT);
  const [previewMode, setPreviewMode] = useState('landscape');
  
  useEffect(() => {
    const saved = localStorage.getItem('gameLayout');
    if (saved) {
      try {
        setLayout({ ...DEFAULT_LAYOUT, ...JSON.parse(saved) });
      } catch (e) {
        console.error('Failed to load layout:', e);
      }
    }
  }, []);
  
  const handleSave = () => {
    localStorage.setItem('gameLayout', JSON.stringify(layout));
    onSave?.(layout);
    toast.success('Layout saved!');
    onClose();
  };
  
  const handleReset = () => {
    setLayout(DEFAULT_LAYOUT);
    localStorage.removeItem('gameLayout');
    toast.info('Layout reset to default');
  };
  
  if (!isOpen) return null;
  
  const ButtonPreview = ({ icon: Icon, label, x, y }) => (
    <div 
      className="absolute flex flex-col items-center gap-1 transition-all"
      style={{ 
        left: `${x}%`, 
        top: `${y}%`,
        transform: 'translate(-50%, -50%)'
      }}
    >
      <div 
        className="rounded-full bg-gold/30 border-2 border-gold flex items-center justify-center"
        style={{ 
          width: `${layout.buttonSize}px`, 
          height: `${layout.buttonSize}px` 
        }}
      >
        <Icon className="w-5 h-5 text-gold" />
      </div>
      <span className="text-[10px] text-muted-foreground">{label}</span>
    </div>
  );
  
  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <Card className="bg-surface/95 border-gold/30 rounded-sm w-full max-w-3xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-border/30 flex items-center justify-between bg-obsidian/50">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-gold" />
            <span className="font-cinzel text-lg text-gold">Layout Customization</span>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        </div>
        
        <div className="p-4 space-y-6">
          {/* Preview Mode Toggle */}
          <div className="flex items-center justify-center gap-4">
            <Button
              variant={previewMode === 'portrait' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setPreviewMode('portrait')}
              className="gap-2"
            >
              <Smartphone className="w-4 h-4" />
              Portrait
            </Button>
            <Button
              variant={previewMode === 'landscape' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setPreviewMode('landscape')}
              className="gap-2"
            >
              <Monitor className="w-4 h-4" />
              Landscape
            </Button>
          </div>
          
          {/* Preview Area */}
          <div 
            className={`relative mx-auto border-2 border-gold/30 rounded-lg bg-obsidian/50 overflow-hidden ${
              previewMode === 'landscape' ? 'w-full h-48' : 'w-48 h-80'
            }`}
          >
            <div className="absolute inset-0 bg-gradient-to-b from-slate-900/50 to-slate-800/50" />
            
            {/* D-Pad Preview */}
            {layout.showDpad && (
              <div 
                className="absolute"
                style={{ 
                  left: previewMode === 'landscape' ? '10%' : '50%',
                  bottom: previewMode === 'landscape' ? '20%' : '15%',
                  transform: previewMode === 'portrait' ? 'translateX(-50%)' : 'none'
                }}
              >
                <div className="w-20 h-20 rounded-full border-2 border-gold/50 bg-black/30 flex items-center justify-center">
                  <Move className="w-6 h-6 text-gold/50" />
                </div>
              </div>
            )}
            
            {/* Action Buttons Preview */}
            <div 
              className="absolute flex gap-2"
              style={{ 
                right: `${layout.edgeMargin}px`,
                bottom: previewMode === 'landscape' ? '30%' : '35%',
              }}
            >
              <ButtonPreview icon={Hand} label="Interact" x={0} y={0} />
            </div>
            
            {/* Combat Buttons Preview */}
            {layout.showCombatButtons && (
              <div 
                className="absolute flex flex-col items-center"
                style={{ 
                  right: `${layout.edgeMargin}px`,
                  bottom: previewMode === 'landscape' ? '5%' : '10%',
                }}
              >
                <div className="flex gap-2 mb-2">
                  <div 
                    className="rounded-full bg-red-500/30 border border-red-500 flex items-center justify-center"
                    style={{ width: `${layout.buttonSize}px`, height: `${layout.buttonSize}px` }}
                  >
                    <Swords className="w-4 h-4 text-red-400" />
                  </div>
                  <div 
                    className="rounded-full bg-blue-500/30 border border-blue-500 flex items-center justify-center"
                    style={{ width: `${layout.buttonSize}px`, height: `${layout.buttonSize}px` }}
                  >
                    <Shield className="w-4 h-4 text-blue-400" />
                  </div>
                  <div 
                    className="rounded-full bg-purple-500/30 border border-purple-500 flex items-center justify-center"
                    style={{ width: `${layout.buttonSize}px`, height: `${layout.buttonSize}px` }}
                  >
                    <Sparkles className="w-4 h-4 text-purple-400" />
                  </div>
                </div>
              </div>
            )}
            
            {/* Screen info */}
            <div className="absolute top-2 left-2 text-xs text-muted-foreground">
              {previewMode === 'landscape' ? 'Landscape (Recommended)' : 'Portrait'}
            </div>
          </div>
          
          {/* Settings */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Button Size */}
            <div className="space-y-2">
              <label className="text-sm text-foreground flex items-center justify-between">
                Button Size
                <span className="text-muted-foreground">{layout.buttonSize}px</span>
              </label>
              <Slider
                value={[layout.buttonSize]}
                onValueChange={([val]) => setLayout(l => ({ ...l, buttonSize: val }))}
                min={30}
                max={60}
                step={5}
                className="w-full"
              />
            </div>
            
            {/* Button Spacing */}
            <div className="space-y-2">
              <label className="text-sm text-foreground flex items-center justify-between">
                Button Spacing
                <span className="text-muted-foreground">{layout.buttonSpacing}px</span>
              </label>
              <Slider
                value={[layout.buttonSpacing]}
                onValueChange={([val]) => setLayout(l => ({ ...l, buttonSpacing: val }))}
                min={10}
                max={40}
                step={5}
                className="w-full"
              />
            </div>
            
            {/* Edge Margin */}
            <div className="space-y-2">
              <label className="text-sm text-foreground flex items-center justify-between">
                Edge Margin
                <span className="text-muted-foreground">{layout.edgeMargin}px</span>
              </label>
              <Slider
                value={[layout.edgeMargin]}
                onValueChange={([val]) => setLayout(l => ({ ...l, edgeMargin: val }))}
                min={15}
                max={50}
                step={5}
                className="w-full"
              />
            </div>
            
            {/* Toggles */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-foreground">Show D-Pad</span>
                <Switch
                  checked={layout.showDpad}
                  onCheckedChange={(checked) => setLayout(l => ({ ...l, showDpad: checked }))}
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-foreground">Show Combat Buttons</span>
                <Switch
                  checked={layout.showCombatButtons}
                  onCheckedChange={(checked) => setLayout(l => ({ ...l, showCombatButtons: checked }))}
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-foreground">Landscape Optimized</span>
                <Switch
                  checked={layout.landscapeOptimized}
                  onCheckedChange={(checked) => setLayout(l => ({ ...l, landscapeOptimized: checked }))}
                />
              </div>
            </div>
          </div>
          
          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-border/30">
            <Button variant="outline" onClick={handleReset} className="gap-2">
              <RotateCcw className="w-4 h-4" />
              Reset Default
            </Button>
            <Button onClick={handleSave} className="bg-gold text-black hover:bg-gold-light gap-2">
              <Save className="w-4 h-4" />
              Save Layout
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default LayoutCustomization;

// Hook to get current layout settings
export const useGameLayout = () => {
  const [layout, setLayout] = useState(DEFAULT_LAYOUT);
  
  useEffect(() => {
    const saved = localStorage.getItem('gameLayout');
    if (saved) {
      try {
        setLayout({ ...DEFAULT_LAYOUT, ...JSON.parse(saved) });
      } catch (e) {
        console.error('Failed to load layout:', e);
      }
    }
  }, []);
  
  return layout;
};
