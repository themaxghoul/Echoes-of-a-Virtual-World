import { useEffect, useState } from 'react';
import { Database, HardDrive } from 'lucide-react';
import { getDiagnostics, isDesktop } from '@/lib/desktopStorage';

export default function DesktopDiagnostics() {
  const [details, setDetails] = useState(null);

  useEffect(() => {
    getDiagnostics().then(setDetails).catch(() => setDetails({ appVersion: 'unavailable', platform: 'unknown', namespaces: {} }));
  }, []);

  if (!details) return null;
  const world = details.namespaces?.world;
  const jarvis = details.namespaces?.jarvis;

  return (
    <section className="desktop-diagnostics">
      <div><HardDrive size={14} /><strong>{isDesktop() ? 'DESKTOP' : 'BROWSER FALLBACK'}</strong><span>v{details.appVersion}</span></div>
      <p><Database size={12} /> world r{world?.revision || 0} / Jarvis r{jarvis?.revision || 0}</p>
      {(world?.recovered || jarvis?.recovered) && <small>Recovered from a known-good backup.</small>}
    </section>
  );
}
