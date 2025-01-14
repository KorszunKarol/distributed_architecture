import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { NodeData } from '../../hooks/useWebSocket'
import { useEffect } from 'react'

interface Props {
    nodes: Record<string, NodeData>
    connected: boolean
    isMonitoring: boolean
    onStartMonitoring: () => void
    onStopMonitoring: () => void
}

const NodeCard = ({ node }: { node: NodeData }) => {
    console.log('Rendering NodeCard for:', node.node_id, node)
    return (
        <Card className="mb-4">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle>Node {node.node_id}</CardTitle>
                    <Badge variant={node.is_connected ? "success" : "destructive"}>
                        {node.is_connected ? "Connected" : "Disconnected"}
                    </Badge>
                </div>
                <CardDescription>Layer {node.layer}</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-2">
                    <div>
                        <span className="font-medium">Update Count:</span> {node.update_count}
                    </div>
                    <div>
                        <span className="font-medium">Last Sync:</span> {node.last_sync_time || 'Never'}
                    </div>
                    <div>
                        <span className="font-medium">Current Data:</span>
                        <pre className="mt-2 p-2 bg-muted rounded-md text-sm">
                            {JSON.stringify(node.current_data, null, 2)}
                        </pre>
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}

export const RightPanel = ({ nodes, connected, isMonitoring, onStartMonitoring, onStopMonitoring }: Props) => {
    useEffect(() => {
        console.log('RightPanel received nodes:', nodes)
    }, [nodes])

    const sortedNodes = Object.values(nodes).sort((a, b) => {
        if (a.layer !== b.layer) return a.layer - b.layer
        return a.node_id.localeCompare(b.node_id)
    })

    console.log('Sorted nodes:', sortedNodes)

    return (
        <div className="h-full bg-background border-l">
            <div className="border-b p-4">
                <div className="flex items-center justify-between mb-4">
                    <div className="space-y-1">
                        <h2 className="text-2xl font-semibold tracking-tight">Node Monitor</h2>
                        <p className="text-sm text-muted-foreground">
                            Real-time monitoring of distributed nodes
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        {isMonitoring ? (
                            <>
                                <Badge variant={connected ? "success" : "destructive"}>
                                    {connected ? "Connected" : "Disconnected"}
                                </Badge>
                                <Button
                                    variant="destructive"
                                    onClick={onStopMonitoring}
                                >
                                    Stop Monitoring
                                </Button>
                            </>
                        ) : (
                            <Button
                                variant="default"
                                onClick={onStartMonitoring}
                            >
                                Start Monitoring
                            </Button>
                        )}
                    </div>
                </div>
            </div>

            <Tabs defaultValue="status" className="h-[calc(100%-5rem)] flex flex-col">
                <TabsList className="border-b px-4 py-2">
                    <TabsTrigger value="status">Node Status ({sortedNodes.length} nodes)</TabsTrigger>
                    <TabsTrigger value="transactions">Transactions</TabsTrigger>
                </TabsList>

                <TabsContent value="status" className="flex-1">
                    <ScrollArea className="h-full">
                        <div className="p-4">
                            {!isMonitoring ? (
                                <Card>
                                    <CardContent className="pt-6">
                                        Click "Start Monitoring" to begin receiving node updates
                                    </CardContent>
                                </Card>
                            ) : sortedNodes.length === 0 ? (
                                <Card>
                                    <CardContent className="pt-6">
                                        Waiting for node data...
                                    </CardContent>
                                </Card>
                            ) : (
                                sortedNodes.map(node => (
                                    <NodeCard key={node.node_id} node={node} />
                                ))
                            )}
                        </div>
                    </ScrollArea>
                </TabsContent>

                <TabsContent value="transactions" className="flex-1">
                    <ScrollArea className="h-full">
                        <div className="p-4">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Transaction History</CardTitle>
                                    <CardDescription>
                                        Recent transactions in the system
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    Transaction log coming soon...
                                </CardContent>
                            </Card>
                        </div>
                    </ScrollArea>
                </TabsContent>
            </Tabs>
        </div>
    )
}