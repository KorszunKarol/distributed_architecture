import { NodeData } from '../../types/node'
import { Paper, Title, Text, Group, Stack, Badge, Timeline, Card } from '@mantine/core'

interface Props {
    nodes: Record<string, NodeData>
}

interface VersionEntry {
    timestamp: string
    operation: 'READ' | 'UPDATE'
    key: number
    value: number
    version: number
}

const NodeStatusCard = ({ nodeId, data }: { nodeId: string, data: NodeData }) => {
    const getLayerInfo = (layer: number) => {
        switch(layer) {
            case 0:
                return { color: 'red', label: 'Core', syncInfo: 'Immediate Replication' }
            case 1:
                return {
                    color: 'blue',
                    label: 'Second',
                    syncInfo: `Syncs every 10 updates (${data.last_sync_count}/10)`
                }
            case 2:
                return {
                    color: 'green',
                    label: 'Third',
                    syncInfo: `Syncs every 10s (${Math.round(10 - (Date.now()/1000 - data.last_sync_time))}s remaining)`
                }
        }
    }

    const layerInfo = getLayerInfo(data.layer)

    return (
        <Card withBorder shadow="sm" radius="md" className="mb-4">
            <Group position="apart" mb="xs">
                <Title order={3}>{nodeId}</Title>
                <Badge color={layerInfo.color}>{layerInfo.label} Layer</Badge>
            </Group>

            <Stack spacing="xs">
                <Text size="sm" color="dimmed">{layerInfo.syncInfo}</Text>
                <Text>Updates: {data.update_count}</Text>

                <div className="mt-2">
                    <Text weight={500} size="sm" mb="xs">Current Data:</Text>
                    {data.current_data.map((item) => (
                        <Text key={item.key} size="sm" color="dimmed">
                            Key {item.key}: {item.value} (v{item.version})
                        </Text>
                    ))}
                </div>

                {data.operation_log && (
                    <div className="mt-2">
                        <Text weight={500} size="sm" mb="xs">Recent Operations:</Text>
                        <Timeline bulletSize={24} lineWidth={2}>
                            {data.operation_log.slice(-3).map((op, i) => (
                                <Timeline.Item
                                    key={i}
                                    bullet={op.operation === 'UPDATE' ? '⟳' : '👁️'}
                                    title={op.operation}
                                >
                                    <Text size="xs" mt={4}>
                                        Key {op.key}: {op.operation === 'UPDATE' ? `→ ${op.value} (v${op.version})` : `read v${op.version}`}
                                    </Text>
                                    <Text size="xs" color="dimmed">
                                        {new Date(op.timestamp).toLocaleTimeString()}
                                    </Text>
                                </Timeline.Item>
                            ))}
                        </Timeline>
                    </div>
                )}
            </Stack>
        </Card>
    )
}

export const Dashboard = ({ nodes }: Props) => {
    return (
        <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4 mb-6">
                <Paper p="md" className="bg-red-50">
                    <Title order={4} className="text-red-700">Core Layer</Title>
                    <Text size="sm" className="text-red-600">Active Replication</Text>
                </Paper>
                <Paper p="md" className="bg-blue-50">
                    <Title order={4} className="text-blue-700">Second Layer</Title>
                    <Text size="sm" className="text-blue-600">Lazy (10 updates)</Text>
                </Paper>
                <Paper p="md" className="bg-green-50">
                    <Title order={4} className="text-green-700">Third Layer</Title>
                    <Text size="sm" className="text-green-600">Lazy (10s)</Text>
                </Paper>
            </div>

            {Object.entries(nodes).map(([nodeId, data]) => (
                <NodeStatusCard key={nodeId} nodeId={nodeId} data={data} />
            ))}
        </div>
    )
}