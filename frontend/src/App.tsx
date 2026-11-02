import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Suspense, lazy } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { LoadingPanel } from './components/common/Feedback'
import { AppShell } from './components/layout/AppShell'

const Dashboard = lazy(() =>
  import('./pages/Dashboard').then((module) => ({
    default: module.Dashboard,
  })),
)
const AIChat = lazy(() =>
  import('./pages/AIChat').then((module) => ({
    default: module.AIChat,
  })),
)
const Library = lazy(() =>
  import('./pages/Library').then((module) => ({
    default: module.Library,
  })),
)
const Import = lazy(() =>
  import('./pages/Import').then((module) => ({
    default: module.Import,
  })),
)
const Conversation = lazy(() =>
  import('./pages/Conversation').then((module) => ({
    default: module.Conversation,
  })),
)
const Settings = lazy(() =>
  import('./pages/Settings').then((module) => ({
    default: module.Settings,
  })),
)
const NotFound = lazy(() =>
  import('./pages/NotFound').then((module) => ({
    default: module.NotFound,
  })),
)

function PageFallback() {
  return (
    <div className="space-y-6" role="status" aria-live="polite">
      <LoadingPanel rows={5} label="Loading page" />
    </div>
  )
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell>
          <Suspense fallback={<PageFallback />}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/chat" element={<AIChat />} />
              <Route path="/library" element={<Library />} />
              <Route path="/import" element={<Import />} />
              <Route
                path="/conversations/:conversationId"
                element={<Conversation />}
              />
              <Route path="/settings" element={<Settings />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </AppShell>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
