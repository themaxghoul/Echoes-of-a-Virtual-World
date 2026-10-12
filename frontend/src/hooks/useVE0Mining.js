// Passive VE0 mining: XR presence + spatial work telemetry.
// Drop into any in-world page — counts keystrokes/clicks as movement/interaction
// proxies and ticks the hybrid economy every 60s. Silent on failure.
import { useEffect, useRef } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function useVE0Mining(active = true) {
  const counts = useRef({ movements: 0, interactions: 0 });

  useEffect(() => {
    if (!active) return undefined;
    const userId = localStorage.getItem('userId');
    if (!userId) return undefined;

    const onKey = () => { counts.current.movements += 1; };
    const onPointer = () => { counts.current.interactions += 1; };
    window.addEventListener('keydown', onKey);
    window.addEventListener('pointerdown', onPointer);

    const sendTick = async () => {
      const { movements, interactions } = counts.current;
      counts.current = { movements: 0, interactions: 0 };
      try {
        await axios.post(`${API}/hybrid-economy/presence/tick`, {
          entity_id: userId,
          seconds: 60,
          movements: Math.min(movements, 240),
          interactions: Math.min(interactions, 120),
        });
      } catch {
        // silent — mining must never break gameplay
      }
    };

    const interval = setInterval(sendTick, 60000);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('pointerdown', onPointer);
      clearInterval(interval);
    };
  }, [active]);
}
