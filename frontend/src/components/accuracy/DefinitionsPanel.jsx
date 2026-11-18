import Card from '../common/Card.jsx'
import DefinitionList from '../common/DefinitionList.jsx'

const ORDER = ['error', 'mae', 'rmse', 'wape', 'bias', 'bias_pct', 'coverage', 'n']
const LABELS = {
  error: 'Error (e)',
  mae: 'MAE',
  rmse: 'RMSE',
  wape: 'WAPE',
  bias: 'Bias',
  bias_pct: 'Bias %',
  coverage: 'Coverage',
  n: 'n (observations)',
}

export default function DefinitionsPanel({ definitions = {}, notes = [], metaNotes = [] }) {
  const items = ORDER.filter((key) => definitions[key]).map((key) => ({
    term: LABELS[key] ?? key,
    description: definitions[key],
  }))

  return (
    <Card
      title="How these metrics are defined"
      description="Served by the API with the metrics themselves, so the dashboard and the backend cannot drift apart."
      footer={
        <div className="space-y-1">
          {notes.map((note) => (
            <p key={note}>{note}</p>
          ))}
          {metaNotes.map((note) => (
            <p key={note} className="text-slate-500">
              {note}
            </p>
          ))}
        </div>
      }
    >
      <DefinitionList items={items} emptyMessage="The API returned no metric definitions." />
    </Card>
  )
}
