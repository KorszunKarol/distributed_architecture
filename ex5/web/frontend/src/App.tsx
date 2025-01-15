import { useWebSocket } from './hooks/useWebSocket'
import { NodeCard } from './components/NodeCard'

export const App = () => {
  const { nodes, connected, connect, disconnect } = useWebSocket()

  // Group nodes by layer, with null check
  const nodesByLayer = Object.values(nodes || {}).reduce((acc, node) => {
    if (!node || !node.node_id) return acc
    const layer = node.node_id.charAt(0) === 'A' ? 0 : node.node_id.charAt(0) === 'B' ? 1 : 2
    if (!acc[layer]) acc[layer] = []
    acc[layer].push(node)
    return acc
  }, {} as Record<number, typeof nodes[keyof typeof nodes][]>)

  // Check if any nodes exist, with null check
  const hasNodes = nodes && Object.keys(nodes).length > 0

  const handleMonitoringAction = () => {
    if (connected) {
      disconnect()
    } else {
      connect()
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-gray-200">Distributed System Monitor</h1>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 rounded-full bg-[#1a1a1a] px-3 py-1.5">
              <span className={`h-2 w-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-sm text-gray-300">{connected ? 'Connected' : 'Disconnected'}</span>
            </div>
            <button
              onClick={handleMonitoringAction}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors duration-200 border ${
                connected
                  ? 'bg-red-500/10 text-red-400 hover:bg-red-500/20 border-red-500/20'
                  : 'bg-green-500/10 text-green-400 hover:bg-green-500/20 border-green-500/20'
              }`}
            >
              {connected ? 'Stop Monitoring' : 'Start Monitoring'}
            </button>
          </div>
        </div>

        {hasNodes ? (
          <div className="space-y-8">
            {[0, 1, 2].map((layer) => (
              nodesByLayer[layer] && nodesByLayer[layer].length > 0 && (
                <div key={layer}>
                  <h2 className="mb-4 text-lg font-medium text-gray-300">Layer {layer}</h2>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {nodesByLayer[layer].map((node) => (
                      <NodeCard key={node.node_id} node={node} />
                    ))}
                  </div>
                </div>
              )
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center h-[60vh]">
            <div className="text-gray-500 text-center">
              <p className="text-lg">No nodes connected</p>
              <p className="text-sm mt-2">Waiting for connections...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
