import Card from '../common/Card.jsx'
import EmptyState from '../common/EmptyState.jsx'

/**
 * Common frame for every chart: consistent height, axis context and an
 * accessible description. Charts are aria-labelled as images; the same data is
 * always available in an adjacent table.
 */
export default function ChartFrame({
  title,
  description,
  action,
  footnote,
  height = 340,
  isEmpty = false,
  emptyMessage = 'No chartable values were returned for this selection.',
  children,
}) {
  return (
    <Card title={title} description={description} actions={action} footer={footnote}>
      {isEmpty ? (
        <EmptyState title="Nothing to plot" description={emptyMessage} />
      ) : (
        <div
          className="w-full"
          style={{ height }}
          role="img"
          aria-label={`${title}. ${description ?? ''}`}
        >
          {children}
        </div>
      )}
    </Card>
  )
}
