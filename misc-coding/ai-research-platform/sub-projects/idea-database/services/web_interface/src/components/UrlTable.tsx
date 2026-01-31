import React from 'react'
import { URL } from '../types'
import { ExternalLink } from 'lucide-react'

interface UrlTableProps {
  urls: URL[]
}

const UrlTable: React.FC<UrlTableProps> = ({ urls }) => {
  if (!urls || urls.length === 0) {
    return <p className="text-sm text-secondary-500">No URLs extracted.</p>
  }

  return (
    <table className="min-w-full divide-y divide-secondary-200 text-sm">
      <thead>
        <tr>
          <th className="px-3 py-2 text-left font-medium text-secondary-600">Title / URL</th>
          <th className="px-3 py-2 text-left font-medium text-secondary-600">Domain</th>
          <th></th>
        </tr>
      </thead>
      <tbody className="divide-y divide-secondary-200">
        {urls.map((u) => (
          <tr key={u.id}>
            <td className="px-3 py-2">
              <div className="font-medium text-primary-700 truncate max-w-xs">
                {u.title || u.url}
              </div>
              <div className="text-secondary-500 truncate max-w-xs">{u.url}</div>
            </td>
            <td className="px-3 py-2 text-secondary-700">{u.domain}</td>
            <td className="px-3 py-2 text-right">
              <a
                href={u.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center text-primary-600 hover:text-primary-800"
              >
                Open
                <ExternalLink className="h-4 w-4 ml-1" />
              </a>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default UrlTable 