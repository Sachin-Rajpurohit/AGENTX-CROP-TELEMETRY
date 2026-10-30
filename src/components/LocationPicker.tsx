import { useEffect, useState } from 'react';
import { Crosshair, Loader2, MapPin, Search } from 'lucide-react';
import { api, type Place } from '../api';

/** Pick any place: search a village or town by name (Open-Meteo geocoding), or use this device's GPS. */
export default function LocationPicker({ value, onChange }: { value: Place | null; onChange: (p: Place) => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Place[]>([]);
  const [searching, setSearching] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setResults([]);
      setMessage('');
      return;
    }
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const found = await api.geocode(q);
        setResults(found);
        setMessage(found.length ? '' : 'No place found. Try the nearest town, or use your location.');
      } catch (e) {
        setMessage((e as Error).message);
      } finally {
        setSearching(false);
      }
    }, 350);
    return () => clearTimeout(timer);
  }, [query]);

  const choose = (p: Place) => {
    onChange(p);
    setQuery('');
    setResults([]);
  };

  const useGps = () => {
    if (!navigator.geolocation) return setMessage('This device cannot share its location.');
    setMessage('Finding your location…');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = +pos.coords.latitude.toFixed(4);
        const lon = +pos.coords.longitude.toFixed(4);
        choose({ name: `My location (${lat}, ${lon})`, lat, lon });
        setMessage('');
      },
      () => setMessage('Location permission denied. Search by name instead.'),
      { timeout: 10000 },
    );
  };


  const field =
    'w-full rounded-xl border border-soil-300 bg-white px-3 py-2.5 text-lg focus:border-leaf-700 focus:outline-none focus:ring-2 focus:ring-leaf-200';

  return (
    <div className="space-y-2">
      {value && (
        <p className="flex items-center gap-2 rounded-xl bg-leaf-50 px-3 py-2 font-semibold text-leaf-800">
          <MapPin className="h-4 w-4 shrink-0" aria-hidden /> {value.name}
          <span className="ml-auto text-xs font-normal text-soil-700">
            {value.lat.toFixed(2)}, {value.lon.toFixed(2)}
          </span>
        </p>
      )}
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-soil-500" aria-hidden />
        <input
          className={`${field} pl-10`}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search village, town or city…"
          aria-label="Search for a place"
        />
        {searching && <Loader2 className="absolute right-3 top-1/2 h-5 w-5 -translate-y-1/2 animate-spin text-leaf-700" />}
        {results.length > 0 && (
          <ul className="absolute z-30 mt-1 max-h-72 w-full overflow-auto rounded-xl border border-soil-200 bg-white shadow-lg">
            {results.map((r) => (
              <li key={`${r.lat},${r.lon}`}>
                <button
                  type="button"
                  onClick={() => choose(r)}
                  className="w-full px-3 py-2.5 text-left hover:bg-leaf-50"
                >
                  {r.name}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="flex flex-wrap gap-2 text-sm">
        <button
          type="button"
          onClick={useGps}
          className="flex items-center gap-1.5 rounded-full border border-soil-300 bg-white px-3 py-1.5 font-semibold text-soil-700 hover:bg-soil-100"
        >
          <Crosshair className="h-4 w-4" aria-hidden /> Use my location
        </button>
      </div>
      {message && <p className="text-sm text-soil-700">{message}</p>}
    </div>
  );
}
