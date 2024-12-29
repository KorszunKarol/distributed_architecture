import { useEffect, useState, useCallback, useRef } from 'react'
import { NodeData } from '../types/node'

export const useWebSocket = () => {
    const [nodes, setNodes] = useState<Record<string, NodeData>>({})
    const [connected, setConnected] = useState(false)
    const lastUpdateTime = useRef<number>(0)
    const THROTTLE_MS = 1000 // Update max once per second

    const connect = useCallback(() => {
        const ws = new WebSocket('ws://localhost:8000/ws')

        ws.onopen = () => {
            setConnected(true)
        }

        ws.onmessage = (event) => {
            const now = Date.now()
            if (now - lastUpdateTime.current < THROTTLE_MS) {
                return
            }

            try {
                const data = JSON.parse(event.data)
                if (data.nodes) {
                    setNodes(data.nodes)
                    lastUpdateTime.current = now
                }
            } catch (error) {
                console.error('Error parsing WebSocket message:', error)
            }
        }

        ws.onclose = () => {
            setConnected(false)
            setTimeout(connect, 1000)
        }

        ws.onerror = () => {
            ws.close()
        }

        return ws
    }, [])

    useEffect(() => {
        const ws = connect()
        return () => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.close()
            }
        }
    }, [connect])

    return { nodes, connected }
}