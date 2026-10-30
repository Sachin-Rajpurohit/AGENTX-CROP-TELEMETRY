import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { ChevronDown, Droplets, FlaskConical, Gauge, Leaf, RotateCcw, Sprout } from 'lucide-react';
import { api, type Advice, type Crops } from '../api';
import { usePersistedState } from '../persist';
import { useFarms } from '../farmStore';
import {
  AdviceCard,
  CROP_LABEL,
  ErrorNote,
  SOIL_LABEL,
  STAGE_LABEL,
  Spinner,
  UrgencyBanner,
  fmt,
} from '../components/ui';

const BAG_KG = 50;
type Source = 'farm' | 'manual' | 'upload';

function Field({ label, ta, children }: { label: string; ta?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block font-semibold text-soil-800">
        {label} {ta && <span className="tamil text-sm font-medium text-soil-500">· {ta}</span>}
      </span>
      {children}
    </label>
  );
}

const inputCls =
  'w-full rounded-xl border border-soil-300 bg-white px-3 py-2.5 text-lg focus:border-leaf-700 focus:outline-none focus:ring-2 focus:ring-leaf-200';

function MoistureBar({ advice }: { advice: Advice }) {
  const { fc, pwp, trigger } = advice.moisture_thresholds;
  const now = advice.readings.moisture;
  const max = Math.max(fc * 1.25, now + 5);
  const pct = (v: number) => `${Math.min(100, (v / max) * 100)}%`;
  return (
    <div>
      <div className="relative h-5 overflow-hidden rounded-full bg-soil-100">
        <div className="absolute inset-y-0 left-0 bg-alert-100" style={{ width: pct(trigger) }} />
        <div className="absolute inset-y-0 bg-leaf-100" style={{ left: pct(trigger), width: `calc(${pct(fc)} - ${pct(trigger)})` }} />
        <div className="absolute inset-y-0 w-1.5 -translate-x-1/2 rounded bg-soil-900" style={{ left: pct(now) }} />
      </div>
      <div className="mt-1 flex justify-between text-xs text-soil-700">
        <span>Wilting {fmt(pwp)}%</span>
        <span className="font-semibold text-alert-700">Water below {fmt(trigger, 1)}%</span>
        <span>Full {fmt(fc)}%</span>
      </div>
    </div>
  );
}

function Tile({ icon, title, ta, children }: { icon: ReactNode; title: string; ta: string; children: ReactNode }) {
  return (
    <section className="card p-4">
      <h3 className="mb-3 flex items-center gap-2 font-bold text-soil-800">
        {icon} {title} <span className="tamil text-sm font-medium text-soil-500">· {ta}</span>
      </h3>
      {children}
    </section>
  );
}

export function AdviceResult({ advice }: { advice: Advice }) {
  const [details, setDetails] = useState(false);
  const water = advice.doses?.irrigation;
  const fert = advice.doses?.fertilizer;
  const area = fert?.area_acres;
  const fit = advice.crop_fit;
  const products = fert
    ? [
        { name: 'Urea', ta: 'யூரியா', kg: fert.kg_area.urea_net },
        { name: 'DAP', ta: 'டிஏபி', kg: fert.kg_area.dap },
        { name: 'MOP (Potash)', ta: 'பொட்டாஷ்', kg: fert.kg_area.mop },
      ]
    : [];

  return (
    <div className="space-y-4">
      <UrgencyBanner urgency={advice.urgency} decision={advice.decision} />

      <div className="grid gap-4 md:grid-cols-3">
        <Tile icon={<Droplets className="h-5 w-5 text-leaf-700" />} title="Water today" ta="இன்றைய நீர்">
          {!water ? (
            <p className="text-soil-700">No dose: check the sensor first.</p>
          ) : water.irrigate ? (
            <>
              <p className="text-3xl font-extrabold text-leaf-800">{fmt(water.litres_per_day)} L</p>
              <p className="text-soil-700">
                {advice.doses!.method === 'flood' ? 'Flood' : 'Drip'} ·{' '}
                {water.events_per_day === 1 ? 'one session' : `${water.events_per_day} sessions`}
                {advice.rules_fired.includes('R4_HEAT_DAWN') && ' · before 7 am'}
              </p>
              {water.days_to_refill > 1 && (
                <p className="mt-1 text-sm text-soil-700">Repeat for about {water.days_to_refill} days.</p>
              )}
            </>
          ) : (
            <p className="text-2xl font-bold text-leaf-800">No water needed</p>
          )}
        </Tile>

        <Tile icon={<FlaskConical className="h-5 w-5 text-leaf-700" />} title="Fertilizer" ta="உரம்">
          {!fert ? (
            <p className="text-soil-700">No N/P/K readings, so no fertilizer dose.</p>
          ) : products.every((p) => p.kg === 0) ? (
            <p className="text-2xl font-bold text-leaf-800">Nutrients are enough</p>
          ) : (
            <ul className="space-y-1.5">
              {products.map((p) => (
                <li key={p.name} className="flex items-baseline justify-between gap-2">
                  <span className="font-semibold">
                    {p.name} <span className="tamil text-sm text-soil-500">{p.ta}</span>
                  </span>
                  <span className="text-right">
                    <span className="text-xl font-extrabold text-soil-900">{fmt(p.kg, 1)} kg</span>
                    <span className="block text-xs text-soil-700">≈ {fmt(p.kg / BAG_KG, 1)} bags of 50 kg</span>
                  </span>
                </li>
              ))}
              <li className="pt-1 text-xs text-soil-700">For {fmt(area ?? 1, 1)} acre(s). Urea already counts the N in DAP.</li>
            </ul>
          )}
        </Tile>

        <Tile icon={<Gauge className="h-5 w-5 text-leaf-700" />} title="Soil moisture" ta="மண் ஈரப்பதம்">
          <p className="text-3xl font-extrabold text-soil-900">{fmt(advice.readings.moisture, 1)}%</p>
          <MoistureBar advice={advice} />
        </Tile>
      </div>

      <AdviceCard
        en={advice.advisory.en.replace(' Estimate only. Confirm with a local agriculture officer.', '')}
        ta={advice.advisory.ta.replace(' இது மதிப்பீடு மட்டுமே. உள்ளூர் வேளாண் அலுவலரிடம் உறுதிப்படுத்தவும்.', '')}
        disclaimer="Estimate only. Confirm with a local agriculture officer."
      />

      <div className="grid gap-4 md:grid-cols-2">
        <Tile icon={<Leaf className="h-5 w-5 text-leaf-700" />} title={`Confidence: ${advice.confidence.level}`} ta="நம்பகத்தன்மை">
          <div className="h-3 overflow-hidden rounded-full bg-soil-100">
            <div className="h-full bg-leaf-700" style={{ width: `${advice.confidence.score * 100}%` }} />
          </div>
          <p className="mt-2 text-soil-800">
            {advice.confidence.reasons.length
              ? `Lowered because: ${advice.confidence.reasons.join('; ')}.`
              : 'Sensor data looks complete and the live forecast was used.'}
          </p>
        </Tile>

        <Tile icon={<Sprout className="h-5 w-5 text-leaf-700" />} title="Crops that suit this soil" ta="பொருத்தமான பயிர்கள்">
          {fit.available && fit.best_matches ? (
            <>
              <ol className="space-y-1">
                {fit.best_matches.map((m) => (
                  <li key={m.crop} className="flex justify-between">
                    <span className="font-semibold capitalize">{m.crop}</span>
                    <span className="text-soil-700">
                      {m.in_range} of {m.of} conditions match
                    </span>
                  </li>
                ))}
              </ol>
              <p className="mt-2 text-xs text-soil-700">
                {fit.selected_crop
                  ? `Your ${advice.crop}: ${fit.selected_crop.in_range} of ${fit.selected_crop.of} conditions match.`
                  : `${CROP_LABEL[advice.crop]?.en ?? advice.crop} is not in the 22-crop Kaggle dataset.`}
              </p>
            </>
          ) : (
            <p className="text-soil-700">Not enough readings to compare crops.</p>
          )}
        </Tile>
      </div>

      <div className="card">
        <button
          type="button"
          onClick={() => setDetails(!details)}
          className="flex w-full items-center justify-between px-4 py-3 text-left font-semibold text-soil-700"
          aria-expanded={details}
        >
          How this was calculated
          <ChevronDown className={`h-4 w-4 transition-transform ${details ? 'rotate-180' : ''}`} />
        </button>
        {details && (
          <div className="space-y-3 border-t border-soil-200 px-4 py-3 text-sm text-soil-800">
            <p>
              <b>Weather used:</b> {fmt(advice.weather.rain_mm_48h, 1)} mm rain in 48 h ({fmt(advice.weather.rain_prob_48h)}%
              chance), max {fmt(advice.weather.tmax_next3, 1)}°C · source: {advice.weather.source}
            </p>
            <p>
              <b>Rules applied:</b> {advice.reasons.join(' · ')}
            </p>
            {advice.quality.issues.length > 0 && (
              <p>
                <b>Sensor checks:</b> {advice.quality.issues.map((i) => i.detail).join(' · ')}
              </p>
            )}
            <ul className="list-disc space-y-0.5 pl-5">
              {advice.assumptions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Dosage() {
  const [crops, setCrops] = useState<Crops | null>(null);
  // Form choices and the last result are saved, so they survive page switches and refreshes.
  // The CSV file itself cannot be saved, so an upload must be chosen again after leaving.
  const [crop, setCrop] = usePersistedState('uzhavan-dose-crop', 'tomato');
  const [stage, setStage] = usePersistedState('uzhavan-dose-stage', '');
  const [area, setArea] = usePersistedState('uzhavan-dose-area', '1');
  const [irrigation, setIrrigation] = usePersistedState('uzhavan-dose-irrigation', 'drip');
  const [soil, setSoil] = usePersistedState('uzhavan-dose-soil', 'clay_loam');
  const [savedSource, setSource] = usePersistedState<Source | 'sample'>('uzhavan-dose-source', 'farm');
  const source: Source = savedSource === 'sample' ? 'farm' : savedSource;  // 'sample' was the old name
  const { selected: farm } = useFarms();
  const [manual, setManual] = usePersistedState('uzhavan-dose-manual', { moisture: '', n: '', p: '', k: '' });
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = usePersistedState<{ advice: Advice; at: string } | null>('uzhavan-dose-result', null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.crops().then(setCrops).catch((e) => setError(e.message));
  }, []);

  const stages = crops?.[crop]?.stages ?? [];
  const flooded = crops?.[crop]?.flooded ?? false;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const form = new FormData();
    form.set('crop', crop);
    if (stage) form.set('stage', stage);
    form.set('area_acres', area);
    form.set('irrigation', flooded ? 'flood' : irrigation);
    form.set('soil', soil);
    if (farm) form.set('farm_id', farm.id);  // the farm's location is used for the weather
    if (source === 'farm') {
      if (!farm) return setError('Add a farm on the Farms page first, or type readings yourself.');
      if (!farm.has_telemetry) return setError(`${farm.name} has no sensor data yet. Upload a CSV on the Farms page.`);
    }
    if (source === 'manual') {
      if (!manual.moisture) return setError('Enter at least the soil moisture.');
      Object.entries(manual).forEach(([k, v]) => v && form.set(k, v));
    }
    if (source === 'upload') {
      if (!file) return setError('Choose a CSV file first.');
      form.set('csv', file);
    }
    setBusy(true);
    setError('');
    try {
      setResult({ advice: await api.advice(form), at: new Date().toISOString() });
    } catch (err) {
      setError((err as Error).message);
      setResult(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-soil-900">
          Dose Calculator <span className="tamil text-xl text-leaf-700">· உர, நீர் அளவு கணிப்பு</span>
        </h1>
        <p className="text-soil-700">Tell us about your field. We compute the exact water and fertilizer for it.</p>
      </div>

      {farm && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-leaf-50 px-4 py-3">
          <p className="text-leaf-800">
            Farm: <b>{farm.name}</b> · {farm.location.name}
          </p>
          <button
            type="button"
            onClick={() => {
              setCrop(farm.crop);
              setStage(farm.stage ?? '');
              setArea(String(farm.area_acres));
              setIrrigation(farm.irrigation);
              setSoil(farm.soil);
              setSource('farm');
            }}
            className="rounded-full border border-leaf-700 bg-white px-4 py-1.5 text-sm font-bold text-leaf-800 hover:bg-leaf-100"
          >
            Fill from my farm · <span className="tamil">என் வயல்</span>
          </button>
        </div>
      )}

      <form onSubmit={submit} className="card grid gap-4 p-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Crop" ta="பயிர்">
          <select
            className={inputCls}
            value={crop}
            onChange={(e) => {
              setCrop(e.target.value);
              setStage('');
            }}
          >
            {Object.keys(crops ?? CROP_LABEL).map((c) => (
              <option key={c} value={c}>
                {CROP_LABEL[c]?.en ?? c} – {CROP_LABEL[c]?.ta ?? ''}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Growth stage" ta="வளர்ச்சி நிலை">
          {stages.length ? (
            <select className={inputCls} value={stage} onChange={(e) => setStage(e.target.value)}>
              <option value="">Not sure (about 1 month old)</option>
              {stages.map((s) => (
                <option key={s} value={s}>
                  {STAGE_LABEL[s] ?? s}
                </option>
              ))}
            </select>
          ) : (
            <p className="rounded-xl bg-soil-100 px-3 py-2.5 text-soil-700">Whole-season target for this crop</p>
          )}
        </Field>

        <Field label="Field size (acres)" ta="நில அளவு (ஏக்கர்)">
          <input
            className={inputCls}
            type="number"
            min="0.1"
            step="0.1"
            value={area}
            onChange={(e) => setArea(e.target.value)}
            required
          />
        </Field>

        <Field label="Watering method" ta="பாசன முறை">
          {flooded ? (
            <p className="rounded-xl bg-soil-100 px-3 py-2.5 text-soil-700">Flooding (paddy is kept ponded)</p>
          ) : (
            <select className={inputCls} value={irrigation} onChange={(e) => setIrrigation(e.target.value)}>
              <option value="drip">Drip – சொட்டு நீர்</option>
              <option value="flood">Flood / furrow – வாய்க்கால்</option>
            </select>
          )}
        </Field>

        <Field label="Soil type" ta="மண் வகை">
          <select className={inputCls} value={soil} onChange={(e) => setSoil(e.target.value)}>
            {Object.entries(SOIL_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Sensor data" ta="சென்சார் தரவு">
          <select className={inputCls} value={source} onChange={(e) => setSource(e.target.value as Source)}>
            <option value="farm">{farm ? `${farm.name} sensor data` : 'My farm sensor data'}</option>
            <option value="manual">Type readings myself</option>
            <option value="upload">Upload a CSV file</option>
          </select>
        </Field>

        {source === 'manual' && (
          <div className="grid grid-cols-2 gap-3 sm:col-span-2 sm:grid-cols-4 lg:col-span-3">
            {(
              [
                ['moisture', 'Soil moisture %'],
                ['n', 'Nitrogen (N)'],
                ['p', 'Phosphorus (P)'],
                ['k', 'Potassium (K)'],
              ] as const
            ).map(([key, label]) => (
              <Field key={key} label={label}>
                <input
                  className={inputCls}
                  type="number"
                  step="any"
                  min="0"
                  value={manual[key]}
                  onChange={(e) => setManual({ ...manual, [key]: e.target.value })}
                  required={key === 'moisture'}
                />
              </Field>
            ))}
          </div>
        )}

        {source === 'upload' && (
          <div className="sm:col-span-2 lg:col-span-3">
            <Field label="CSV with a moisture column (and N, P, K, timestamp if you have them)">
              <input
                className={`${inputCls} file:mr-3 file:rounded-lg file:border-0 file:bg-soil-100 file:px-3 file:py-1.5 file:font-semibold`}
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </Field>
          </div>
        )}

        <div className="sm:col-span-2 lg:col-span-3">
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-xl bg-leaf-700 px-6 py-3.5 text-lg font-bold text-white hover:bg-leaf-800 disabled:opacity-60 sm:w-auto"
          >
            Calculate · <span className="tamil">கணக்கிடு</span>
          </button>
        </div>
      </form>

      {error && <ErrorNote message={error} />}
      {busy && <Spinner label="Checking soil trend, weather and doses…" />}
      {result && !busy && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-soil-700">
            <span>
              Result for {CROP_LABEL[result.advice.crop]?.en ?? result.advice.crop}, calculated at{' '}
              {new Date(result.at).toLocaleString('en-IN', { hour: 'numeric', minute: '2-digit', day: 'numeric', month: 'short' })}
              . Calculate again for the latest weather.
            </span>
            <button
              type="button"
              onClick={() => setResult(null)}
              className="flex items-center gap-1.5 rounded-full border border-soil-300 bg-white px-3 py-1.5 font-semibold text-soil-700 hover:bg-soil-100"
            >
              <RotateCcw className="h-4 w-4" aria-hidden /> Clear · <span className="tamil">அழி</span>
            </button>
          </div>
          <AdviceResult advice={result.advice} />
        </div>
      )}
    </div>
  );
}
