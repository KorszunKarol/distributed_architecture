import { useEffect } from 'react'
import { AppShell, Group, Title, Button, Stack, Paper, Text, Badge } from '@mantine/core'
import { IconPlayCircle, IconStopCircle } from '@tabler/icons-react'
import { useWebSocket } from './hooks/useWebSocket'
import { NodeCard } from './components/NodeCard'

export function App() {
  const { nodes, connected, isMonitoring, connect, disconnect } = useWebSocket()

  useEffect(() => {
    console.log('WebSocket connection state:', { connected, isMonitoring })
  }, [connected, isMonitoring])

  // Group nodes by layer
  const nodesByLayer = Object.values(nodes).reduce((acc, node) => {
    const layer = `Layer ${node.layer}`
    if (!acc[layer]) acc[layer] = []
    acc[layer].push(node)
    return acc
  }, {} as Record<string, typeof nodes[keyof typeof nodes][]>)

  return (
    <AppShell
      padding="md"
      header={{ height: 60 }}
    >
      <AppShell.Header>
        <Group justify="space-between" h="100%" px="md">
          <Title order={3}>Distributed System Monitor</Title>
          <Group>
            <Badge
              color={connected ? 'green' : 'red'}
              variant="dot"
            >
              {connected ? 'Connected' : 'Disconnected'}
            </Badge>
            <Button
              leftSection={isMonitoring ? <IconStopCircle /> : <IconPlayCircle />}
              onClick={isMonitoring ? disconnect : connect}
              color={isMonitoring ? 'red' : 'blue'}
            >
              {isMonitoring ? 'Stop Monitoring' : 'Start Monitoring'}
            </Button>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Main>
        <Stack gap="md">
          {Object.entries(nodesByLayer).map(([layer, layerNodes]) => (
            <Paper key={layer} shadow="sm" p="md">
              <Stack gap="sm">
                <Title order={4}>{layer}</Title>
                <Group grow>
                  {layerNodes.map(node => (
                    <NodeCard key={node.node_id} node={node} />
                  ))}
                </Group>
              </Stack>
            </Paper>
          ))}
        </Stack>
      </AppShell.Main>
    </AppShell>
  )
}
