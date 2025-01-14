import { useEffect, useState, useCallback, useRef } from 'react'

export interface NodeData {
    node_id: string
    layer: number
    timestamp: string
    is_connected: boolean
    last_sync_time: string | null
    update_count: number
    current_data: Record<string, string>
}

export const useWebSocket = () => {
    const [nodes, setNodes] = useState<Record<string, NodeData>>({})
    const [connected, setConnected] = useState(false)
    const [isMonitoring, setIsMonitoring] = useState(false)
    const wsRef = useRef<WebSocket | null>(null)
    const reconnectTimeoutRef = useRef<number>()

    const disconnect = useCallback(() => {
        console.log('Disconnecting WebSocket monitor')
        if (wsRef.current) {
            wsRef.current.close()
            wsRef.current = null
        }
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current)
            reconnectTimeoutRef.current = undefined
        }
        setConnected(false)
        setIsMonitoring(false)
        setNodes({})
    }, [])

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            console.log('WebSocket monitor already connected')
            setIsMonitoring(true)
            return
        }

        if (wsRef.current?.readyState === WebSocket.CONNECTING) {
            console.log('WebSocket monitor already connecting')
            setIsMonitoring(true)
            return
        }

        console.log('Connecting WebSocket monitor...')
        const ws = new WebSocket('ws://localhost:8000/ws')
        wsRef.current = ws

        ws.onopen = () => {
            console.log('WebSocket monitor connected successfully')
            setConnected(true)
            setIsMonitoring(true)
            ws.send(JSON.stringify({ type: 'monitor' }))
        }

        ws.onmessage = (event) => {
            try {
                console.log('Received raw message:', event.data)
                const data: NodeData = JSON.parse(event.data)
                console.log(`Received update for node ${data.node_id}:`, data)
                setNodes(prev => {
                    const newNodes = {
                        ...prev,
                        [data.node_id]: data
                    }
                    console.log('Updated nodes state:', newNodes)
                    return newNodes
                })
            } catch (error) {
                console.error('Error parsing WebSocket message:', error)
                console.error('Raw message:', event.data)
            }
        }

        ws.onerror = (error) => {
            console.error('WebSocket monitor error:', error)
            setConnected(false)
            setIsMonitoring(false)
        }

        ws.onclose = (event) => {
            console.log(`WebSocket monitor disconnected: ${event.code} ${event.reason}`)
            setConnected(false)
            setIsMonitoring(false)
            // Optional: Implement reconnection logic here
        }
    }, [isMonitoring])

    useEffect(() => {
        return () => {
            disconnect()
        }
    }, [disconnect])

    return {
        nodes,
        connected,
        isMonitoring,
        connect,
        disconnect
    }
}