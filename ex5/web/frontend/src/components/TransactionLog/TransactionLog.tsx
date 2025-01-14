import { Card, Title, Text, Timeline, Badge, Group } from '@mantine/core'
import { NodeData } from '../../types/node'

interface Props {
    nodes: Record<string, NodeData>
}

interface Transaction {
    timestamp: string
    command: string
    status: 'success' | 'failed'
    error?: string
    targetLayer?: number
}

export const TransactionLog = ({ nodes }: Props) => {
    const recentTransactions: Transaction[] = [
        {
            timestamp: new Date().toISOString(),
            command: 'b0, r(1), r(2), c',
            status: 'success',
            targetLayer: 0
        },
        {
            timestamp: new Date().toISOString(),
            command: 'b, r(1), w(2,200), c',
            status: 'success'
        },
        {
            timestamp: new Date().toISOString(),
            command: 'b2, r(1), r(2), c',
            status: 'failed',
            error: 'Invalid layer',
            targetLayer: 2
        }
    ]

    return (
        <Card withBorder shadow="sm" radius="md">
            <Title order={3} mb="md">Transaction Log</Title>

            <Timeline bulletSize={24} lineWidth={2}>
                {recentTransactions.map((tx, i) => (
                    <Timeline.Item
                        key={i}
                        bullet={tx.status === 'success' ? '✓' : '✗'}
                        title={
                            <Group spacing="xs">
                                <Text size="sm" weight={500}>{tx.command}</Text>
                                <Badge
                                    color={tx.status === 'success' ? 'green' : 'red'}
                                    size="sm"
                                >
                                    {tx.status}
                                </Badge>
                            </Group>
                        }
                    >
                        {tx.targetLayer !== undefined && (
                            <Text size="xs" color="dimmed">Target Layer: {tx.targetLayer}</Text>
                        )}
                        {tx.error && (
                            <Text size="xs" color="red">{tx.error}</Text>
                        )}
                        <Text size="xs" color="dimmed">
                            {new Date(tx.timestamp).toLocaleTimeString()}
                        </Text>
                    </Timeline.Item>
                ))}
            </Timeline>
        </Card>
    )
}