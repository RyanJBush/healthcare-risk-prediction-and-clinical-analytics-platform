import {
  Area,
  ComposedChart,
  CartesianGrid,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

type Point = {
  time: number
  survival_probability: number
  ci_lower: number
  ci_upper: number
  tier: 'Low' | 'Medium' | 'High'
}

type Props = {
  curves: Record<string, Point[]>
}

const COLORS: Record<string, string> = {
  Low: '#16a34a',
  Medium: '#f59e0b',
  High: '#dc2626',
}

export default function SurvivalCurveChart({ curves }: Props) {
  const merged = Object.entries(curves).flatMap(([tier, points]) =>
    points.map((p) => ({
      time: p.time,
      [`${tier}_survival`]: p.survival_probability,
      [`${tier}_lower`]: p.ci_lower,
      [`${tier}_upper`]: p.ci_upper,
    })),
  )

  const byTime = Object.values(
    merged.reduce((acc: Record<number, Record<string, number>>, row) => {
      const key = row.time
      acc[key] = { ...(acc[key] || { time: key }), ...row }
      return acc
    }, {}),
  ).sort((a, b) => a.time - b.time)

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={byTime}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" />
          <YAxis domain={[0, 1]} />
          <Tooltip />
          <Legend />
          {Object.keys(COLORS).map((tier) => (
            <>
              <Area key={`${tier}-upper`} type="monotone" dataKey={`${tier}_upper`} stroke="none" fill={COLORS[tier]} fillOpacity={0.08} />
              <Area key={`${tier}-lower`} type="monotone" dataKey={`${tier}_lower`} stroke="none" fill="#ffffff" fillOpacity={1} />
              <Line key={`${tier}-line`} type="stepAfter" dataKey={`${tier}_survival`} stroke={COLORS[tier]} dot={false} name={`${tier} survival`} />
            </>
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
