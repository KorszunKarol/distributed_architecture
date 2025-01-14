import { Card, Text, Group, Badge, Stack, Progress } from '@mantine/core'
import { NodeData } from '../hooks/useWebSocket'

interface NodeCardProps {
  node: NodeData
}

export function NodeCard({ node }: NodeCardProps) {
  const dataCount = Object.keys(node.current_data).length

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Stack gap="xs">
        <Group justify="space-between">
          <Text fw={500}>{node.node_id}</Text>
          <Badge
            color={node.is_connected ? 'green' : 'red'}
            variant="light"
          >
            {node.is_connected ? 'Active' : 'Inactive'}
          </Badge>
        </Group>

        <Text size="sm" c="dimmed">
          Updates: {node.update_count}
        </Text>

        <Text size="sm" c="dimmed">
          Data Items: {dataCount}
        </Text>

        {node.last_sync_time && (
          <Text size="sm" c="dimmed">
            Last Sync: {new Date(node.last_sync_time).toLocaleTimeString()}
          </Text>
        )}

        <Progress
          value={(node.update_count / 100) * 100}
          color={node.is_connected ? 'blue' : 'gray'}
        />

        <Stack gap={2}>
          {Object.entries(node.current_data).slice(0, 3).map(([key, value]) => (
            <Text key={key} size="xs" c="dimmed">
              {key}: {value}
            </Text>
          ))}
          {dataCount > 3 && (
            <Text size="xs" c="dimmed">
              +{dataCount - 3} more items...
            </Text>
          )}
        </Stack>
      </Stack>
    </Card>
  )
}