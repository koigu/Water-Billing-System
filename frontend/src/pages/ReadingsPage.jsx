import { useEffect, useState } from 'react'
import { fetchReadings } from '../api/adminApi'

export default function ReadingsPage() {
  const [readings, setReadings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchReadings()
      .then((res) => {
        setReadings(res)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Meter Readings</h2>
          <p className="page-description">Latest readings per customer</p>
        </div>
      </div>

      {loading && <div>Loading readings...</div>}
      {error && <div style={{ color: '#dc3545' }}>Error: {error}</div>}

      {!loading && readings.length > 0 && (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Customer ID</th>
                <th>Reading (m³)</th>
                <th>Recorded At</th>
              </tr>
            </thead>
            <tbody>
              {readings.map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td>
                  <td>{r.customer_id}</td>
                  <td>{r.reading_value}</td>
                  <td>{new Date(r.recorded_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
