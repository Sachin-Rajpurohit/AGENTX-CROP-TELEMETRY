import { useState, type FormEvent, type ReactNode } from 'react';
import { CalendarDays, CheckCircle2, Download, MapPin, Pencil, Plus, Ruler, Trash2, Upload } from 'lucide-react';
import { api, type Crops, type Farm, type FarmInput, type Place } from '../api';
import LocationPicker from '../components/LocationPicker';
import { ErrorNote, SOIL_LABEL, STAGE_LABEL, Spinner, fmt } from '../components/ui';
import { cropName, cropTamil, useCrops } from '../crops';
import { loadFarms, selectFarm, useFarms } from '../farmStore';

const inputCls =
  'w-full rounded-xl border border-soil-300 bg-white px-3 py-2.5 text-lg focus:border-leaf-700 focus:outline-none focus:ring-2 focus:ring-leaf-200';

export type Unit = Farm['area_unit'];
export const UNITS: { id: Unit; en: string; ta: string; perAcre: number }[] = [
  { id: 'acre', en: 'Acres', ta: 'ஏக்கர்', perAcre: 1 },
  { id: 'cent', en: 'Cents', ta: 'சென்ட்', perAcre: 100 },
  { id: 'hectare', en: 'Hectares', ta: 'ஹெக்டேர்', perAcre: 0.404686 },
];
export const toAcres = (value: number, unit: Unit) => value / UNITS.find((u) => u.id === unit)!.perAcre;
export const fromAcres = (acres: number, unit: Unit) => acres * UNITS.find((u) => u.id === unit)!.perAcre;
const today = () => new Date().toISOString().slice(0, 10);

export function farmSize(farm: Farm) {
  const unit = UNITS.find((u) => u.id === (farm.area_unit ?? 'acre'))!;
  return `${fmt(fromAcres(farm.area_acres, unit.id), 2)} ${unit.en.toLowerCase()}`;
}

async function downloadTemplate() {
  const sample = await fetch('/api/sample').then((r) => r.json());
  const url = URL.createObjectURL(new Blob([sample.csv], { type: 'text/csv' }));
  const a = Object.assign(document.createElement('a'), { href: url, download: 'sensor_template.csv' });
  a.click();
  URL.revokeObjectURL(url);
}

function Field({ label, ta, hint, children }: { label: string; ta?: string; hint?: string; children: ReactNode }) {
  return (
    <div>
      <span className="mb-1 block font-semibold text-soil-800">
        {label} {ta && <span className="tamil text-sm font-medium text-soil-500">· {ta}</span>}
      </span>
      {children}
      {hint && <span className="mt-1 block text-sm text-soil-700">{hint}</span>}
    </div>
  );
}

function FarmForm({ initial, crops, onDone }: { initial: Farm | null; crops: Crops | null; onDone: (farm?: Farm) => void }) {
  const [name, setName] = useState(initial?.name ?? '');
  const [crop, setCrop] = useState(initial?.crop ?? 'tomato');
  const [plantedOn, setPlantedOn] = useState(initial?.planted_on ?? '');
  const [stage, setStage] = useState(initial?.stage ?? '');
  const [unit, setUnit] = useState<Unit>(initial?.area_unit ?? 'acre');
  const [size, setSize] = useState(initial ? String(+fromAcres(initial.area_acres, initial.area_unit ?? 'acre').toFixed(2)) : '');
  const [irrigation, setIrrigation] = useState<Farm['irrigation']>(initial?.irrigation ?? 'drip');
  const [soil, setSoil] = useState(initial?.soil ?? 'clay_loam');
  const [location, setLocation] = useState<Place | null>(initial?.location ?? null);
  const [sensor, setSensor] = useState<'upload' | 'sample' | 'later'>(initial?.has_telemetry ? 'later' : 'upload');
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const info = crops?.[crop];
  const stages = info?.stages ?? [];
  const flooded = info?.flooded ?? false;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!location) return setError('Choose where the farm is: search your village or town, or use your location.');
    if (!(Number(size) > 0)) return setError('Enter the size of the farm.');
    if (sensor === 'upload' && !file && !initial?.has_telemetry) return setError('Choose the sensor CSV file, or pick another option.');
    const body: FarmInput = {
      name: name.trim(),
      crop,
      stage: stage || null,
      planted_on: plantedOn || null,
      area_acres: +toAcres(Number(size), unit).toFixed(4),
      area_unit: unit,
      irrigation: flooded ? 'flood' : irrigation,
      soil,
      location,
    };
    setBusy(true);
    setError('');
    try {
      let saved = initial ? await api.updateFarm(initial.id, body) : await api.createFarm(body);
      if (sensor === 'upload' && file) saved = (await api.uploadFarmTelemetry(saved.id, file)).farm;
      if (sensor === 'sample') saved = (await api.useSampleData(saved.id)).farm;
      onDone(saved);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="card space-y-5 p-4 sm:p-6">
      <h2 className="text-xl font-bold text-soil-900">
        {initial ? `Edit ${initial.name}` : 'Add your farm'}{' '}
        <span className="tamil text-lg text-leaf-700">· {initial ? 'வயலைத் திருத்து' : 'உங்கள் வயலைச் சேர்க்கவும்'}</span>
      </h2>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Farm name" ta="வயல் பெயர்">
          <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Field near the well" maxLength={60} required />
        </Field>

        <Field label="Crop" ta="பயிர்">
          <select className={inputCls} value={crop} onChange={(e) => { setCrop(e.target.value); setStage(''); }}>
            {Object.entries(crops ?? { tomato: { en: 'Tomato', ta: 'தக்காளி' } }).map(([c, v]) => (
              <option key={c} value={c}>
                {v.en} – {v.ta}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Sowing / transplanting date" ta="நடவு தேதி"
          hint={stages.length ? 'Used to work out the growth stage automatically.' : 'Optional for this crop.'}>
          <div className="relative">
            <CalendarDays className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-soil-500" aria-hidden />
            <input className={`${inputCls} pl-10`} type="date" max={today()} value={plantedOn}
              onChange={(e) => setPlantedOn(e.target.value)} />
          </div>
        </Field>

        <Field label="Growth stage" ta="வளர்ச்சி நிலை">
          {stages.length ? (
            <select className={inputCls} value={stage} onChange={(e) => setStage(e.target.value)}>
              <option value="">{plantedOn ? 'Work out from the planting date' : 'Not sure'}</option>
              {stages.map((s) => (
                <option key={s} value={s}>
                  {STAGE_LABEL[s] ?? s}
                </option>
              ))}
            </select>
          ) : (
            <p className="rounded-xl bg-soil-100 px-3 py-2.5 text-soil-700">One target for the whole season</p>
          )}
        </Field>

        <Field label="Farm size" ta="நில அளவு">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Ruler className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-soil-500" aria-hidden />
              <input className={`${inputCls} pl-10`} type="number" min="0.01" step="any" value={size}
                onChange={(e) => setSize(e.target.value)} placeholder="e.g. 2" required />
            </div>
            <select
              className={`${inputCls} w-48 shrink-0`}
              value={unit}
              onChange={(e) => {
                // Keep the same land: convert the number into the new unit.
                const next = e.target.value as Unit;
                if (Number(size) > 0) setSize(String(+fromAcres(toAcres(Number(size), unit), next).toFixed(2)));
                setUnit(next);
              }}
              aria-label="Unit"
            >
              {UNITS.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.en} – {u.ta}
                </option>
              ))}
            </select>
          </div>
        </Field>

        <Field label="Watering method" ta="பாசன முறை">
          {flooded ? (
            <p className="rounded-xl bg-soil-100 px-3 py-2.5 text-soil-700">Flooding (paddy is kept ponded)</p>
          ) : (
            <select className={inputCls} value={irrigation} onChange={(e) => setIrrigation(e.target.value as Farm['irrigation'])}>
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

        <Field label="Where is the farm?" ta="வயல் எங்கே?">
          <LocationPicker value={location} onChange={setLocation} />
        </Field>

        <div className="sm:col-span-2">
          <Field label="Soil sensor data" ta="சென்சார் தரவு">
            <div className="grid gap-2 sm:grid-cols-3">
              {(
                [
                  ['upload', initial?.has_telemetry ? 'Replace with a new CSV' : 'Upload my sensor CSV'],
                  ['sample', 'Use sample data to try the app'],
                  ['later', initial?.has_telemetry ? 'Keep the current data' : 'Add it later'],
                ] as const
              ).map(([id, label]) => (
                <label key={id} className={`flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2.5 ${
                  sensor === id ? 'border-leaf-700 bg-leaf-50 font-semibold text-leaf-800' : 'border-soil-300 bg-white'}`}>
                  <input type="radio" name="sensor" checked={sensor === id} onChange={() => setSensor(id)} />
                  {label}
                </label>
              ))}
            </div>
            {sensor === 'upload' && (
              <input className={`${inputCls} mt-2 file:mr-3 file:rounded-lg file:border-0 file:bg-soil-100 file:px-3 file:py-1.5 file:font-semibold`}
                type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            )}
          </Field>
        </div>
      </div>

      {error && <ErrorNote message={error} />}
      <div className="flex flex-wrap gap-2">
        <button type="submit" disabled={busy}
          className="rounded-xl bg-leaf-700 px-6 py-3 text-lg font-bold text-white hover:bg-leaf-800 disabled:opacity-60">
          {busy ? 'Saving…' : 'Save farm · சேமி'}
        </button>
        <button type="button" onClick={() => onDone()}
          className="rounded-xl border border-soil-300 bg-white px-6 py-3 font-semibold text-soil-700 hover:bg-soil-100">
          Cancel
        </button>
      </div>
    </form>
  );
}

function FarmCard({ farm, crops, selected, onEdit }: { farm: Farm; crops: Crops | null; selected: boolean; onEdit: () => void }) {
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const run = async (label: string, action: () => Promise<unknown>) => {
    setBusy(label);
    setError('');
    try {
      await action();
      await loadFarms();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy('');
    }
  };

  const remove = () => {
    if (window.confirm(`Delete "${farm.name}" and its sensor data? This cannot be undone.`)) {
      run('Deleting…', () => api.deleteFarm(farm.id));
    }
  };

  return (
    <li className={`card space-y-3 p-4 ${selected ? 'ring-2 ring-leaf-700' : ''}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-lg font-bold text-soil-900">{farm.name}</h3>
          <p className="text-soil-700">
            {cropName(crops, farm.crop)} <span className="tamil">{cropTamil(crops, farm.crop)}</span> · {farmSize(farm)} ·{' '}
            {farm.irrigation}
          </p>
          <p className="text-sm text-soil-700">
            {farm.stage
              ? STAGE_LABEL[farm.stage] ?? farm.stage
              : farm.days_since_planting != null
                ? `Planted ${farm.days_since_planting} days ago`
                : 'Planting date not set'}
          </p>
          <p className="mt-1 flex items-center gap-1 text-sm text-soil-700">
            <MapPin className="h-4 w-4 shrink-0" aria-hidden /> {farm.location.name}
          </p>
        </div>
        {selected ? (
          <span className="flex shrink-0 items-center gap-1 rounded-full bg-leaf-700 px-3 py-1 text-sm font-bold text-white">
            <CheckCircle2 className="h-4 w-4" aria-hidden /> Selected
          </span>
        ) : (
          <button type="button" onClick={() => selectFarm(farm.id)}
            className="shrink-0 rounded-full border border-leaf-700 px-3 py-1 text-sm font-bold text-leaf-800 hover:bg-leaf-50">
            Select
          </button>
        )}
      </div>
      <p className={`text-sm font-semibold ${farm.has_telemetry ? 'text-leaf-800' : 'text-warn-700'}`}>
        {farm.has_telemetry ? '✓ Sensor data added' : '⚠ No sensor data yet: upload a CSV or use sample data'}
      </p>
      <div className="flex flex-wrap gap-2 text-sm">
        <label className="flex cursor-pointer items-center gap-1.5 rounded-full border border-soil-300 bg-white px-3 py-1.5 font-semibold text-soil-700 hover:bg-soil-100">
          <Upload className="h-4 w-4" aria-hidden /> {farm.has_telemetry ? 'Replace sensor data' : 'Upload sensor data'}
          <input type="file" accept=".csv,text/csv" className="sr-only"
            onChange={(e) => e.target.files?.[0] && run('Uploading…', () => api.uploadFarmTelemetry(farm.id, e.target.files![0]))} />
        </label>
        {!farm.has_telemetry && (
          <button type="button" onClick={() => run('Adding sample data…', () => api.useSampleData(farm.id))}
            className="rounded-full border border-soil-300 bg-white px-3 py-1.5 font-semibold text-soil-700 hover:bg-soil-100">
            Use sample data
          </button>
        )}
        <button type="button" onClick={onEdit}
          className="flex items-center gap-1.5 rounded-full border border-soil-300 bg-white px-3 py-1.5 font-semibold text-soil-700 hover:bg-soil-100">
          <Pencil className="h-4 w-4" aria-hidden /> Edit
        </button>
        <button type="button" onClick={remove}
          className="flex items-center gap-1.5 rounded-full border border-alert-700/30 bg-white px-3 py-1.5 font-semibold text-alert-700 hover:bg-alert-100">
          <Trash2 className="h-4 w-4" aria-hidden /> Delete
        </button>
      </div>
      {busy && <Spinner label={busy} />}
      {error && <ErrorNote message={error} />}
    </li>
  );
}

export default function Farms() {
  const { farms, selectedId, loaded, error } = useFarms();
  const crops = useCrops();
  const [editing, setEditing] = useState<Farm | 'new' | null>(null);
  const showForm = editing !== null || (loaded && farms.length === 0);

  const done = async (saved?: Farm) => {
    setEditing(null);
    if (saved) await loadFarms(saved.id);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-soil-900">
            My Farms <span className="tamil text-xl text-leaf-700">· என் வயல்கள்</span>
          </h1>
          <p className="text-soil-700">Add each of your fields. The selected farm is used on every page.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={downloadTemplate}
            className="flex items-center gap-1.5 rounded-xl border border-soil-300 bg-white px-4 py-2.5 font-semibold text-soil-700 hover:bg-soil-100">
            <Download className="h-4 w-4" aria-hidden /> Sensor CSV template
          </button>
          {farms.length > 0 && !editing && (
            <button type="button" onClick={() => setEditing('new')}
              className="flex items-center gap-1.5 rounded-xl bg-leaf-700 px-4 py-2.5 font-bold text-white hover:bg-leaf-800">
              <Plus className="h-5 w-5" aria-hidden /> Add farm
            </button>
          )}
        </div>
      </div>

      {showForm && (
        <FarmForm key={editing === 'new' || editing === null ? 'new' : editing.id}
          initial={editing && editing !== 'new' ? editing : null} crops={crops} onDone={done} />
      )}
      {error && <ErrorNote message={error} />}
      {!loaded && <Spinner label="Loading your farms…" />}

      <ul className="grid gap-4 md:grid-cols-2">
        {farms.map((f) => (
          <FarmCard key={f.id} farm={f} crops={crops} selected={f.id === selectedId} onEdit={() => setEditing(f)} />
        ))}
      </ul>
    </div>
  );
}
