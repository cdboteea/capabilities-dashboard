import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { apiService } from '../services/api'
import { RefreshCw, CheckCircle, XCircle } from 'lucide-react'
import XAPIQuotaCard from './XAPIQuotaCard'

interface XPostItem {
  tweet_id: string
  url: string
  processing_status: string
  created_at?: string
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return <CheckCircle className="w-4 h-4 text-green-600" />
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-600" />
    default:
      return <RefreshCw className="w-4 h-4 animate-spin text-yellow-600" />
  }
}

const XPostsTab: React.FC = () => {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const { data, isLoading, error } = useQuery('xPosts', () => apiService.getXPosts(1, 100), {
    refetchInterval: 30000,
  })

  const fetchMutation = useMutation((urls: string[]) => apiService.fetchXPosts(urls), {
    onSuccess: () => {
      setSelected(new Set())
      queryClient.invalidateQueries('xPosts')
      queryClient.invalidateQueries('xApiUsage')
    },
  })

  const toggleSelect = (url: string) => {
    const newSet = new Set(selected)
    if (newSet.has(url)) newSet.delete(url)
    else newSet.add(url)
    setSelected(newSet)
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const rows: XPostItem[] = (data as any)?.x_posts ?? []

  return (
    <div className="space-y-4">
      <XAPIQuotaCard />

      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h3 className="font-medium">X Posts ({rows.length})</h3>
          <button
            onClick={() => fetchMutation.mutate(Array.from(selected))}
            disabled={selected.size === 0 || fetchMutation.isLoading}
            className="btn btn-primary"
          >
            Fetch Selected ({selected.size})
          </button>
        </div>
        <div className="card-body overflow-x-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-8 h-8 animate-spin" />
            </div>
          ) : error ? (
            <p className="text-red-600">Failed to load X posts</p>
          ) : (
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-secondary-500">
                  <th className="px-2 py-1"></th>
                  <th className="px-2 py-1">Tweet</th>
                  <th className="px-2 py-1">Status</th>
                  <th className="px-2 py-1">Created</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.tweet_id} className="border-t">
                    <td className="px-2 py-1">
                      <input
                        type="checkbox"
                        checked={selected.has(row.url)}
                        onChange={() => toggleSelect(row.url)}
                      />
                    </td>
                    <td className="px-2 py-1 text-blue-600 underline cursor-pointer" onClick={() => window.open(row.url, '_blank')}>{row.tweet_id}</td>
                    <td className="px-2 py-1 flex items-center space-x-1">
                      {getStatusIcon(row.processing_status)}
                      <span>{row.processing_status}</span>
                    </td>
                    <td className="px-2 py-1">
                      {row.created_at ? new Date(row.created_at).toLocaleString() : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

export default XPostsTab 