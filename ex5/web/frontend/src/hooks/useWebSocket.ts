import { useEffect, useState, useRef, useCallback } from 'react'

export interface NodeData {
  node_id: string
  is_connected: boolean
  current_data: Record<string, any>
  update_count: number
  last_sync_time?: string
}

export function useWebSocket() {
  const [nodes, setNodes] = useState<Record<string, NodeData>>({})
  const [connected, setConnected] = useState(false)
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimeout = useRef<number>()

  const connect = useCallback(() => {
    try {
      // Clear any existing connection
      if (ws.current) {
        ws.current.close()
        ws.current = null
      }

      // Clear any existing timeout
      if (reconnectTimeout.current) {
        window.clearTimeout(reconnectTimeout.current)
      }

      ws.current = new WebSocket('ws://localhost:8000/ws')

      ws.current.onopen = () => {
        console.log('WebSocket connected')
        setConnected(true)
        ws.current?.send(JSON.stringify({ type: 'monitor' }))
      }

      ws.current.onclose = () => {
        console.log('WebSocket closed')
        setConnected(false)
        setNodes({})
      }

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        if (ws.current) {
          ws.current.close()
        }
      }

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('Received data:', data) // Debug log
          if (typeof data === 'object' && data !== null) {
            setNodes(data)
          }
        } catch (error) {
          console.error('Error parsing message:', error)
        }
      }
    } catch (error) {
      console.error('Error creating WebSocket:', error)
      setConnected(false)
    }
  }, [])

  const disconnect = useCallback(() => {
    // Clear any reconnection timeout
    if (reconnectTimeout.current) {
      window.clearTimeout(reconnectTimeout.current)
    }

    if (ws.current) {
      ws.current.close()
      ws.current = null
      setConnected(false)
      setNodes({})
    }
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeout.current) {
        window.clearTimeout(reconnectTimeout.current)
      }
      if (ws.current) {
        ws.current.close()
      }
    }
  }, [])

  return { nodes, connected, connect, disconnect }
}