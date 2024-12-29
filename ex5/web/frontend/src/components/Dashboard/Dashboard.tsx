import { NodeData } from '../../types/node'
import { Paper, Title, Text, Group, Stack } from '@mantine/core'

interface Props {
    nodes: Record<string, NodeData>
}

export const Dashboard = ({ nodes }: Props) => {
    const formatTimestamp = (timestamp: number) => {
        const date = new Date(timestamp * 1000)
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        })
    }

    const getVersionDiff = (nodeData: NodeData) => {
        if (!nodeData.current_data.length) return 0
        const latestVersion = Math.max(...nodeData.current_data.map(d => d.version))
        const oldestVersion = Math.min(...nodeData.current_data.map(d => d.version))
        return latestVersion - oldestVersion
    }

    return (
        <div className="space-y-4">
            {/* Layer Status Overview */}
            <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="p-4 bg-red-50 rounded-lg">
                    <h3 className="font-semibold text-red-700">Core Layer</h3>
                    <p className="text-sm text-red-600">Active Replication</p>
                </div>
                <div className="p-4 bg-blue-50 rounded-lg">
                    <h3 className="font-semibold text-blue-700">Second Layer</h3>
                    <p className="text-sm text-blue-600">Lazy (10 updates)</p>
                </div>
                <div className="p-4 bg-green-50 rounded-lg">
                    <h3 className="font-semibold text-green-700">Third Layer</h3>
                    <p className="text-sm text-green-600">Lazy (10s)</p>
                </div>
            </div>

            {/* Node Details */}
            {Object.entries(nodes).map(([nodeId, data]) => (
                <div key={nodeId} className="p-4 bg-white rounded-lg border border-gray-200">
                    <div className="flex items-center justify-between mb-2">
                        <h3 className="text-lg font-medium text-gray-800">{nodeId}</h3>
                        <span className={`px-2 py-1 rounded-full text-xs ${
                            data.layer === 0 ? 'bg-red-100 text-red-800' :
                            data.layer === 1 ? 'bg-blue-100 text-blue-800' :
                            'bg-green-100 text-green-800'
                        }`}>
                            Layer {data.layer}
                        </span>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mt-4 text-sm">
                        <div className="bg-gray-50 p-3 rounded">
                            <p className="text-gray-500 mb-1">Updates</p>
                            <p className="font-medium text-gray-900">{data.update_count}</p>
                        </div>
                        <div className="bg-gray-50 p-3 rounded">
                            <p className="text-gray-500 mb-1">Data Items</p>
                            <p className="font-medium text-gray-900">{data.current_data.length}</p>
                        </div>
                        <div className="bg-gray-50 p-3 rounded">
                            <p className="text-gray-500 mb-1">Version Range</p>
                            <p className="font-medium text-gray-900">{getVersionDiff(data)}</p>
                        </div>
                        <div className="bg-gray-50 p-3 rounded">
                            <p className="text-gray-500 mb-1">Last Update</p>
                            <p className="font-medium text-gray-900">{formatTimestamp(data.last_update)}</p>
                        </div>
                    </div>

                    {/* Latest Updates */}
                    <div className="mt-4 bg-gray-50 p-3 rounded">
                        <p className="text-gray-500 mb-2">Latest Data</p>
                        <div className="space-y-1 max-h-32 overflow-auto">
                            {data.current_data.slice(-3).reverse().map((item, idx) => (
                                <div key={idx} className="text-xs text-gray-600 flex justify-between">
                                    <span>Key {item.key} = {item.value}</span>
                                    <span>v{item.version}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            ))}
        </div>
    )
}