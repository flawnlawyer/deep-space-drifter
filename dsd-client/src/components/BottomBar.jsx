import { useStore } from '../store'

export default function BottomBar() {
  const { lastEpoch, satellites } = useStore()

  return (
    <footer className="absolute bottom-0 left-0 right-0 z-10 flex items-center justify-between
                       px-5 py-2 bg-gradient-to-t from-[#040a14f5] to-transparent
                       font-mono text-[10px] text-dim">
      <div className="flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-[#20c080] animate-pulse inline-block" />
        Live · updates every 10s
      </div>

      <div className="text-accent tracking-wider">
        {lastEpoch ?? '—'}
      </div>

      <div>v1.0 · Deep Space Drifter</div>
    </footer>
  )
}
