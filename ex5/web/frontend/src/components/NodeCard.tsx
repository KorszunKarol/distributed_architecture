import { NodeData } from '../hooks/useWebSocket'
import { useState } from 'react'

interface NodeCardProps {
  node: NodeData
}

export function NodeCard({ node }: NodeCardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const dataCount = Object.keys(node.current_data).length

  return (
    <>
      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-90 p-4 backdrop-blur-sm">
          <div className="max-h-[80vh] w-full max-w-2xl overflow-hidden rounded-xl bg-[#1a1a1a] shadow-xl border border-gray-800">
            <div className="flex items-center justify-between border-b border-gray-800 p-4">
              <h3 className="text-xl font-medium text-gray-200">
                Node {node.node_id} Data
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="rounded-full p-2 hover:bg-[#252525]"
              >
                <svg className="h-6 w-6 text-gray-400" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24" stroke="currentColor">
                  <path d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </button>
            </div>

            <div className="p-4">
              <div className="mb-4 grid grid-cols-2 gap-4">
                <div className="rounded-lg bg-[#252525] p-3 border border-gray-700">
                  <div className="text-sm text-gray-400">Updates</div>
                  <div className="text-lg font-medium text-gray-200">{node.update_count}</div>
                </div>
                <div className="rounded-lg bg-[#252525] p-3 border border-gray-700">
                  <div className="text-sm text-gray-400">Status</div>
                  <div className="text-lg font-medium text-gray-200">{node.is_connected ? 'Active' : 'Inactive'}</div>
                </div>
                {node.last_sync_time && (
                  <div className="col-span-2 rounded-lg bg-[#252525] p-3 border border-gray-700">
                    <div className="text-sm text-gray-400">Last Sync</div>
                    <div className="text-lg font-medium text-gray-200">
                      {new Date(node.last_sync_time).toLocaleString()}
                    </div>
                  </div>
                )}
              </div>

              <div className="rounded-lg border border-gray-700 bg-[#252525]">
                <div className="border-b border-gray-700 bg-[#1a1a1a] p-3">
                  <h4 className="font-medium text-gray-200">Current Data</h4>
                </div>
                <div className="max-h-[40vh] overflow-y-auto p-3">
                  <table className="w-full">
                    <thead className="sticky top-0 bg-[#1a1a1a]">
                      <tr>
                        <th className="pb-2 text-left text-sm font-medium text-gray-400">Key</th>
                        <th className="pb-2 text-left text-sm font-medium text-gray-400">Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                      {Object.entries(node.current_data).map(([key, value]) => (
                        <tr key={key}>
                          <td className="py-2 pr-4 font-mono text-sm text-gray-300">{key}</td>
                          <td className="py-2 font-mono text-sm text-gray-300">{value}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Card */}
      <div
        onClick={() => setIsModalOpen(true)}
        className="animate-fadeIn cursor-pointer rounded-lg bg-gradient-to-br from-[#1a1a1a] to-[#252525] p-5 shadow-lg transition-all duration-300 hover:-translate-y-1 hover:shadow-xl border border-gray-800 hover:border-gray-700"
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-200">{node.node_id}</h3>
          <span className={`transform rounded-full px-2 py-1 text-xs font-medium transition-all duration-300 ${
            node.is_connected
              ? 'bg-green-900/30 text-green-400 border border-green-800/50 scale-100'
              : 'bg-[#252525] text-gray-400 border border-gray-700 scale-95'
          }`}>
            {node.is_connected ? 'Active' : 'Inactive'}
          </span>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm text-gray-300">
            <span>Updates</span>
            <span className="font-medium transition-all duration-300">{node.update_count}</span>
          </div>

          <div className="flex items-center justify-between text-sm text-gray-300">
            <span>Data Items</span>
            <span className="font-medium transition-all duration-300">{dataCount}</span>
          </div>

          {node.last_sync_time && (
            <div className="text-sm text-gray-400">
              Last Sync: {new Date(node.last_sync_time).toLocaleTimeString()}
            </div>
          )}

          <div className="mt-4 space-y-1">
            <div className="text-xs text-purple-400 hover:text-purple-300">
              Click to view all {dataCount} items →
            </div>
          </div>
        </div>
      </div>
    </>
  )
}