import { useEffect, useState, type FormEvent } from 'react';
import { CheckCircle2, Download, MapPin, Pencil, Plus, Trash2, Upload } from 'lucide-react';
import { api, type Crops, type Farm, type FarmInput, type Place } from '../api';
import LocationPicker from '../components/LocationPicker';
import { CROP_LABEL, ErrorNote, SOIL_LABEL, STAGE_LABEL, Spinner, fmt } from '../components/ui';
import { loadFarms, selectFarm, useFarms } from '../farmStore';

const inputCls =
  'w-full rounded-xl border border-soil-300 bg-white px-3 py-2.5 text-lg focus:border-leaf-700 focus:outline-none focus:ring-2 focus:ring-leaf-200';

const EMPTY: FarmInput = {
  name: '',
  crop: 'tomato',
  stage: null,
  area_acres: 1,
  irrigation: 'drip',
  soil: 'clay_loam',
  location: null as unknown as Place,
};

async function downloadTemplate() {
  const sample = await fetch('/api/sample').then((r) => r.json());
  const url = URL.createObjectURL(new Blob([sample.csv], { type: 'text/csv' }));
  const a = Object.assign(document.createElement('a'), { href: url, download: 'sensor_template.csv' });
  a.click();
  URL.revokeObjectURL(url);
}

function FarmForm({
  initial,
  crops,
  onDone,
}: {
  initial: Farm | null;
  crops: Crops | null;
  onDone: (farm?: Farm) => void;
}) {
  const [farm, setFarm] = useState<FarmInput>(initial ? { ...initial } : EMPTY);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const stages = crops?.[farm.crop]?.stages ?? [];
  const flooded = crops?.[farm.crop]?.flooded ?? false;
  const set = (patch: Partial<FarmInput>) => setFarm({ ...farm, ...patch });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!farm.location) return setError('Choose where the farm is.');
    setBusy(true);
    setError('');
    try {
      const body = { ...farm, irrigation: flooded ? 'flood' : farm.irrigation } as FarmInput;
      let saved = initial ? await api.updateFarm(initial.id, body) : await api.createFarm(body);
      if (file) saved = (await api.uploadFarmTelemetry(saved.id, file)).farm;
      onDone(saved);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="card space-y-4 p-4">
      <h2 className="text-lg font-bold text-soil-900">{initial ? `Edit ${initial.name}` : 'Add a farm'}</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block sm:col-span-2">
          <span className="mb-1 block font-semibold text-soil-800">
            Farm name <span className="tamil text-sm font-medium text-soil-500">· வயல் பெயர்</span>
          </span>
          <input
            className={inputCls}
            value={farm.name}
            onChange={(e) => set({ name: e.target.value })}
            placeholder="e.g. North field near the well"
            maxLength={60}
            required
          />
        </label>
        <label className="block">
          <span className="mb-1 block font-semibold text-soil-800">Crop</span>
          <select className={inputCls} value={farm.crop} onChange={(e) => set({ crop: e.target.value, stage: null })}>
            {Object.keys(crops ?? CROP_LABEL).map((c) => (
              <option key={c} value={c}>
                {CROP_LABEL[c]?.en ?? c} – {CROP_LABEL[c]?.ta ?? ''}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block font-semibold text-soil-800">Growth stage</span>
          {stages.length ? (
            <select className={inputCls} value={farm.stage ?? ''} onChange={(e) => set({ stage: e.target.value || null })}>
              <option value="">Not sure</option>
              {stages.map((s) => (
                <option key={s} value={s}>
                  {STAGE_LABEL[s] ?? s}
                </option>
              ))}
            </select>
          ) : (
            <p className="rounded-xl bg-soil-100 px-3 py-2.5 text-soil-700">Whole-season target</p>
          )}
        </label>
        <label className="block">
          <span className="mb-1 block font-semibold text-soil-800">Size (acres)</span>
          <input
            className={inputCls}
            type="number"
            min="0.1"
            step="0.1"
            value={farm.area_acres}
            onChange={(e) => set({ area_acres: Number(e.target.value) })}
            required
          />
        </label>
        <label className="block">
          <span className="mb-1 block font-semibold text-soil-800">Watering</span>
          {flooded ? (
            <p className="rounded-xl bg-soil-100 px-3 py-2.5 text-soil-700">Flooding (paddy)</p>
          ) : (
            <select
              className={inputCls}
              value={farm.irrigation}
              onChange={(e) => set({ irrigation: e.target.value as FarmInput['irrigation'] })}
            >
              <option value="drip">Drip – சொட்டு நீர்</option>
              <option value="flood">Flood / furrow – வாய்க்கால்</option>
            </select>
          )}
        </label>
        <label className="block sm:col-span-2">
          <span className="mb-1 block font-semibold text-soil-800">Soil type</span>
          <select className={inputCls} value={farm.soil} onChange={(e) => set({ soil: e.target.value })}>
            {Object.entries(SOIL_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </label>
        <div className="sm:col-span-2">
          <span className="mb-1 block font-semibold text-soil-800">
            Location <span className="tamil text-sm font-medium text-soil-500">· இடம்</span>
          </span>
          <LocationPicker value={farm.location} onChange={(location) => set({ location })} />
        </div>
        <label className="block sm:col-span-2">
          <span className="mb-1 block font-semibold text-soil-800">
            Sensor data (CSV) {initial?.has_telemetry && <span className="text-sm font-normal">· leave empty to keep the current file</span>}
          </span>
          <input
            className={`${inputCls} file:mr-3 file:rounded-lg file:border-0 file:bg-soil-100 file:px-3 file:py-1.5 file:font-semibold`}
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>
      </div>
      {error && <ErrorNote message={error} />}
      <div className="flex flex-wrap gap-2">
        <button
          type="submit"
          disabled={busy}
          className="rounded-xl bg-leaf-700 px-6 py-3 text-lg font-bold text-white hover:bg-leaf-800 disabled:opacity-60"
        >
          {busy ? 'Saving…' : 'Save farm'}
        </button>
        <button
          type="button"
          onClick={() => onDone()}
          className="rounded-xl border border-soil-300 bg-white px-6 py-3 font-semibold text-soil-700 hover:bg-soil-100"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

function FarmCard({ farm, selected, onEdit }: { farm: Farm; selected: boolean; onEdit: () => void }) {
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const upload = async (file: File | undefined) => {
    if (!file) return;
    setBusy('Uploading…');
    setError('');
    try {
      await api.uploadFarmTelemetry(farm.id, file);
      await loadFarms();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy('');
    }
  };

  const remove = async () => {
    if (!window.confirm(`Delete "${farm.name}" and its sensor data? This cannot be undone.`)) return;
    setBusy('Deleting…');
    try {
      await api.deleteFarm(farm.id);
      await loadFarms();
    } catch (e) {
      setError((e as Error).message);
      setBusy('');
    }
  };

  return (
    <li className={`card space-y-3 p-4 ${selected ? 'ring-2 ring-leaf-700' : ''}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-lg font-bold text-soil-900">{farm.name}</h3>
          <p className="text-soil-700">
            {CROP_LABEL[farm.crop]?.en ?? farm.crop} <span className="tamil">{CROP_LABEL[farm.crop]?.ta}</span>
            {farm.stage && ` · ${STAGE_LABEL[farm.stage] ?? farm.stage}`} · {fmt(farm.area_acres, 1)} acre(s) ·{' '}
            {farm.irrigation}
          </p>
          <p className="mt-1 flex items-center gap-1 text-sm text-soil-700">
            <MapPin className="h-4 w-4 shrink-0" aria-hidden /> {farm.location.name}
          </p>
        </div>
        {selected ? (
          <span className="flex items-center gap-1 rounded-full bg-leaf-700 px-3 py-1 text-sm font-bold text-white">
            <CheckCircle2 className="h-4 w-4" aria-hidden /> Selected
          </span>
        ) : (
          <button
            type="button"
            onClick={() => selectFarm(farm.id)}
            className="rounded-full border border-leaf-700 px-3 py-1 text-sm font-bold text-leaf-800 hover:bg-leaf-50"
          >
            Select
          </button>
        )}
      </div>
      <p className={`text-sm font-semibold ${farm.has_telemetry ? 'text-leaf-800' : 'text-warn-700'}`}>
        {farm.has_telemetry ? '✓ Sensor data uploaded' : '⚠ No sensor data yet: upload a CSV to get advice'}
      </p>
      <div className="flex flex-wrap gap-2 text-sm">
        <label className="flex cursor-pointer items-center gap-1.5 rounded-full border border-soil-300 bg-white px-3 py-1.5 font-semibold text-soil-700 hover:bg-soil-100">
          <Upload className="h-4 w-4" aria-hidden /> {farm.has_telemetry ? 'Replace sensor data' : 'Upload sensor data'}
          <input type="file" accept=".csv,text/csv" className="sr-only" onChange={(e) => upload(e.target.files?.[0])} />
        </label>
        <button
          type="button"
          onClick={onEdit}
          className="flex items-center gap-1.5 rounded-full border border-soil-300 bg-white px-3 py-1.5 font-semibold text-soil-700 hover:bg-soil-100"
        >
          <Pencil className="h-4 w-4" aria-hidden /> Edit
        </button>
        <button
          type="button"
          onClick={remove}
          className="flex items-center gap-1.5 rounded-full border border-alert-700/30 bg-white px-3 py-1.5 font-semibold text-alert-700 hover:bg-alert-100"
        >
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
  const [crops, setCrops] = useState<Crops | null>(null);
  const [editing, setEditing] = useState<Farm | 'new' | null>(null);

  useEffect(() => {
    api.crops().then(setCrops).catch(() => undefined);
  }, []);

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
          <p className="text-soil-700">Add each field with its crop, size and place. The selected farm is used everywhere.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={downloadTemplate}
            className="flex items-center gap-1.5 rounded-xl border border-soil-300 bg-white px-4 py-2.5 font-semibold text-soil-700 hover:bg-soil-100"
          >
            <Download className="h-4 w-4" aria-hidden /> CSV template
          </button>
          <button
            type="button"
            onClick={() => setEditing('new')}
            className="flex items-center gap-1.5 rounded-xl bg-leaf-700 px-4 py-2.5 font-bold text-white hover:bg-leaf-800"
          >
            <Plus className="h-5 w-5" aria-hidden /> Add farm
          </button>
        </div>
      </div>

      {editing && <FarmForm initial={editing === 'new' ? null : editing} crops={crops} onDone={done} />}
      {error && <ErrorNote message={error} />}
      {!loaded && <Spinner label="Loading your farms…" />}

      <ul className="grid gap-4 md:grid-cols-2">
        {farms.map((f) => (
          <FarmCard key={f.id} farm={f} selected={f.id === selectedId} onEdit={() => setEditing(f)} />
        ))}
      </ul>
      {loaded && farms.length === 0 && (
        <p className="card p-6 text-center text-soil-700">No farms yet. Add your first field to get advice for it.</p>
      )}
    </div>
  );
}
