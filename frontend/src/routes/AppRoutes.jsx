import { Navigate, Route, Routes } from 'react-router-dom'

import AppLayout from '../layouts/AppLayout.jsx'
import Dashboard from '../pages/Dashboard.jsx'
import DataSources from '../pages/DataSources.jsx'
import ForecastAccuracy from '../pages/ForecastAccuracy.jsx'
import ForecastExplorer from '../pages/ForecastExplorer.jsx'
import NotFound from '../pages/NotFound.jsx'
import ProcurementInsights from '../pages/ProcurementInsights.jsx'

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="forecast" element={<ForecastExplorer />} />
        <Route path="accuracy" element={<ForecastAccuracy />} />
        <Route path="procurement" element={<ProcurementInsights />} />
        <Route path="data" element={<DataSources />} />
        <Route path="dashboard" element={<Navigate to="/" replace />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
