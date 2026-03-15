// ============================================================================
// 404 — catch-all not found page
// ============================================================================

import { Link } from 'react-router'
import { Button } from '@/components/ui/button'
import { useDocumentTitle } from '@/lib/use-document-title'

export function NotFoundPage() {
  useDocumentTitle('Page Not Found')
  return (
    <div className="flex flex-col items-center justify-center py-20 space-y-4">
      <h1 className="text-6xl font-bold text-muted-foreground">404</h1>
      <p className="text-lg text-muted-foreground">Page not found</p>
      <Button asChild>
        <Link to="/">Go home</Link>
      </Button>
    </div>
  )
}
