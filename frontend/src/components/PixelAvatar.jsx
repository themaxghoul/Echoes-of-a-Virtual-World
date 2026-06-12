import React from 'react';
import { Grid3X3 } from 'lucide-react';

// Frame styles purchasable in the VE$ Boutique
export const FRAME_CLASSES = {
  frame_bronze: 'ring-2 ring-[#CD7F32]',
  frame_silver: 'ring-2 ring-[#C0C0C0]',
  frame_neon: 'ring-2 ring-cyan-400 shadow-[0_0_12px_2px_rgba(34,211,238,0.7)]',
  frame_gold: 'ring-2 ring-yellow-400 shadow-[0_0_14px_3px_rgba(250,204,21,0.7)] animate-pulse',
  frame_ember: 'ring-2 ring-orange-500 shadow-[0_0_16px_4px_rgba(249,115,22,0.7)] animate-pulse',
  frame_prismatic: 'pixel-frame-prismatic',
};

export const PixelAvatar = ({ dataUrl, frame, size = 64, className = '', testId = 'pixel-avatar' }) => {
  const frameClass = frame ? (FRAME_CLASSES[frame] || '') : '';

  if (!dataUrl) {
    return (
      <div
        data-testid={`${testId}-placeholder`}
        className={`bg-surface/60 border border-border/40 rounded-md flex items-center justify-center ${frameClass} ${className}`}
        style={{ width: size, height: size }}
      >
        <Grid3X3 className="text-muted-foreground/50" style={{ width: size * 0.45, height: size * 0.45 }} />
      </div>
    );
  }

  return (
    <img
      data-testid={testId}
      src={dataUrl}
      alt="Pixel avatar"
      className={`rounded-md ${frameClass} ${className}`}
      style={{ width: size, height: size, imageRendering: 'pixelated' }}
    />
  );
};

export default PixelAvatar;
