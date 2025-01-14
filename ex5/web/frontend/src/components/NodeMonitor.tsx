import React, { useEffect, useState } from 'react'

const NodeMonitor: React.FC = () => {
    const [nodes, setNodes] = useState<Record<string, NodeData>>({})

    useEffect(() => {
        console.log('Current nodes state:', nodes)
    }, [nodes])

    return (
        // Rest of the component code
    )
}

export default NodeMonitor