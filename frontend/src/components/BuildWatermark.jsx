import buildInfo from '@/buildInfo.json';

export default function BuildWatermark() {
  return <p className="mt-5 font-mono text-[10px] tracking-widest text-muted-foreground/50">EOV {buildInfo.version} · {buildInfo.name}</p>;
}
