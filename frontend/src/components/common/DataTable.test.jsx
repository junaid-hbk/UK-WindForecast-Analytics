import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import DataTable from './DataTable.jsx'

const columns = [
  { key: 'name', header: 'Name' },
  { key: 'value', header: 'Value', align: 'right' },
]

describe('DataTable', () => {
  it('renders a caption, headers and rows', () => {
    render(
      <DataTable
        caption="Test caption"
        columns={columns}
        rows={[
          { id: 1, name: 'Alpha', value: '1' },
          { id: 2, name: 'Beta', value: '2' },
        ]}
        getRowKey={(row) => row.id}
      />,
    )

    expect(screen.getByRole('table', { name: 'Test caption' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Name' })).toBeInTheDocument()
    expect(screen.getAllByRole('row')).toHaveLength(3)
    expect(screen.getByText('Alpha')).toBeInTheDocument()
  })

  it('shows the empty message spanning all columns', () => {
    render(
      <DataTable
        caption="Empty table"
        columns={columns}
        rows={[]}
        emptyMessage="Nothing stored here."
      />,
    )

    expect(screen.getByText('Nothing stored here.')).toBeInTheDocument()
    expect(screen.queryByText('Alpha')).not.toBeInTheDocument()
  })

  it('uses the custom renderer for a cell', () => {
    render(
      <DataTable
        caption="Custom cells"
        columns={[{ key: 'value', header: 'Value', render: (row) => `formatted:${row.value}` }]}
        rows={[{ id: 1, value: 9 }]}
        getRowKey={(row) => row.id}
      />,
    )

    expect(screen.getByText('formatted:9')).toBeInTheDocument()
  })
})
