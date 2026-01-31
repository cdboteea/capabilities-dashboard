import { format } from 'date-fns'
import { Eye, MoreVertical } from 'lucide-react'
import { Idea } from '../types'

interface EmailTableProps {
  emails: Idea[]
  loading?: boolean
  onEmailSelect: (email: Idea) => void
  onEmailAction: (action: string, email: Idea) => void
  getStatusIcon: (status: string) => React.ReactNode
  getStatusBadge: (status: string) => string
}

const EmailTable: React.FC<EmailTableProps> = ({
  emails,
  loading = false,
  onEmailSelect,
  onEmailAction,
  getStatusIcon,
  getStatusBadge,
}) => {
  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="space-y-4 p-6">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center space-x-4">
              <div className="h-4 bg-secondary-200 rounded w-1/4"></div>
              <div className="h-4 bg-secondary-200 rounded w-1/3"></div>
              <div className="h-4 bg-secondary-200 rounded w-1/4"></div>
              <div className="h-4 bg-secondary-200 rounded w-20"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (!emails || emails.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-secondary-500">No emails found</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-secondary-200">
        <thead className="bg-secondary-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Subject
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Sender
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Category
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Date
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-secondary-200">
          {emails.map((email) => (
            <tr
              key={email.id}
              className="hover:bg-secondary-50 cursor-pointer"
              onClick={() => onEmailSelect(email)}
            >
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-medium text-secondary-900">
                  {email.subject || 'No Subject'}
                </div>
                {email.ai_summary && (
                  <div className="text-sm text-secondary-500 truncate max-w-xs">
                    {email.ai_summary}
                  </div>
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-secondary-900">{email.sender_name}</div>
                <div className="text-sm text-secondary-500">{email.sender_email}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className="badge badge-primary">{email.category}</span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center">
                  {getStatusIcon(email.processing_status)}
                  <span className={`ml-2 ${getStatusBadge(email.processing_status)}`}>
                    {email.processing_status}
                  </span>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-500">
                {format(new Date(email.received_date), 'MMM dd, yyyy')}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onEmailSelect(email)
                  }}
                  className="text-primary-600 hover:text-primary-900 mr-2"
                >
                  <Eye className="h-4 w-4" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    // Show action menu
                  }}
                  className="text-secondary-400 hover:text-secondary-600"
                >
                  <MoreVertical className="h-4 w-4" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default EmailTable 