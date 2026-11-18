import { AppDataProvider } from './hooks/useAppData.jsx'
import AppRoutes from './routes/AppRoutes.jsx'

/**
 * Application shell.
 *
 * `AppDataProvider` fetches platform metadata and the loaded data window once,
 * so pages never guess a default date range or hard-code cutoff policies.
 */
export default function App() {
  return (
    <AppDataProvider>
      <AppRoutes />
    </AppDataProvider>
  )
}
