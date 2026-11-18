import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { AppDataProvider } from '../hooks/useAppData.jsx'

/**
 * Render a page inside the real router context and the real data provider, with
 * `src/api/index.js` mocked by the test file.
 */
export function renderWithApp(ui, { route = '/' } = {}) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AppDataProvider>{ui}</AppDataProvider>
    </MemoryRouter>,
  )
}
