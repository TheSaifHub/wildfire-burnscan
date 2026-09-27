const API_BASE = "http://localhost:8000";

export default async function HomePage() {
  const res = await fetch(`${API_BASE}/fires`, { cache: "no-store" });
  const fires = await res.json();

  return (
    <main className="max-w-3xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-2">Wildfire BurnScan</h1>
      <p className="text-gray-600 mb-8">
        Wildfire burn severity, mapped from satellite imagery and validated
        against official government ground truth.
      </p>

      <h2 className="text-lg font-semibold mb-3">Select a fire</h2>
      <ul className="space-y-3">
        {fires.map((fire) => (
          <li key={fire.id}>
            <a
              href={`/fires/${fire.id}`}
              className="block border rounded-lg p-4 hover:bg-gray-50 transition"
            >
              <div className="font-semibold">{fire.name}</div>
              <div className="text-sm text-gray-600">
                {fire.location} &middot; Ignited {fire.ignition_date}
              </div>
            </a>
          </li>
        ))}
      </ul>
    </main>
  );
}
