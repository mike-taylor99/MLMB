import { BrowserRouter, Routes, Route } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/context/theme'
import { SportProvider } from '@/context/sport'
import { Layout } from '@/components/layout'
import { HomePage } from '@/pages/home'
import { PredictPage } from '@/pages/predict'
import { TeamsPage } from '@/pages/teams'
import { TeamDetailPage } from '@/pages/team-detail'
import { HistoryPage } from '@/pages/history'
import { NotFoundPage } from '@/pages/not-found'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <SportProvider>
          <BrowserRouter>
            <Routes>
              <Route element={<Layout />}>
                <Route index element={<HomePage />} />
                <Route path="predict" element={<PredictPage />} />
                <Route path="teams" element={<TeamsPage />} />
                <Route path="teams/:teamId" element={<TeamDetailPage />} />
                <Route path="history" element={<HistoryPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </SportProvider>
      </QueryClientProvider>
    </ThemeProvider>
  )
}

export default App
