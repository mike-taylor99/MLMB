import { BrowserRouter, Routes, Route } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/context/theme'
import { SportProvider } from '@/context/sport'
import { AuthProvider } from '@/context/auth'
import { Layout } from '@/components/layout'
import { RequireAuth } from '@/components/require-auth'
import { HomePage } from '@/pages/home'
import { PredictPage } from '@/pages/predict'
import { TeamsPage } from '@/pages/teams'
import { TeamDetailPage } from '@/pages/team-detail'
import { HistoryPage } from '@/pages/history'
import { NotFoundPage } from '@/pages/not-found'
import { LoginPage } from '@/pages/login'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <QueryClientProvider client={queryClient}>
          <SportProvider>
            <BrowserRouter>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route element={<Layout />}>
                  <Route index element={<HomePage />} />
                  <Route element={<RequireAuth />}>
                    <Route path="predict" element={<PredictPage />} />
                    <Route path="history" element={<HistoryPage />} />
                  </Route>
                  <Route path="teams" element={<TeamsPage />} />
                  <Route path="teams/:teamId" element={<TeamDetailPage />} />
                  <Route path="*" element={<NotFoundPage />} />
                </Route>
              </Routes>
            </BrowserRouter>
          </SportProvider>
        </QueryClientProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App
