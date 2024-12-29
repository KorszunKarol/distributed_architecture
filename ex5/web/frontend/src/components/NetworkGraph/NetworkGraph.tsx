import { useEffect, useRef, useMemo } from 'react'
import { Chart as ChartJS } from 'chart.js'
import { NetworkNode, NetworkLink } from '../../types/node'

interface Props {
    nodes: NetworkNode[]
    links: NetworkLink[]
}

export const NetworkGraph = ({ nodes, links }: Props) => {
    const chartRef = useRef<HTMLCanvasElement>(null)
    const animationFrameId = useRef<number>()
    const lastUpdateTime = useRef<Record<string, number>>({})
    const mousePos = useRef<{x: number, y: number} | null>(null)

    const calculateNodePositions = (width: number, height: number) => {
        const margin = 100
        const layerSpacing = (height - 2 * margin) / 2

        return {
            A1: { x: width / 2, y: margin },
            A2: { x: width / 3, y: margin + 80 },
            A3: { x: (2 * width) / 3, y: margin + 80 },
            B1: { x: width / 3, y: margin + layerSpacing },
            B2: { x: (2 * width) / 3, y: margin + layerSpacing },
            C1: { x: (width * 0.4), y: height - margin },
            C2: { x: (width * 0.6), y: height - margin }
        }
    }

    const drawNode = (ctx: CanvasRenderingContext2D, node: NetworkNode, pos: {x: number, y: number}, hovered: boolean) => {
        const now = Date.now()
        const lastUpdate = lastUpdateTime.current[node.id] || 0
        const timeSinceUpdate = now - lastUpdate

        const pulseScale = timeSinceUpdate < 1000 ?
            1 + (Math.sin(timeSinceUpdate / 100) * 0.2) : 1

        const baseRadius = 25 * pulseScale

        // Draw node circle
        ctx.beginPath()
        ctx.arc(pos.x, pos.y, baseRadius, 0, Math.PI * 2)

        // Color based on layer with lighter opacity
        ctx.fillStyle = node.layer === 0 ? 'rgba(255, 182, 182, 0.8)' :    // Light red
                       node.layer === 1 ? 'rgba(182, 182, 255, 0.8)' :    // Light blue
                       'rgba(182, 255, 182, 0.8)'                         // Light green
        ctx.fill()

        // Node border
        ctx.strokeStyle = node.layer === 0 ? 'rgba(255, 0, 0, 0.8)' :    // Red
                         node.layer === 1 ? 'rgba(0, 0, 255, 0.8)' :    // Blue
                         'rgba(0, 255, 0, 0.8)'                         // Green
        ctx.lineWidth = 2
        ctx.stroke()

        ctx.font = 'bold 16px Arial'
        ctx.fillStyle = '#000000'
        ctx.textAlign = 'center'
        ctx.fillText(node.id, pos.x, pos.y - baseRadius - 10)

        ctx.font = '14px Arial'
        ctx.fillStyle = '#666666'
        ctx.fillText(`${node.data.update_count} updates`, pos.x, pos.y + baseRadius + 15)
    }

    const drawLink = (ctx: CanvasRenderingContext2D, from: {x: number, y: number}, to: {x: number, y: number}, active: boolean) => {
        ctx.beginPath()
        ctx.moveTo(from.x, from.y)
        ctx.lineTo(to.x, to.y)

        ctx.strokeStyle = 'rgba(0, 0, 255, 0.4)'
        ctx.lineWidth = 1.5
        ctx.setLineDash([5, 5])

        if (active) {
            ctx.strokeStyle = 'rgba(0, 0, 255, 0.8)'
            const dashOffset = (Date.now() / 100) % 16
            ctx.lineDashOffset = -dashOffset
        }

        ctx.stroke()
        ctx.setLineDash([])
    }

    const handleMouseMove = (event: React.MouseEvent<HTMLCanvasElement>) => {
        const canvas = chartRef.current
        if (!canvas) return

        const rect = canvas.getBoundingClientRect()
        mousePos.current = {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top
        }
    }

    const handleMouseLeave = () => {
        mousePos.current = null
    }

    const isNodeHovered = (nodePos: {x: number, y: number}, radius: number) => {
        if (!mousePos.current) return false
        const dx = nodePos.x - mousePos.current.x
        const dy = nodePos.y - mousePos.current.y
        return Math.sqrt(dx * dx + dy * dy) < radius
    }

    const animate = () => {
        const canvas = chartRef.current
        if (!canvas) return

        const ctx = canvas.getContext('2d')
        if (!ctx) return

        const width = canvas.width
        const height = canvas.height
        const nodePositions = calculateNodePositions(width, height)

        ctx.clearRect(0, 0, width, height)

        links.forEach(link => {
            const from = nodePositions[link.source]
            const to = nodePositions[link.target]
            const active = nodes.find(n => n.id === link.source)?.data.update_count !==
                          nodes.find(n => n.id === link.target)?.data.update_count
            drawLink(ctx, from, to, active)
        })

        // Draw nodes
        nodes.forEach(node => {
            const pos = nodePositions[node.id]
            const hovered = isNodeHovered(pos, 20)
            drawNode(ctx, node, pos, hovered)
        })

        animationFrameId.current = requestAnimationFrame(animate)
    }

    useEffect(() => {
        if (!chartRef.current || !nodes.length) return

        const resizeCanvas = () => {
            const canvas = chartRef.current
            if (!canvas) return

            const container = canvas.parentElement
            if (!container) return

            canvas.width = container.clientWidth
            canvas.height = container.clientHeight

            animate()
        }

        resizeCanvas()

        window.addEventListener('resize', resizeCanvas)

        return () => {
            window.removeEventListener('resize', resizeCanvas)
            if (animationFrameId.current) {
                cancelAnimationFrame(animationFrameId.current)
            }
        }
    }, [nodes, links])

    return (
        <div className="w-full h-full">
            <canvas
                ref={chartRef}
                className="w-full h-full"
                onMouseMove={handleMouseMove}
                onMouseLeave={handleMouseLeave}
                style={{ display: 'block' }}
            />
        </div>
    )
}