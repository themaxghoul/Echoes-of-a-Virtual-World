import { useState, useEffect, useCallback, createContext, useContext } from 'react';

// Default control positions
const DEFAULT_POSITIONS = {
  // Movement controls
  moveUp: { x: 80, y: 500, label: 'W/↑', key: 'w' },
  moveDown: { x: 80, y: 600, label: 'S/↓', key: 's' },
  moveLeft: { x: 30, y: 550, label: 'A/←', key: 'a' },
  moveRight: { x: 130, y: 550, label: 'D/→', key: 'd' },
  
  // Action buttons
  interact: { x: 1750, y: 550, label: 'E', key: 'e' },
  inventory: { x: 1750, y: 480, label: 'I', key: 'i' },
  map: { x: 1820, y: 480, label: 'M', key: 'm' },
  menu: { x: 1820, y: 550, label: 'ESC', key: 'Escape' },
  
  // Combat controls
  attack: { x: 1750, y: 620, label: 'LMB', key: 'mouse0' },
  block: { x: 1820, y: 620, label: 'RMB', key: 'mouse1' },
  sprint: { x: 80, y: 670, label: 'SHIFT', key: 'Shift' },
  dodge: { x: 150, y: 670, label: 'SPACE', key: ' ' }
};

// Control Layout Context
const ControlLayoutContext = createContext(null);

export const ControlLayoutProvider = ({ children }) => {
  const [positions, setPositions] = useState(() => {
    const saved = localStorage.getItem('controlLayout');
    return saved ? JSON.parse(saved) : DEFAULT_POSITIONS;
  });
  const [editMode, setEditMode] = useState(false);
  const [dragging, setDragging] = useState(null);
  const [showControls, setShowControls] = useState(true);
  const [opacity, setOpacity] = useState(() => {
    const saved = localStorage.getItem('controlOpacity');
    return saved ? parseFloat(saved) : 0.7;
  });
  const [scale, setScale] = useState(() => {
    const saved = localStorage.getItem('controlScale');
    return saved ? parseFloat(saved) : 1.0;
  });

  // Save to localStorage
  useEffect(() => {
    localStorage.setItem('controlLayout', JSON.stringify(positions));
  }, [positions]);

  useEffect(() => {
    localStorage.setItem('controlOpacity', opacity.toString());
  }, [opacity]);

  useEffect(() => {
    localStorage.setItem('controlScale', scale.toString());
  }, [scale]);

  // Update position of a control
  const updatePosition = useCallback((controlId, x, y) => {
    setPositions(prev => ({
      ...prev,
      [controlId]: { ...prev[controlId], x, y }
    }));
  }, []);

  // Reset to default positions
  const resetPositions = useCallback(() => {
    setPositions(DEFAULT_POSITIONS);
    setOpacity(0.7);
    setScale(1.0);
    localStorage.removeItem('controlLayout');
    localStorage.removeItem('controlOpacity');
    localStorage.removeItem('controlScale');
  }, []);

  // Handle drag start
  const handleDragStart = useCallback((controlId, e) => {
    if (!editMode) return;
    e.preventDefault();
    const rect = e.target.getBoundingClientRect();
    setDragging({
      id: controlId,
      offsetX: e.clientX - rect.left,
      offsetY: e.clientY - rect.top
    });
  }, [editMode]);

  // Handle drag move
  const handleDragMove = useCallback((e) => {
    if (!dragging) return;
    const newX = e.clientX - dragging.offsetX;
    const newY = e.clientY - dragging.offsetY;
    updatePosition(dragging.id, newX, newY);
  }, [dragging, updatePosition]);

  // Handle drag end
  const handleDragEnd = useCallback(() => {
    setDragging(null);
  }, []);

  // Toggle edit mode
  const toggleEditMode = useCallback(() => {
    setEditMode(prev => !prev);
  }, []);

  // Get control by key
  const getControlByKey = useCallback((key) => {
    return Object.entries(positions).find(([_, control]) => control.key === key);
  }, [positions]);

  return (
    <ControlLayoutContext.Provider value={{
      positions,
      editMode,
      dragging,
      showControls,
      opacity,
      scale,
      setShowControls,
      setOpacity,
      setScale,
      updatePosition,
      resetPositions,
      toggleEditMode,
      handleDragStart,
      handleDragMove,
      handleDragEnd,
      getControlByKey
    }}>
      {children}
    </ControlLayoutContext.Provider>
  );
};

export const useControlLayout = () => {
  const context = useContext(ControlLayoutContext);
  if (!context) {
    throw new Error('useControlLayout must be used within a ControlLayoutProvider');
  }
  return context;
};

// Draggable Control Button Component
export const DraggableControl = ({ 
  controlId, 
  children,
  className = "",
  onPress
}) => {
  const { 
    positions, 
    editMode, 
    opacity, 
    scale,
    handleDragStart,
    handleDragMove,
    handleDragEnd
  } = useControlLayout();

  const control = positions[controlId];
  if (!control) return null;

  const style = {
    position: 'fixed',
    left: control.x,
    top: control.y,
    opacity: opacity,
    transform: `scale(${scale})`,
    transformOrigin: 'center',
    zIndex: editMode ? 1000 : 100,
    cursor: editMode ? 'move' : 'pointer',
    touchAction: 'none'
  };

  return (
    <div
      style={style}
      className={`draggable-control ${editMode ? 'edit-mode' : ''} ${className}`}
      onMouseDown={(e) => handleDragStart(controlId, e)}
      onMouseMove={handleDragMove}
      onMouseUp={handleDragEnd}
      onMouseLeave={handleDragEnd}
      onTouchStart={(e) => {
        const touch = e.touches[0];
        handleDragStart(controlId, { clientX: touch.clientX, clientY: touch.clientY, target: e.target, preventDefault: () => e.preventDefault() });
      }}
      onTouchMove={(e) => {
        const touch = e.touches[0];
        handleDragMove({ clientX: touch.clientX, clientY: touch.clientY });
      }}
      onTouchEnd={handleDragEnd}
      onClick={() => !editMode && onPress && onPress()}
      data-testid={`control-${controlId}`}
    >
      {children || (
        <div className={`
          w-14 h-14 rounded-xl flex items-center justify-center
          ${editMode 
            ? 'bg-gold/40 border-2 border-gold border-dashed' 
            : 'bg-black/50 border border-white/20 backdrop-blur-sm'
          }
          text-white font-mono text-sm font-bold
          hover:bg-white/20 transition-colors
          active:scale-95
        `}>
          {control.label}
        </div>
      )}
      {editMode && (
        <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-xs text-gold whitespace-nowrap bg-black/80 px-2 py-0.5 rounded">
          {controlId}
        </div>
      )}
    </div>
  );
};

// Control Layout Editor Panel
export const ControlLayoutEditor = () => {
  const {
    editMode,
    showControls,
    opacity,
    scale,
    setShowControls,
    setOpacity,
    setScale,
    toggleEditMode,
    resetPositions
  } = useControlLayout();

  return (
    <div className="fixed top-4 right-4 z-[1001] bg-surface/90 backdrop-blur-sm rounded-lg border border-border/30 p-4 w-64" data-testid="control-editor">
      <h3 className="font-cinzel text-gold mb-4">Control Layout</h3>
      
      {/* Edit Mode Toggle */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm">Edit Mode</span>
        <button
          onClick={toggleEditMode}
          className={`px-3 py-1 rounded text-sm transition-colors ${
            editMode 
              ? 'bg-gold text-black' 
              : 'bg-surface border border-border/30'
          }`}
          data-testid="toggle-edit-mode"
        >
          {editMode ? 'ON' : 'OFF'}
        </button>
      </div>
      
      {editMode && (
        <p className="text-xs text-amber-400 mb-4 bg-amber-500/10 p-2 rounded">
          Drag any control button to reposition it
        </p>
      )}
      
      {/* Show/Hide Controls */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm">Show Controls</span>
        <button
          onClick={() => setShowControls(!showControls)}
          className={`px-3 py-1 rounded text-sm transition-colors ${
            showControls 
              ? 'bg-green-500/20 text-green-400' 
              : 'bg-red-500/20 text-red-400'
          }`}
          data-testid="toggle-show-controls"
        >
          {showControls ? 'VISIBLE' : 'HIDDEN'}
        </button>
      </div>
      
      {/* Opacity Slider */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm">Opacity</span>
          <span className="text-xs text-muted-foreground">{Math.round(opacity * 100)}%</span>
        </div>
        <input
          type="range"
          min="0.1"
          max="1"
          step="0.05"
          value={opacity}
          onChange={(e) => setOpacity(parseFloat(e.target.value))}
          className="w-full accent-gold"
          data-testid="opacity-slider"
        />
      </div>
      
      {/* Scale Slider */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm">Size</span>
          <span className="text-xs text-muted-foreground">{Math.round(scale * 100)}%</span>
        </div>
        <input
          type="range"
          min="0.5"
          max="1.5"
          step="0.1"
          value={scale}
          onChange={(e) => setScale(parseFloat(e.target.value))}
          className="w-full accent-gold"
          data-testid="scale-slider"
        />
      </div>
      
      {/* Reset Button */}
      <button
        onClick={resetPositions}
        className="w-full py-2 bg-red-500/20 text-red-400 border border-red-500/30 rounded hover:bg-red-500/30 transition-colors text-sm"
        data-testid="reset-controls"
      >
        Reset to Default
      </button>
    </div>
  );
};

export default ControlLayoutContext;
