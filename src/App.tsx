import { HashRouter, Routes, Route } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { ComparePage } from './pages/ComparePage'
import { DrillDownPage } from './pages/DrillDownPage'
import { SearchPage } from './pages/SearchPage'
import { InsightsPage } from './pages/InsightsPage'
import { GuidePage } from './pages/GuidePage'
import { DepartmentsPage } from './pages/DepartmentsPage'

function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<InsightsPage />} />
          <Route path="overview" element={<DashboardPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="category/:code" element={<DrillDownPage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="guide" element={<GuidePage />} />
          <Route path="departments" element={<DepartmentsPage />} />
        </Route>
      </Routes>
    </HashRouter>
  )
}

export default App
