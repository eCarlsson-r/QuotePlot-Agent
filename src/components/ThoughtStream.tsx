import { memo, useEffect, useState, useRef } from 'react';
import Typewriter from './Typewriter';
import { Insight, Stats } from '@/types/market';

interface ThoughtStreamProps {
    logs: string[];
    selectedSymbol: string;
    setLogs: React.Dispatch<React.SetStateAction<string[]>>;
    setInsight: (insight: Insight) => void;
    setStats: (stats: Stats) => void;
    setThemeMode: React.Dispatch<React.SetStateAction<'normal' | 'volatile'>>;
}
const ThoughtStream = ({logs, selectedSymbol, setLogs, setInsight, setStats, setThemeMode}: ThoughtStreamProps) => {
    const masterLogsRef = useRef<Record<string, string[]>>({});
    const scrollRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);

    const [visibleLogs, setVisibleLogs] = useState<string[]>([]);
    const queueRef = useRef<string[]>([]);
    const [isTyping, setIsTyping] = useState(false);
    
    const [status, setStatus] = useState<'online' | 'offline' | 'connecting'>('connecting');

    const getStatusColor = () => {
        if (status === 'online') return '#00ff41';
        if (status === 'connecting') return '#ffcc00';
        return '#ff3b30';
    };

    const getLogStyle = (content: string) => {
        if (content.startsWith("[ERROR]")) return { color: "#ff3b30", fontWeight: "bold" as const };
        if (content.startsWith("[SUCCESS]")) return { color: "#00ff41" };
        if (content.startsWith("[WARN]")) return { color: "#ffcc00" };
        return { color: "#00d4ff" };
    };

    const processQueue = () => {
        if (queueRef.current.length > 0) {
            const nextLog = queueRef.current.shift(); // Remove first item
            if (nextLog) {
                setLogs(prev => [...prev.slice(-19), nextLog]);
                setIsTyping(true);
            }
        } else {
            setIsTyping(false);
        }
    };

    useEffect(() => {
        setTimeout(() => {
            const history = masterLogsRef.current[selectedSymbol] || [];
            setVisibleLogs(history.slice(-20)); // Show last 20 recorded logs
            queueRef.current = []; // Clear any pending typewriter animations from old symbol
            setIsTyping(false);
        }, 0);
    }, [selectedSymbol]);

    useEffect(() => {
        if (wsRef.current) return;

        const ws = new WebSocket(process.env.NEXT_PUBLIC_WS_URL+"/ws/thoughts");
        wsRef.current = ws;

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(JSON.parse(event.data).content);

                // 2. Safely update Parent (Dashboard) asynchronously
                setTimeout(() => {
                    if (data.type === "insight_update" && data.symbol === selectedSymbol) {
                        setInsight(data);
                        setThemeMode(data.prediction === "Bearish" && data.probability > 0.85 ? 'volatile' : 'normal');
                    } else if (data.type === "agent_stats" && data.symbol === selectedSymbol) {
                        setStats(data);
                    }
                }, 0);

                if (data.type === "insight_update") {
                    const symbol = data.symbol;
                    const text = data.insight_text;

                    // ALWAYS store in master cache (background task)
                    if (!masterLogsRef.current[symbol]) masterLogsRef.current[symbol] = [];
                    masterLogsRef.current[symbol].push(text);
                    if (masterLogsRef.current[symbol].length > 50) masterLogsRef.current[symbol].shift();

                    if (symbol === selectedSymbol) {
                        // Push to the Ref queue (doesn't trigger render)
                        queueRef.current.push(text);
                        // If Lucy is idle, kickstart the typing
                        setIsTyping(currentlyTyping => {
                            if (!currentlyTyping) {
                                processQueue();
                                return true;
                            }
                            return true;
                        });
                    }
                } else {
                    const newLog = data.content;

                    // Push to the Ref queue (doesn't trigger render)
                    queueRef.current.push(newLog);
                    
                    // If Lucy is idle, kickstart the typing
                    setIsTyping(currentlyTyping => {
                        if (!currentlyTyping) {
                            processQueue();
                            return true;
                        }
                        return true;
                    });
                }
            } catch (e) { console.error("WS Error:", e); }
        };

        // Cleanup: Use a small timeout to allow remounting without closing
        return () => {
            setTimeout(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.close();
                    wsRef.current = null;
                }
            }, 100);
        };
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
            {visibleLogs.map((log, i) => (
                <div key={`${i}-${log.substring(0, 5)}`} style={getLogStyle(log)} className="mb-1">
                    <span className="opacity-50 mr-2">{">"}</span>
                    {/* Only the NEWEST log gets the typewriter effect if you want, 
                        or apply to all for a cool cascading effect */}
                    <Typewriter text={log.replace(/\[.*?\] /, "")} delay={15} onComplete={i === logs.length - 1 ? processQueue : undefined} />
                </div>
            ))}
            <div ref={scrollRef} />
        </div>
    );
};

export default memo(ThoughtStream);