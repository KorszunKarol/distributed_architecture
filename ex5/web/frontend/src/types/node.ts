export interface NodeData {
    node_id: string
    layer: number
    update_count: number
    last_sync_time: number
    last_sync_count: number
    current_data: Array<{
        key: number
        value: number
        version: number
        timestamp: number
    }>
    operation_log: Array<{
        timestamp: string
        operation: 'READ' | 'UPDATE'
        key: number
        value: number
        version: number
    }>
}

export interface NetworkNode {
    id: string
    layer: number
    data: NodeData
}

export interface NetworkLink {
    source: string
    target: string
}