import { memo, useEffect, useState, useRef } from 'react';
import Typewriter from './Typewriter';

const ThoughtStream = () => {
    const [logs, setLogs] = useState<string[]>([]);
    const scrollRef = useRef<HTMLDivElement>(null);
    
    const [status, setStatus] = useState<'online' | 'offline' | 'connecting'>('connecting');

    const getStatusColor = () => {
        if (status === 'online') return '#00ff41';
        if (status === 'connecting') return '#ffcc00';
        return '#ff3b30';
    };

    const getLogStyle = (content: string) => {
        if (content.startsWith("[ERROR]")) return { color: "#ff4d4d", fontWeight: "bold" as const };
        if (content.startsWith("[SUCCESS]")) return { color: "#00ff41" };
        if (content.startsWith("[WARN]")) return { color: "#ffcc00" };
        return { color: "#00d4ff" };
    };

    useEffect(() => {
        const ws = new WebSocket("ws://localhost:8000/ws/thoughts");

        ws.onopen = () => setStatus('online');
        ws.onclose = () => setStatus('offline');
        ws.onerror = () => setStatus('offline');

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                // Ensure data.content exists before adding
                if (data.content) {
                    setLogs((prev) => [...prev.slice(-19), data.content]);
                }
            } catch (e) {
                console.error(e);
            }
        };

        return () => ws.close();
    }, []);

    useEffect(() => {
        // scrollIntoView now exists because we typed the Ref
        scrollRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [logs]);

    return (
        <div className="thought-stream p-4 rounded-lg overflow-y-auto max-h-[300px] font-mono text-[11px] leading-tight">
            {/* Header / Heartbeat */}
            <div className="flex items-center justify-between mb-3 border-b border-[#00ff41]/30 pb-2">
                <span className="font-bold tracking-tighter">LUCY_CORE_LOGS</span>
                <div className="flex items-center gap-2">
                    <span className="text-[9px] opacity-70">{status.toUpperCase()}</span>
                    <div style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        backgroundColor: getStatusColor(),
                        boxShadow: `0 0 8px ${getStatusColor()}`
                    }} className="animate-pulse" />
                </div>
            </div>

            {/* Log Feed */}
            {logs.map((log, i) => (
                <div key={`${i}-${log.substring(0, 5)}`} style={getLogStyle(log)} className="mb-1">
                    <span className="opacity-50 mr-2">{">"}</span>
                    {/* Only the NEWEST log gets the typewriter effect if you want, 
                        or apply to all for a cool cascading effect */}
                    <Typewriter text={log.replace(/\[.*?\] /, "")} delay={15} />
                </div>
            ))}
            <div ref={scrollRef} />
        </div>
    );
};

export default memo(ThoughtStream);