export interface NodeData {
    node_id: string
    layer: number
    update_count: number
    current_data: Array<{
        key: number
        value: number
        version: number
        timestamp: number
    }>
    last_update: number
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