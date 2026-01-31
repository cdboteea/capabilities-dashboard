import React from 'react'
import { Attachment } from '../types'
import { Download, Eye } from 'lucide-react'

interface AttachmentTableProps {
  atts: Attachment[]
  onView: (att: Attachment) => void
  onDownload?: (att: Attachment) => void
}

const AttachmentTable: React.FC<AttachmentTableProps> = ({ atts, onView, onDownload }) => {
  if (!atts || atts.length === 0) {
    return <p className="text-sm text-secondary-500">No attachments.</p>
  }
  return (
    <table className="min-w-full divide-y divide-secondary-200 text-sm">
      <thead>
        <tr>
          <th className="px-3 py-2 text-left font-medium text-secondary-600">Filename</th>
          <th className="px-3 py-2 text-left font-medium text-secondary-600">Type</th>
          <th className="px-3 py-2 text-left font-medium text-secondary-600">Size</th>
          <th></th>
        </tr>
      </thead>
      <tbody className="divide-y divide-secondary-200">
        {atts.map((a) => (
          <tr key={a.id}>
            <td className="px-3 py-2 text-primary-700 truncate max-w-xs">{a.filename}</td>
            <td className="px-3 py-2 text-secondary-700">{a.file_type}</td>
            <td className="px-3 py-2 text-secondary-700">{(a.file_size / 1024).toFixed(1)} KB</td>
            <td className="px-3 py-2 text-right space-x-3">
              <button
                onClick={() => onView(a)}
                className="inline-flex items-center text-secondary-600 hover:text-secondary-900"
              >
                <Eye className="h-4 w-4 mr-1" />View
              </button>
              <button
                onClick={() => onDownload ? onDownload(a) : onView(a)}
                className="inline-flex items-center text-primary-600 hover:text-primary-800"
              >
                <Download className="h-4 w-4 mr-1" />Download
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default AttachmentTable 