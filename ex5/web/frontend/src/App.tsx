import { NetworkGraph } from './components/NetworkGraph/NetworkGraph'
import { Dashboard } from './components/Dashboard/Dashboard'
import { TransactionLog } from './components/TransactionLog/TransactionLog'
import { RightPanel } from './components/RightPanel/RightPanel'
import { useWebSocket } from './hooks/useWebSocket'
import { NetworkNode, NetworkLink } from './types/node'
import { useMemo } from 'react'
import { DebugPanel } from './components/Debug/DebugPanel'

const NETWORK_LINKS: NetworkLink[] = [
    { source: 'A1', target: 'A2' },
    { source: 'A2', target: 'A3' },
    { source: 'A1', target: 'A3' },
    { source: 'A2', target: 'B1' },
    { source: 'A3', target: 'B2' },
    { source: 'B2', target: 'C1' },
    { source: 'B2', target: 'C2' }
]

export const App = () => {
    const { nodes, connected } = useWebSocket()

    const networkNodes: NetworkNode[] = useMemo(() => {
        return Object.entries(nodes).map(([id, data]) => ({
            id,
            layer: data.layer,
            data
        }))
    }, [nodes])

    return (
        <div className="h-screen w-screen flex flex-col bg-gray-100">
            <nav className="bg-white shadow-lg shrink-0">
                <div className="px-6 py-4">
                    <h1 className="text-2xl font-bold text-gray-800">
                        Distributed System Monitor
                    </h1>
                    <div className={`mt-1 text-sm font-medium ${connected ? 'text-green-600' : 'text-red-600'}`}>
                        {connected ? '● Connected' : '○ Disconnected'}
                    </div>
                </div>
            </nav>

            <main className="flex-1 p-6 min-h-0">
                <div className="flex gap-6 h-full">
                    <div className="w-3/4 h-full">
                        <div className="bg-white rounded-lg shadow-lg w-full h-full">
                            <NetworkGraph
                                nodes={networkNodes}
                                links={NETWORK_LINKS}
                            />
                        </div>
                    </div>
                    <div className="w-1/4 h-full">
                        <RightPanel nodes={nodes} />
                    </div>
                </div>
            </main>
        </div>
    )
}
