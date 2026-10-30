import { useEffect, useState } from 'react';
import { CloudRain, FlaskConical, MessageCircle } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, type Advice, type TelemetryRow } from '../api';
import { AdviceCard, CROP_LABEL, ErrorNote, Spinner, STAGE_LABEL, UrgencyBanner, fmt } from '../components/ui';

const READINGS = [
  { key: 'moisture', en: 'Soil moisture', ta: 'ஈரப்பதம்', unit: '%' },
  { key: 'N', en: 'Nitrogen', ta: 'தழைச்சத்து', unit: '' },
  { key: 'P', en: 'Phosphorus', ta: 'மணிச்சத்து', unit: '' },
  { key: 'K', en: 'Potassium', ta: 'சாம்பல் சத்து', unit: '' },
  { key: 'pH', en: 'Soil pH', ta: 'கார அமிலம்', unit: '' },
  { key: 'temperature', en: 'Temperature', ta: 'வெப்பநிலை', unit: '°C' },
];

const LINKS = [
  { href: '#/chat', en: 'Ask Uzhavan', ta: 'கேள்வி கேளுங்கள்', Icon: MessageCircle, note: 'Ask in your own words' },
  { href: '#/dosage', en: 'Dose Calculator', ta: 'அளவு கணிப்பு', Icon: FlaskConical, note: 'Water and fertilizer for your field' },
  { href: '#/weather', en: 'Weather', ta: 'வானிலை', Icon: CloudRain, note: '5-day rain and radar' },
];

export default function Home() {
  const [rows, setRows] = useState<TelemetryRow[]>([]);
  const [advice, setAdvice] = useState<Advice | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([api.sample(), api.advice(new FormData())])
      .then(([sample, adv]) => {
        setRows(sample.rows);
        setAdvice(adv);
      })
      .catch((e) => setError(e.message));
  }, []);

  const latest = rows[rows.length - 1];
  const chart = rows.slice(-7).map((r) => ({
    day: String(r.timestamp ?? '').slice(5, 10),
    moisture: Number(r.moisture),
  }));

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-extrabold text-soil-900 sm:text-3xl">
          Vanakkam! <span className="tamil text-leaf-700">வணக்கம்!</span>
        </h1>
        <p className="text-lg text-soil-700">
          {advice
            ? `Your ${CROP_LABEL[advice.crop]?.en.toLowerCase() ?? advice.crop} field · ${STAGE_LABEL[advice.stage] ?? advice.stage} · today's advice`
            : 'Your field today'}
        </p>
      </section>

      {error && <ErrorNote message={error} />}
      {!advice && !error && <Spinner label="Reading your soil sensor and the weather…" />}

      {advice && (
        <>
          <UrgencyBanner urgency={advice.urgency} decision={advice.decision} />
          <AdviceCard
            en={advice.advisory.en.replace(' Estimate only. Confirm with a local agriculture officer.', '')}
            ta={advice.advisory.ta.replace(' இது மதிப்பீடு மட்டுமே. உள்ளூர் வேளாண் அலுவலரிடம் உறுதிப்படுத்தவும்.', '')}
            disclaimer="Estimate only. Confirm with a local agriculture officer."
          />
        </>
      )}

      {latest && (
        <section>
          <h2 className="mb-3 text-lg font-bold text-soil-900">
            Latest sensor readings <span className="tamil text-base text-leaf-700">· சென்சார் அளவீடுகள்</span>
          </h2>
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {READINGS.filter((r) => latest[r.key] != null).map((r) => (
              <li key={r.key} className="card p-3">
                <p className="text-sm font-semibold text-soil-700">{r.en}</p>
                <p className="tamil text-xs text-soil-500">{r.ta}</p>
                <p className="mt-1 text-2xl font-extrabold text-soil-900">
                  {fmt(Number(latest[r.key]), 1)}
                  {r.unit}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {chart.length > 1 && advice && (
        <section className="card p-4">
          <h2 className="text-lg font-bold text-soil-900">
            Soil moisture, last 7 days <span className="tamil text-base text-leaf-700">· 7 நாள் ஈரப்பதம்</span>
          </h2>
          <p className="mb-3 text-sm text-soil-700">
            Water when the line drops below the red mark ({fmt(advice.moisture_thresholds.trigger, 1)}%).
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chart} margin={{ top: 8, right: 16, bottom: 0, left: -12 }}>
                <CartesianGrid stroke="#e8d9c4" strokeDasharray="3 3" />
                <XAxis dataKey="day" stroke="#6b4423" fontSize={13} />
                <YAxis
                  stroke="#6b4423"
                  fontSize={13}
                  unit="%"
                  domain={[
                    (min: number) => Math.floor(Math.min(min, advice.moisture_thresholds.trigger) - 3),
                    (max: number) => Math.ceil(Math.max(max, advice.moisture_thresholds.fc) + 2),
                  ]}
                />
                <Tooltip formatter={(v: number) => [`${v}%`, 'Moisture']} />
                <ReferenceLine
                  y={advice.moisture_thresholds.trigger}
                  stroke="#a3261c"
                  strokeDasharray="6 4"
                  label={{ value: 'Water below', fill: '#a3261c', fontSize: 12, position: 'insideBottomRight' }}
                />
                <ReferenceLine
                  y={advice.moisture_thresholds.fc}
                  stroke="#2e7d32"
                  strokeDasharray="6 4"
                  label={{ value: 'Full', fill: '#2e7d32', fontSize: 12, position: 'insideTopRight' }}
                />
                <Line type="monotone" dataKey="moisture" stroke="#6b4423" strokeWidth={3} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      <section className="grid gap-3 sm:grid-cols-3">
        {LINKS.map(({ href, en, ta, Icon, note }) => (
          <a key={href} href={href} className="card flex items-center gap-3 p-4 transition-colors hover:border-leaf-700">
            <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-leaf-100 text-leaf-700">
              <Icon className="h-6 w-6" aria-hidden />
            </span>
            <span>
              <span className="block font-bold text-soil-900">
                {en} <span className="tamil text-sm font-semibold text-leaf-700">{ta}</span>
              </span>
              <span className="text-sm text-soil-700">{note}</span>
            </span>
          </a>
        ))}
      </section>
    </div>
  );
}
