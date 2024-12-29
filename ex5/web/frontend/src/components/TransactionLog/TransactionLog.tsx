import { NodeData } from '../../types/node'
import { Paper, Title, Text, Stack, ScrollArea } from '@mantine/core'

interface Props {
    nodes: Record<string, NodeData>
}

export const TransactionLog = ({ nodes }: Props) => {
    return (
        <div className="space-y-2">
            {Object.entries(nodes).map(([nodeId, data]) =>
                data.current_data.map((item, idx) => (
                    <div key={`${nodeId}-${idx}`} className="text-sm text-gray-600 p-2 bg-gray-50 rounded">
                        {nodeId}: Key {item.key} = {item.value} (v{item.version})
                    </div>
                ))
            )}
        </div>
    )
}