import { Compass } from 'lucide-react'
import { Link } from 'react-router-dom'

import { buttonStyles } from '../components/common/Button'
import { EmptyState } from '../components/common/Feedback'
import { PageHeader } from '../components/common/PageHeader'
import { Panel } from '../components/common/Panel'

export function NotFound() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Not found"
        title="Page not found"
        description="The route you requested does not exist in this workspace."
      />
      <Panel>
        <EmptyState
          icon={Compass}
          title="Nothing lives at this address"
          description="Use the sidebar to return to the dashboard, browse the library, or ask a question."
          action={
            <Link to="/" className={buttonStyles('primary', 'sm')}>
              Back to dashboard
            </Link>
          }
        />
      </Panel>
    </div>
  )
}
