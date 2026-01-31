import React, { useState, useEffect, useRef, useCallback } from 'react'
import { 
  Network, 
  Filter, 
  ZoomIn, 
  ZoomOut, 
  Download, 
  Settings, 
  Search,
  Eye,
  EyeOff,
  Maximize2,
  Minimize2,
  RefreshCw,
  Info,
  X,
  AlertCircle,
  HelpCircle
} from 'lucide-react'
import { KnowledgeGraphData, KnowledgeGraphNode, KnowledgeGraphEdge } from '../types'
import { getKnowledgeGraph, getNodeDetails } from '../services/api'
import apiService from '../services/api'

// D3.js-like force simulation for node positioning (simplified)
interface Position {
  x: number
  y: number
}

interface SimulationNode extends KnowledgeGraphNode {
  x: number
  y: number
  vx: number
  vy: number
  fx?: number
  fy?: number
}

interface SimulationEdge extends Omit<KnowledgeGraphEdge, 'source' | 'target'> {
  source: SimulationNode
  target: SimulationNode
  color: string // Add color property for dynamic edge coloring
}

const KnowledgeGraph = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [graphData, setGraphData] = useState<KnowledgeGraphData | null>(null)
  const [simulationNodes, setSimulationNodes] = useState<SimulationNode[]>([])
  const [simulationEdges, setSimulationEdges] = useState<SimulationEdge[]>([])
  const [selectedNode, setSelectedNode] = useState<SimulationNode | null>(null)
  const [hoveredNode, setHoveredNode] = useState<SimulationNode | null>(null)
  const [filters, setFilters] = useState({
    nodeTypes: ['concept', 'organization', 'technology'],
    edgeTypes: ['is-a', 'part-of', 'related-to'],
    minConnections: 1
  })
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showLegend, setShowLegend] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [showHelp, setShowHelp] = useState(false)
  const [isPanning, setIsPanning] = useState(false)
  const [panStart, setPanStart] = useState<{ x: number; y: number; origX: number; origY: number } | null>(null)

  // Add taxonomy state
  const [taxonomyNodes, setTaxonomyNodes] = useState<any[]>([])
  const [taxonomyEdges, setTaxonomyEdges] = useState<any[]>([])
  const [taxonomyLoading, setTaxonomyLoading] = useState(false)

  // Fetch taxonomy on mount
  useEffect(() => {
    const fetchTaxonomy = async () => {
      setTaxonomyLoading(true)
      try {
        const [nodesRes, edgesRes] = await Promise.all([
          fetch('/taxonomy/nodes'),
          fetch('/taxonomy/edges'),
        ])
        const nodes = await nodesRes.json()
        const edges = await edgesRes.json()
        console.log('Fetched taxonomy nodes:', nodes)
        console.log('Fetched taxonomy edges:', edges)
        setTaxonomyNodes(nodes)
        setTaxonomyEdges(edges)
      } catch (e) {
        console.error('Failed to fetch taxonomy:', e)
      }
      setTaxonomyLoading(false)
    }
    fetchTaxonomy()
  }, [])

  // Color scheme for different node types (case-insensitive)
  const nodeColors = React.useMemo(() => {
    const map: Record<string, string> = {}
    taxonomyNodes.forEach((n) => { map[n.name.toLowerCase()] = n.color })
    return map
  }, [taxonomyNodes])
  const edgeColors = React.useMemo(() => {
    const map: Record<string, string> = {}
    taxonomyEdges.forEach((e) => { map[e.name.toLowerCase()] = e.color })
    return map
  }, [taxonomyEdges])

  // Helper to get color with fallback
  const getNodeColor = (type: string) => nodeColors[type?.toLowerCase()] || '#888888'
  const getEdgeColor = (type: string) => edgeColors[type?.toLowerCase()] || '#888888'

  const initializeSimulation = useCallback(() => {
    if (!graphData || !containerRef.current) return

    // Filter nodes and apply search query
    const searchedNodes = graphData.nodes.filter(node => 
      node.label.toLowerCase().includes(searchQuery.toLowerCase())
    )

    const nodeIds = new Set(searchedNodes.map(n => n.id))

    // Filter edges based on filtered nodes
    const filteredEdges = graphData.edges.filter(edge => 
      nodeIds.has(edge.source) && nodeIds.has(edge.target) && filters.edgeTypes.includes(edge.type)
    )

    // Further filter nodes based on connections
    const connectionCounts = filteredEdges.reduce((acc, edge) => {
      acc[edge.source] = (acc[edge.source] || 0) + 1
      acc[edge.target] = (acc[edge.target] || 0) + 1
      return acc
    }, {} as Record<string, number>)

    const finalNodes = searchedNodes.filter(node => 
      filters.nodeTypes.includes(node.type) &&
      (filteredEdges.length === 0 || (connectionCounts[node.id] || 0) >= filters.minConnections)
    )

    // Adjust for UI elements to find the visual center
    const { clientWidth, clientHeight } = containerRef.current
    const legendWidth = showLegend ? 280 : 0; // Approx. width of the legend panel
    const toolbarHeight = 70; // Approx. height of the toolbar

    const availableWidth = clientWidth - legendWidth;
    const centerX = availableWidth / 2;
    const centerY = toolbarHeight + (clientHeight - toolbarHeight) / 2;

    // Start nodes in a tight random cluster around the visual center
    const radius = Math.min(availableWidth, clientHeight) * 0.1;

    const simNodes: SimulationNode[] = finalNodes.map((node, i) => {
      // Keep existing random initialization but centered correctly
      return {
        ...node,
        size: Math.max(5, Math.min(15, (connectionCounts[node.id] || 0) + 5)),
        color: getNodeColor(node.type),
        metadata: { connections: connectionCounts[node.id] || 0 },
        x: centerX + (Math.random() - 0.5) * radius,
        y: centerY + (Math.random() - 0.5) * radius,
        vx: 0,
        vy: 0
      }
    })

    const simEdges: SimulationEdge[] = filteredEdges.map(edge => {
      const source = simNodes.find(n => n.id === edge.source)!
      const target = simNodes.find(n => n.id === edge.target)!
      return { 
        ...edge, 
        weight: edge.weight || 1, // Default weight if not provided
        source, 
        target,
        color: getEdgeColor(edge.type)
      }
    })

    setSimulationNodes(simNodes)
    setSimulationEdges(simEdges)

    // Center view on initial cluster immediately
    if (containerRef.current) {
      setTransform({
        x: 0, // Centering is now done via node positions
        y: 0,
        scale: 1,
      })
    }
  }, [graphData, filters, searchQuery, showLegend])

  // Reverted to simple load on mount. Manual refresh might be needed.
  useEffect(() => {
    loadKnowledgeGraph()
  }, [])

  useEffect(() => {
    if (graphData) {
      initializeSimulation()
    }
  }, [graphData, filters, searchQuery, showLegend]) // Re-init if legend visibility changes

  // Auto-restart simulation when container ref is available
  useEffect(() => {
    if (containerRef.current && graphData && simulationNodes.length === 0) {
      initializeSimulation()
    }
  }, [containerRef.current, graphData])

  // Re-enable the animation loop
  useEffect(() => {
    let animationFrameId: number;

    const animate = () => {
      updateSimulation();
      drawGraph();
      animationFrameId = requestAnimationFrame(animate);
    };

    if (simulationNodes.length > 0) {
      animate();
    }

    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
    };
  }, [simulationNodes, transform]); // Rerun if transform changes to keep drawing


  const loadKnowledgeGraph = async () => {
    setIsLoading(true)
    setError(null)
    try {
      // Directly use the returned data, which is already of type KnowledgeGraphData
      const data = await getKnowledgeGraph()
      setGraphData(data)
    } catch (error) {
      console.error('Failed to load knowledge graph:', error)
      setError('Failed to load knowledge graph. Please check if the backend services are running.')
    } finally {
      setIsLoading(false)
    }
  }

  const renderCanvas = () => {
    if (isLoading) {
      return (
        <div className="absolute inset-0 bg-secondary-100 flex items-center justify-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-primary-500"></div>
        </div>
      )
    }

    if (error) {
      return (
        <div className="absolute inset-0 bg-secondary-100 flex items-center justify-center p-4">
          <div className="text-center bg-white p-6 rounded-lg shadow-md max-w-sm">
            <AlertCircle className="mx-auto h-12 w-12 text-error-400" />
            <h3 className="mt-2 text-lg font-medium text-secondary-900">
              Error Loading Graph
            </h3>
            <p className="mt-1 text-sm text-secondary-600">{error}</p>
            <button
              onClick={loadKnowledgeGraph}
              className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
            >
              Retry
            </button>
          </div>
        </div>
      )
    }
    
    if (simulationNodes.length === 0) {
      return (
        <div className="absolute inset-0 bg-secondary-100 flex items-center justify-center pt-20">
          <div className="text-center bg-white p-8 rounded-lg shadow-lg">
            <h3 className="text-lg font-medium text-secondary-800">
              No data to display
            </h3>
            <p className="text-sm text-secondary-600 mt-2">
              Try adjusting your filters or wait for more data to be processed.
            </p>
          </div>
        </div>
      )
    }

    const canvasWidth = containerRef.current?.clientWidth ?? 1200;
    const canvasHeight = containerRef.current?.clientHeight ?? 800;

    return (
      <canvas
        ref={canvasRef}
        width={canvasWidth}
        height={canvasHeight}
        onClick={handleCanvasClick}
        onMouseDown={handleCanvasMouseDown}
        onMouseUp={handleCanvasMouseUp}
        onMouseMove={handleCanvasMouseMove}
        onMouseLeave={handleCanvasMouseLeave}
        className="cursor-grab active:cursor-grabbing w-full h-full"
        style={{ minWidth: '800px', minHeight: '600px', maxWidth: '100%', maxHeight: '100%' }}
      />
    )
  }

  const updateSimulation = () => {
    // "Calm" simulation parameters
    const alpha = 0.1; // Learning rate
    const linkDistance = 150; // Ideal distance for links
    const linkStrength = 0.05; // How strongly links pull nodes together
    const repelStrength = 60;  // How much nodes push each other apart
    const centerStrength = 0.01; // How strongly nodes are pulled to the visual center

    const { clientWidth, clientHeight } = containerRef.current || { clientWidth: 0, clientHeight: 0 };
    const legendWidth = showLegend ? 280 : 0;
    const toolbarHeight = 70;
    const centerX = (clientWidth - legendWidth) / 2;
    const centerY = toolbarHeight + (clientHeight - toolbarHeight) / 2;

    // Apply forces
    simulationNodes.forEach(node => {
      if (node.fx !== undefined) node.x = node.fx;
      if (node.fy !== undefined) node.y = node.fy;

      // Centering force
      node.vx += (centerX - node.x) * centerStrength * alpha;
      node.vy += (centerY - node.y) * centerStrength * alpha;

      // Repel from other nodes
      simulationNodes.forEach(other => {
        if (node === other) return;
        const dx = node.x - other.x;
        const dy = node.y - other.y;
        let distance = Math.sqrt(dx * dx + dy * dy);
        if (distance < 1) distance = 1; // prevent division by zero

        if (distance < repelStrength * 5) { // Only calculate repulsion for nearby nodes
          const force = (repelStrength / distance);
          node.vx += (dx / distance) * force * alpha;
          node.vy += (dy / distance) * force * alpha;
        }
      });
    });

    // Link forces
    simulationEdges.forEach(edge => {
      const dx = edge.target.x - edge.source.x;
      const dy = edge.target.y - edge.source.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      if (distance > 0) {
        const force = (distance - linkDistance) * linkStrength * alpha;
        const fx = (dx / distance) * force;
        const fy = (dy / distance) * force;

        edge.source.vx += fx;
        edge.source.vy += fy;
        edge.target.vx -= fx;
        edge.target.vy -= fy;
      }
    });

    // Update positions with damping
    simulationNodes.forEach(node => {
      if (node.fx === undefined) {
        node.vx *= 0.95; // Damping to prevent endless oscillation
        node.x += node.vx;
      }
      if (node.fy === undefined) {
        node.vy *= 0.95; // Damping
        node.y += node.vy;
      }
    });
  }

  const drawGraph = () => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Apply transform
    ctx.save()
    ctx.translate(transform.x, transform.y)
    ctx.scale(transform.scale, transform.scale)

    // Draw edges
    simulationEdges.forEach(edge => {
      ctx.beginPath()
      ctx.moveTo(edge.source.x, edge.source.y)
      ctx.lineTo(edge.target.x, edge.target.y)
      ctx.strokeStyle = edge.color + '80'
      ctx.lineWidth = Math.sqrt(edge.weight) * 2
      ctx.stroke()

      // Draw edge labels for selected nodes
      if (selectedNode && (edge.source === selectedNode || edge.target === selectedNode)) {
        const midX = (edge.source.x + edge.target.x) / 2
        const midY = (edge.source.y + edge.target.y) / 2
        ctx.fillStyle = '#374151'
        ctx.font = '10px Arial'
        ctx.textAlign = 'center'
        ctx.fillText(edge.type, midX, midY)
      }
    })

    // Draw nodes
    simulationNodes.forEach(node => {
      const isSelected = selectedNode === node
      const isHovered = hoveredNode === node
      const isHighlighted = searchQuery && node.label.toLowerCase().includes(searchQuery.toLowerCase())

      // Node circle
      ctx.beginPath()
      ctx.arc(node.x, node.y, node.size * 2, 0, 2 * Math.PI)
      ctx.fillStyle = node.color
      
      if (isSelected) {
        ctx.shadowColor = node.color
        ctx.shadowBlur = 20
      }
      
      if (isHighlighted) {
        ctx.strokeStyle = '#EF4444'
        ctx.lineWidth = 3
        ctx.stroke()
      }

      ctx.fill()
      ctx.shadowBlur = 0

      // Node border
      if (isSelected || isHovered) {
        ctx.beginPath()
        ctx.arc(node.x, node.y, node.size * 2 + 2, 0, 2 * Math.PI)
        ctx.strokeStyle = isSelected ? '#1F2937' : '#6B7280'
        ctx.lineWidth = 2
        ctx.stroke()
      }

      // Node label
      ctx.fillStyle = '#1F2937'
      ctx.font = `${12 * Math.sqrt(transform.scale)}px Arial`
      ctx.textAlign = 'center'
      const maxLength = 20
      const label = node.label.length > maxLength 
        ? node.label.substring(0, maxLength) + '...' 
        : node.label
      ctx.fillText(label, node.x, node.y + node.size * 2 + 20)
    })

    ctx.restore()
  }

  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = (event.clientX - rect.left - transform.x) / transform.scale
    const y = (event.clientY - rect.top - transform.y) / transform.scale

    // Find clicked node
    const clickedNode = simulationNodes.find(node => {
      const distance = Math.sqrt((x - node.x) ** 2 + (y - node.y) ** 2)
      return distance <= node.size * 2
    })

    setSelectedNode(clickedNode || null)
  }

  // --- Panning Handlers ---
  const handleCanvasMouseDown = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mouseX = event.clientX - rect.left
    const mouseY = event.clientY - rect.top
    // Check if clicking on a node (don't start panning if so)
    const x = (mouseX - transform.x) / transform.scale
    const y = (mouseY - transform.y) / transform.scale
    const clickedNode = simulationNodes.find(node => {
      const distance = Math.sqrt((x - node.x) ** 2 + (y - node.y) ** 2)
      return distance <= node.size * 2
    })
    if (!clickedNode) {
      setIsPanning(true)
      setPanStart({ x: mouseX, y: mouseY, origX: transform.x, origY: transform.y })
    }
  }

  const handleCanvasMouseUp = () => {
    setIsPanning(false)
    setPanStart(null)
  }

  const handleCanvasMouseMove = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mouseX = event.clientX - rect.left
    const mouseY = event.clientY - rect.top
    if (isPanning && panStart) {
      // Calculate new transform offset
      setTransform(prev => ({
        ...prev,
        x: panStart.origX + (mouseX - panStart.x),
        y: panStart.origY + (mouseY - panStart.y),
      }))
      return
    }
    // Existing hover logic
    const x = (mouseX - transform.x) / transform.scale
    const y = (mouseY - transform.y) / transform.scale
    const hoveredNode = simulationNodes.find(node => {
      const distance = Math.sqrt((x - node.x) ** 2 + (y - node.y) ** 2)
      return distance <= node.size * 2
    })
    setHoveredNode(hoveredNode || null)
    canvas.style.cursor = hoveredNode ? 'pointer' : isPanning ? 'grabbing' : 'grab'
  }

  // Add mouse leave to stop panning if mouse leaves canvas
  const handleCanvasMouseLeave = () => {
    setIsPanning(false)
    setPanStart(null)
    setHoveredNode(null)
  }

  const handleReset = () => {
    setTransform({ x: 0, y: 0, scale: 1 })
    setSelectedNode(null)
    initializeSimulation()
  }

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen)
  }

  const exportGraph = () => {
    const canvas = canvasRef.current
    if (!canvas) return

    const link = document.createElement('a')
    link.download = 'knowledge-graph.png'
    link.href = canvas.toDataURL()
    link.click()
  }

  const handleNodeUpdate = async (nodeId: string, updates: { label: string }) => {
    try {
      // Update the backend first
      await apiService.updateNodeLabel(nodeId, updates.label)
      
      // Update the local state only after successful backend update
      setSimulationNodes(nodes => 
        nodes.map(node => 
          node.id === nodeId ? { ...node, label: updates.label } : node
        )
      )
      
      // Update the graph data
      if (graphData) {
        setGraphData(data => {
          if (!data) return data
          return {
            ...data,
            nodes: data.nodes.map(node => 
              node.id === nodeId ? { ...node, label: updates.label } : node
            )
          }
        })
      }
      
    } catch (error) {
      console.error('Failed to update node:', error)
      // Reload the graph data to ensure consistency
      await loadKnowledgeGraph()
      throw error
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Knowledge Graph</h1>
          <p className="mt-1 text-sm text-secondary-600">
            Visualize relationships between ideas, entities, and categories
          </p>
        </div>
        <div className="card">
          <div className="card-body">
            <div className="text-center py-12">
              <RefreshCw className="mx-auto h-16 w-16 text-secondary-400 animate-spin" />
              <h3 className="mt-4 text-lg font-medium text-secondary-900">
                Loading Knowledge Graph
              </h3>
              <p className="mt-2 text-sm text-secondary-500">
                Analyzing relationships and building visualization...
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Knowledge Graph</h1>
          <p className="mt-1 text-sm text-secondary-600">
            Visualize relationships between ideas, entities, and categories
          </p>
        </div>
        <div className="card">
          <div className="card-body">
            <div className="text-center py-12">
              <AlertCircle className="mx-auto h-16 w-16 text-error-400" />
              <h3 className="mt-4 text-lg font-medium text-secondary-900">
                Failed to Load Knowledge Graph
              </h3>
              <p className="mt-2 text-sm text-secondary-500">
                {error}
              </p>
              <button
                onClick={loadKnowledgeGraph}
                className="mt-4 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const handleWheel = (event: React.WheelEvent) => {
    event.preventDefault()
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const mouseX = event.clientX - rect.left
    const mouseY = event.clientY - rect.top

    const zoomFactor = event.deltaY > 0 ? 0.9 : 1.1
    const newScale = Math.max(0.3, Math.min(3, transform.scale * zoomFactor))
    
    // Zoom towards mouse position
    const scaleChange = newScale / transform.scale
    const newX = mouseX - (mouseX - transform.x) * scaleChange
    const newY = mouseY - (mouseY - transform.y) * scaleChange

    setTransform({
      x: newX,
      y: newY,
      scale: newScale
    })
  }

  const zoomAroundCenter = (factor: number) => {
    const canvas = canvasRef.current
    if (!canvas) return
    setTransform(prev => {
      const newScale = Math.max(0.3, Math.min(3, prev.scale * factor))
      const scaleChange = newScale / prev.scale
      const centerX = canvas.width / 2
      const centerY = canvas.height / 2
      const newX = centerX - (centerX - prev.x) * scaleChange
      const newY = centerY - (centerY - prev.y) * scaleChange
      const newTransform = { x: newX, y: newY, scale: newScale }
      // Force immediate redraw
      setTimeout(() => drawGraph(), 0)
      return newTransform
    })
  }

  const handleZoomIn = () => zoomAroundCenter(1.25)
  const handleZoomOut = () => zoomAroundCenter(0.8)

  return (
    <div
      ref={containerRef}
      className={`bg-secondary-100 relative mx-auto my-6 rounded-lg shadow w-[90vw] h-[70vh] min-w-[800px] min-h-[600px] max-w-full max-h-full ${
        isFullscreen ? 'fixed inset-0 z-50 w-full h-full m-0 rounded-none shadow-none' : ''
      }`}
      onWheel={handleWheel}
    >
      {/* Canvas or message is the base layer */}
      {renderCanvas()}

      {/* Toolbar and other components are overlays */}
      <GraphToolbar
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onReset={handleReset}
        onToggleFullscreen={toggleFullscreen}
        isFullscreen={isFullscreen}
        onExport={exportGraph}
        onRefresh={loadKnowledgeGraph}
        isLegendVisible={showLegend}
        onToggleLegend={() => setShowLegend(!showLegend)}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        totalNodes={graphData?.nodes.length ?? 0}
        visibleNodes={simulationNodes.length}
        onShowHelp={() => setShowHelp(true)}
      />

      {/* Legend */}
      {showLegend && (
        <GraphLegend
          taxonomyNodes={taxonomyNodes}
          taxonomyEdges={taxonomyEdges}
          stats={{
            nodes: simulationNodes.length,
            edges: simulationEdges.length,
          }}
          onShowHelp={() => setShowHelp(true)}
        />
      )}

      {/* Node Details Panel */}
      {selectedNode && (
        <NodeDetailsPanel 
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
          onNodeUpdate={handleNodeUpdate}
        />
      )}

      {/* Help Modal */}
      {showHelp && (
        <KnowledgeGraphHelp onClose={() => setShowHelp(false)} />
      )}

      {/* Graph Stats removed – stats now only in legend */}
    </div>
  )
}

// Refactor GraphLegend to use taxonomy props
const GraphLegend: React.FC<{
  taxonomyNodes: any[];
  taxonomyEdges: any[];
  stats: { nodes: number; edges: number };
  onShowHelp?: () => void;
}> = ({ taxonomyNodes, taxonomyEdges, stats, onShowHelp }) => {
  return (
    <div className="absolute top-20 right-4 bg-white bg-opacity-90 backdrop-blur-sm rounded-lg shadow-lg p-4 w-56">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-secondary-900">Legend</h4>
        {onShowHelp && (
          <button
            onClick={onShowHelp}
            className="p-1 text-secondary-400 hover:text-secondary-600 rounded"
            title="Show detailed definitions"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
        )}
      </div>
      <div className="space-y-2">
        <div className="text-xs font-medium text-secondary-700">Node Types</div>
        {taxonomyNodes.map((node) => (
          <div key={node.id} className="flex items-center space-x-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: node.color }}
            />
            <span className="text-xs text-secondary-600 capitalize">{node.name}</span>
          </div>
        ))}
        {taxonomyNodes.length === 0 && (
          <div className="text-xs text-red-600">No node types found in taxonomy.</div>
        )}
        <div className="text-xs font-medium text-secondary-700 mt-3 pt-2 border-t">Edge Types</div>
        {taxonomyEdges.map((edge) => (
          <div key={edge.id} className="flex items-center space-x-2">
            <div
              className="w-6 h-0.5"
              style={{ backgroundColor: edge.color }}
            />
            <span className="text-xs text-secondary-600">{edge.name.replace(/_/g, ' ')}</span>
          </div>
        ))}
        {taxonomyEdges.length === 0 && (
          <div className="text-xs text-red-600">No edge types found in taxonomy.</div>
        )}
      </div>
      <div className="mt-3 pt-3 border-t">
        <h4 className="text-sm font-medium text-secondary-900 mb-2">Stats</h4>
        <div className="text-xs text-secondary-600 space-y-1">
          <div>Visible Nodes: {stats.nodes}</div>
          <div>Visible Edges: {stats.edges}</div>
        </div>
      </div>
    </div>
  )
}

// Graph Filters Component
const GraphFilters: React.FC<{
  filters: any
  onFiltersChange: (filters: any) => void
}> = ({ filters, onFiltersChange }) => {
  const nodeTypeOptions = [
    { value: 'concept', label: 'Concepts', color: '#3B82F6' },
    { value: 'organization', label: 'Organizations', color: '#10B981' },
    { value: 'technology', label: 'Technologies', color: '#F59E0B' }
  ]

  const edgeTypeOptions = [
    { value: 'is-a', label: 'Is A' },
    { value: 'part-of', label: 'Part Of' },
    { value: 'related-to', label: 'Related To' }
  ]

  return (
    <>
      <div>
        <label className="block text-sm font-medium text-secondary-700 mb-2">
          Node Types
        </label>
        <div className="space-y-2">
          {nodeTypeOptions.map((option) => (
            <label key={option.value} className="flex items-center text-sm">
              <input
                type="checkbox"
                checked={filters.nodeTypes.includes(option.value)}
                onChange={(e) => {
                  const nodeTypes = e.target.checked
                    ? [...filters.nodeTypes, option.value]
                    : filters.nodeTypes.filter((t: string) => t !== option.value)
                  onFiltersChange({ ...filters, nodeTypes })
                }}
                className="mr-2 rounded border-secondary-300 text-primary-600"
              />
              <div 
                className="w-3 h-3 rounded-full mr-2" 
                style={{ backgroundColor: option.color }}
              />
              <span className="text-secondary-700">{option.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-secondary-700 mb-2">
          Edge Types
        </label>
        <div className="space-y-2">
          {edgeTypeOptions.map((option) => (
            <label key={option.value} className="flex items-center text-sm">
              <input
                type="checkbox"
                checked={filters.edgeTypes.includes(option.value)}
                onChange={(e) => {
                  const edgeTypes = e.target.checked
                    ? [...filters.edgeTypes, option.value]
                    : filters.edgeTypes.filter((t: string) => t !== option.value)
                  onFiltersChange({ ...filters, edgeTypes })
                }}
                className="mr-2 rounded border-secondary-300 text-primary-600"
              />
              <span className="text-secondary-700">{option.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-secondary-700 mb-2">
          Minimum Connections
        </label>
        <input
          type="range"
          min="1"
          max="20"
          value={filters.minConnections}
          onChange={(e) => onFiltersChange({ 
            ...filters, 
            minConnections: parseInt(e.target.value) 
          })}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-secondary-500 mt-1">
          <span>1</span>
          <span>{filters.minConnections}</span>
          <span>20+</span>
        </div>
      </div>
    </>
  )
}

// Node Details Panel Component
const NodeDetailsPanel: React.FC<{
  node: SimulationNode
  onClose: () => void
  onNodeUpdate?: (nodeId: string, updates: { label: string }) => void
}> = ({ node, onClose, onNodeUpdate }) => {
  const [nodeDetails, setNodeDetails] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editedLabel, setEditedLabel] = useState(node.label)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    loadNodeDetails()
  }, [node.id])

  const loadNodeDetails = async () => {
    setIsLoading(true)
    try {
      const details = await getNodeDetails(node.id)
      setNodeDetails(details)
    } catch (error) {
      console.error('Failed to load node details:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSave = async () => {
    if (!onNodeUpdate || editedLabel.trim() === node.label) return
    
    setIsSaving(true)
    try {
      await onNodeUpdate(node.id, { label: editedLabel.trim() })
      setIsEditing(false)
    } catch (error) {
      console.error('Failed to update node:', error)
      // Reset to original label on error
      setEditedLabel(node.label)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setEditedLabel(node.label)
    setIsEditing(false)
  }

  return (
    <div className="absolute top-4 left-4 bg-white rounded-lg shadow-xl border border-secondary-200 w-80 max-h-96 overflow-hidden z-20">
      <div className="p-4 border-b border-secondary-200">
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0 mr-2">
            <h3
              className="text-lg font-medium text-secondary-900 truncate"
              title={node.label}
            >
              {node.label}
            </h3>
          </div>
          {onNodeUpdate && (
            <button
              onClick={() => setIsEditing(true)}
              className="p-1 text-secondary-400 hover:text-secondary-600 rounded"
              title="Edit label"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1 hover:bg-secondary-100 rounded"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="flex items-center mt-2">
          <div 
            className="w-3 h-3 rounded-full mr-2" 
            style={{ backgroundColor: node.color }}
          />
          <span className="text-sm text-secondary-600 capitalize">{node.type}</span>
          <span className="ml-2 text-xs text-secondary-500">
            {node.size} connections
          </span>
        </div>
      </div>
      
      <div className="p-4 overflow-y-auto max-h-64">
        {isLoading ? (
          <div className="text-center py-4">
            <RefreshCw className="w-6 h-6 text-secondary-400 animate-spin mx-auto" />
            <p className="text-sm text-secondary-500 mt-2">Loading details...</p>
          </div>
        ) : nodeDetails ? (
          <div className="space-y-3 text-sm">
            {nodeDetails.description && (
              <div>
                <div className="font-medium text-secondary-700">Description</div>
                <p className="text-secondary-600 mt-1">{nodeDetails.description}</p>
              </div>
            )}
            {nodeDetails.metadata && (
              <div>
                <div className="font-medium text-secondary-700">Metadata</div>
                <div className="mt-1 space-y-1">
                  {Object.entries(nodeDetails.metadata).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-secondary-500">{key}:</span>
                      <span className="text-secondary-700">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {nodeDetails.connections && (
              <div>
                <div className="font-medium text-secondary-700">Top Connections</div>
                <div className="mt-1 space-y-1">
                  {nodeDetails.connections.slice(0, 5).map((conn: any, index: number) => (
                    <div key={index} className="text-secondary-600">
                      {conn.type}: {conn.target}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-4">
            <Info className="w-6 h-6 text-secondary-400 mx-auto" />
            <p className="text-sm text-secondary-500 mt-2">No additional details available</p>
          </div>
        )}
      </div>
    </div>
  )
}

// Graph Toolbar Component
const GraphToolbar: React.FC<{
  onZoomIn: () => void
  onZoomOut: () => void
  onReset: () => void
  onToggleFullscreen: () => void
  isFullscreen: boolean
  onExport: () => void
  onRefresh: () => void
  isLegendVisible: boolean
  onToggleLegend: () => void
  searchQuery: string
  onSearchChange: (query: string) => void
  totalNodes: number
  visibleNodes: number
  onShowHelp: () => void
}> = ({
  onZoomIn,
  onZoomOut,
  onReset,
  onToggleFullscreen,
  isFullscreen,
  onExport,
  onRefresh,
  isLegendVisible,
  onToggleLegend,
  searchQuery,
  onSearchChange,
  totalNodes,
  visibleNodes,
  onShowHelp
}) => {
  return (
    <div className="absolute top-4 left-4 z-10 bg-white shadow-lg rounded-lg p-2 flex flex-wrap items-center gap-2 max-w-4xl">
      {/* Zoom controls */}
      <div className="flex items-center space-x-1">
        <button
          onClick={onZoomOut}
          className="p-1.5 text-secondary-600 hover:text-secondary-900 hover:bg-secondary-100 rounded"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={onZoomIn}
          className="p-1.5 text-secondary-600 hover:text-secondary-900 hover:bg-secondary-100 rounded"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
      </div>

      <div className="w-px h-6 bg-secondary-200" />

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-secondary-400" />
        <input
          type="text"
          placeholder={`Search ${visibleNodes}/${totalNodes} nodes...`}
          value={searchQuery}
          onChange={e => onSearchChange(e.target.value)}
          className="pl-7 pr-2 py-1 text-xs w-36 border border-secondary-300 rounded focus:ring-primary-500 focus:border-primary-500"
        />
      </div>

      <div className="w-px h-6 bg-secondary-200" />

      {/* Action buttons */}
      <div className="flex items-center space-x-1">
        <button
          onClick={onReset}
          className="p-1.5 text-secondary-600 hover:text-secondary-900 hover:bg-secondary-100 rounded"
          title="Reset View"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
        
        <button
          onClick={onToggleFullscreen}
          className="p-1.5 text-secondary-600 hover:text-secondary-900 hover:bg-secondary-100 rounded"
          title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
        >
          {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
        </button>

        <button
          onClick={onExport}
          className="p-1.5 text-secondary-600 hover:text-secondary-900 hover:bg-secondary-100 rounded"
          title="Export Graph"
        >
          <Download className="w-4 h-4" />
        </button>

        <button
          onClick={onToggleLegend}
          className={`flex items-center px-2 py-1.5 text-xs rounded ${
            isLegendVisible ? 'bg-primary-100 text-primary-700' : 'text-secondary-600 hover:bg-secondary-100'
          }`}
          title={isLegendVisible ? "Hide Legend" : "Show Legend"}
        >
          {isLegendVisible ? <EyeOff className="w-3 h-3 mr-1" /> : <Eye className="w-3 h-3 mr-1" />}
          Legend
        </button>

        <button
          onClick={onRefresh}
          className="p-1.5 text-secondary-600 hover:text-secondary-900 hover:bg-secondary-100 rounded"
          title="Refresh Data"
        >
          <RefreshCw className="w-4 h-4" />
        </button>

        <button
          onClick={onShowHelp}
          className="p-1.5 text-secondary-600 hover:text-secondary-900 hover:bg-secondary-100 rounded"
          title="Show Help"
        >
          <HelpCircle className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

// Knowledge Graph Help Modal Component
const KnowledgeGraphHelp: React.FC<{
  onClose: () => void
}> = ({ onClose }) => {
  // Fetch taxonomy for help modal
  const [taxonomyNodes, setTaxonomyNodes] = React.useState<any[]>([])
  const [taxonomyEdges, setTaxonomyEdges] = React.useState<any[]>([])
  const [loading, setLoading] = React.useState(false)
  React.useEffect(() => {
    const fetchTaxonomy = async () => {
      setLoading(true)
      try {
        const [nodesRes, edgesRes] = await Promise.all([
          fetch('/taxonomy/nodes'),
          fetch('/taxonomy/edges'),
        ])
        setTaxonomyNodes(await nodesRes.json())
        setTaxonomyEdges(await edgesRes.json())
      } catch {}
      setLoading(false)
    }
    fetchTaxonomy()
  }, [])
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        <div className="p-6 border-b border-secondary-200">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-secondary-900">Knowledge Graph Guide</h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-secondary-100 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <p className="mt-2 text-secondary-600">
            Explore how your ideas, entities, and relationships are mapped in the knowledge graph. This guide explains what the nodes and edges mean, and how to use the graph for discovery and insight.
          </p>
        </div>
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)] space-y-8">
          {/* Node Types */}
          <section>
            <h3 className="text-xl font-semibold text-secondary-900 mb-4">🔍 Node Types</h3>
            {loading ? <div>Loading...</div> : (
              <div className="grid gap-4 md:grid-cols-2">
                {taxonomyNodes.map((node) => (
                  <div key={node.id} className="border rounded-lg p-4" style={{ borderColor: node.color + '55' }}>
                    <div className="flex items-center mb-2">
                      <div className="w-4 h-4 rounded-full mr-3" style={{ background: node.color }}></div>
                      <h4 className="text-lg font-medium text-secondary-900">{node.name}</h4>
                    </div>
                    <p className="text-secondary-700 text-sm mb-1"><strong>Definition:</strong> {node.definition}</p>
                    {node.example && <div className="text-xs text-secondary-600">Example: {node.example}</div>}
                  </div>
                ))}
              </div>
            )}
            {taxonomyNodes.length === 0 && (
              <div className="text-xs text-red-600">No node types found in taxonomy.</div>
            )}
          </section>
          {/* Edge Types */}
          <section>
            <h3 className="text-xl font-semibold text-secondary-900 mb-4">🔗 Relationship Types</h3>
            {loading ? <div>Loading...</div> : (
              <div className="grid gap-3 md:grid-cols-2">
                {taxonomyEdges.map((edge) => (
                  <div key={edge.id} className="flex items-center p-3 bg-gray-50 rounded-lg">
                    <div className="w-8 h-0.5 mr-3" style={{ background: edge.color }}></div>
                    <div>
                      <span className="font-medium">{edge.name}:</span> {edge.definition} {edge.example && <span className="text-xs text-secondary-600">({edge.example})</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {taxonomyEdges.length === 0 && (
              <div className="text-xs text-red-600">No edge types found in taxonomy.</div>
            )}
          </section>
          {/* Usage Guidelines */}
          <section>
            <h3 className="text-xl font-semibold text-secondary-900 mb-4">💡 Usage Tips</h3>
            <div className="space-y-3">
              <div className="p-3 bg-green-50 border-l-4 border-green-400">
                <strong className="text-green-800">Explore:</strong>
                <span className="text-green-700"> Click nodes to see details and connections. Use zoom and pan to navigate large graphs.</span>
              </div>
              <div className="p-3 bg-blue-50 border-l-4 border-blue-400">
                <strong className="text-blue-800">Discover:</strong>
                <span className="text-blue-700"> Look for clusters and bridges between ideas, entities, and categories to find new insights.</span>
              </div>
              <div className="p-3 bg-purple-50 border-l-4 border-purple-400">
                <strong className="text-purple-800">Organize:</strong>
                <span className="text-purple-700"> Use filters and search to focus on specific types or topics. Categories help you group related knowledge.</span>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

export default KnowledgeGraph 