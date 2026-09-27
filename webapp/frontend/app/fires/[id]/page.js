import MapLoader from "./MapLoader";

const API_BASE = "http://localhost:8000";

export default async function FireDetailPage({ params }) {
  const { id } = await params;
  const res = await fetch(`${API_BASE}/fires/${id}`, { cache: "no-store" });
  const fire = await res.json();

  const { stats } = fire;

  return (
    <main className="max-w-4xl mx-auto p-8">
      <a href="/" className="text-sm text-blue-600 hover:underline">
        &larr; All fires
      </a>

      <h1 className="text-3xl font-bold mt-2">{fire.name}</h1>
      <p className="text-gray-600 mb-6">
        {fire.location} &middot; Ignited {fire.ignition_date} &middot; Before:{" "}
        {fire.before_date} &middot; After: {fire.after_date}
      </p>

      <MapLoader bounds={fire.bounds} images={fire.images} apiBase={API_BASE} />

      <section className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-6">
        <div>
          <h2 className="font-semibold mb-2">Summary</h2>
          <p>Total area analyzed: <strong>{stats.total_area_km2} km²</strong></p>
          <table className="mt-2 text-sm w-full">
            <tbody>
              <tr>
                <td className="py-1">High severity</td>
                <td className="text-right font-medium">{stats.severity_breakdown_pct.high}%</td>
              </tr>
              <tr>
                <td className="py-1">Moderate severity</td>
                <td className="text-right font-medium">{stats.severity_breakdown_pct.moderate}%</td>
              </tr>
              <tr>
                <td className="py-1">Low severity</td>
                <td className="text-right font-medium">{stats.severity_breakdown_pct.low}%</td>
              </tr>
              <tr>
                <td className="py-1">Unburned / very low</td>
                <td className="text-right font-medium">{stats.severity_breakdown_pct.unburned}%</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div>
          <h2 className="font-semibold mb-2">Model validation</h2>
          <p className="text-sm">
            U-Net: <strong>{stats.validation.unet_agreement_pct}%</strong> agreement
            with official MTBS ground truth
          </p>
          <p className="text-sm text-gray-600">
            vs. simple dNBR-threshold baseline: {stats.validation.baseline_agreement_pct}%
          </p>
          <p className="text-xs text-gray-500 mt-3">{stats.validation.note}</p>
        </div>
      </section>
    </main>
  );
}
