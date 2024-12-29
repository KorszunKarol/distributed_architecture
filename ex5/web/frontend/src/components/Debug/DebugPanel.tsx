import { NodeData } from '../../types/node'

interface Props {
    nodes: Record<string, NodeData>
    connected: boolean
}

export const DebugPanel = ({ nodes, connected }: Props) => {
    return (
        <div className="fixed bottom-4 right-4 p-4 bg-black/80 text-white rounded-lg max-w-lg max-h-96 overflow-auto">
            <h3 className="text-sm font-bold mb-2">Debug Info</h3>
            <div className="text-xs">
                <p>WebSocket: {connected ? '🟢 Connected' : '🔴 Disconnected'}</p>
                <p>Nodes: {Object.keys(nodes).length}</p>
                <pre className="mt-2 text-xs">
                    {JSON.stringify(nodes, null, 2)}
                </pre>
            </div>
        </div>
    )
}