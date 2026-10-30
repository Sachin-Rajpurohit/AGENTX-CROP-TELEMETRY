import { useEffect, useState } from 'react';
import { CloudRain, Droplets, FlaskConical, MapPin, Sun, Thermometer } from 'lucide-react';
import { api, type Forecast } from '../api';
import { ErrorNote, Spinner, fmt } from '../components/ui';

const PLACES = [
  { name: 'Tiruchirappalli', ta: 'திருச்சிராப்பள்ளி', lat: 10.79, lon: 78.7 },
  { name: 'Thanjavur', ta: 'தஞ்சாவூர்', lat: 10.79, lon: 79.14 },
  { name: 'Madurai', ta: 'மதுரை', lat: 9.93, lon: 78.12 },
  { name: 'Coimbatore', ta: 'கோயம்புத்தூர்', lat: 11.02, lon: 76.96 },
  { name: 'Salem', ta: 'சேலம்', lat: 11.66, lon: 78.15 },
  { name: 'Chennai', ta: 'சென்னை', lat: 13.08, lon: 80.27 },
];

const SOURCE_NOTE: Record<Forecast['source'], string> = {
  live: 'Live forecast from Open-Meteo',
  cache: 'Open-Meteo forecast (saved in the last hour)',
  fallback: 'Live forecast unavailable – showing a cautious dry estimate',
};

function dayName(iso: string, i: number) {
  if (i === 0) return 'Today';
  if (i === 1) return 'Tomorrow';
  return new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });
}

function Effect({ on, icon, yes, no, ta }: { on: boolean; icon: React.ReactNode; yes: string; no: string; ta: string }) {
  return (
    <li
      className={`flex items-start gap-3 rounded-xl border p-3 ${
        on ? 'border-warn-700/30 bg-warn-100' : 'border-leaf-200 bg-leaf-50'
      }`}
    >
      <span className={on ? 'text-warn-700' : 'text-leaf-700'}>{icon}</span>
      <span>
        <span className="block font-semibold text-soil-900">{on ? yes : no}</span>
        {on && <span className="tamil block text-sm text-soil-800">{ta}</span>}
      </span>
    </li>
  );
}

export default function Weather() {
  const [place, setPlace] = useState(PLACES[0]);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    setForecast(null);
    setError('');
    api.weather(place.lat, place.lon).then(setForecast).catch((e) => setError(e.message));
  }, [place]);

  const radar =
    `https://embed.windy.com/embed2.html?lat=${place.lat}&lon=${place.lon}&detailLat=${place.lat}` +
    `&detailLon=${place.lon}&zoom=7&level=surface&overlay=rain&product=ecmwf&menu=&message=true&marker=true` +
    `&calendar=now&type=map&location=coordinates&metricWind=km%2Fh&metricTemp=%C2%B0C`;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-soil-900">
            Weather & Rain Radar <span className="tamil text-xl text-leaf-700">· வானிலை</span>
          </h1>
          <p className="text-soil-700">Rain and heat for the next 5 days, and what it means for your field.</p>
        </div>
        <label className="flex items-center gap-2">
          <MapPin className="h-5 w-5 text-leaf-700" aria-hidden />
          <span className="sr-only">Location</span>
          <select
            className="rounded-xl border border-soil-300 bg-white px-3 py-2.5 text-lg font-semibold"
            value={place.name}
            onChange={(e) => setPlace(PLACES.find((p) => p.name === e.target.value)!)}
          >
            {PLACES.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name} – {p.ta}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <ErrorNote message={error} />}
      {!forecast && !error && <Spinner label="Fetching the forecast…" />}

      {forecast && (
        <>
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {forecast.days.map((d, i) => {
              const rainy = d.rain_prob >= forecast.effects.thresholds.rain_skip_prob_pct;
              return (
                <li key={d.date} className={`card p-4 ${i < 2 ? 'ring-2 ring-leaf-200' : ''}`}>
                  <p className="font-bold text-soil-800">{dayName(d.date, i)}</p>
                  {rainy ? (
                    <CloudRain className="my-2 h-10 w-10 text-leaf-700" aria-label="Rain likely" />
                  ) : (
                    <Sun className="my-2 h-10 w-10 text-soil-500" aria-label="Mostly dry" />
                  )}
                  <p className="flex items-center gap-1.5 text-lg font-bold text-soil-900">
                    <Droplets className="h-4 w-4 text-leaf-700" aria-hidden /> {fmt(d.rain_mm, 1)} mm
                  </p>
                  <p className="text-sm text-soil-700">{fmt(d.rain_prob)}% chance of rain</p>
                  <p className="mt-1 flex items-center gap-1.5 text-soil-800">
                    <Thermometer className="h-4 w-4 text-alert-700" aria-hidden /> {fmt(d.tmax, 1)}°C
                  </p>
                </li>
              );
            })}
          </ul>
          <p className="text-sm text-soil-700">{SOURCE_NOTE[forecast.source]} · next 48 h are highlighted.</p>

          <section className="card p-4">
            <h2 className="mb-3 text-lg font-bold text-soil-900">
              What this means for your field <span className="tamil text-base text-leaf-700">· உங்கள் வயலுக்கு</span>
            </h2>
            <ul className="grid gap-3 md:grid-cols-3">
              <Effect
                on={forecast.effects.skip_irrigation}
                icon={<CloudRain className="h-6 w-6" />}
                yes={`Rain is coming (${fmt(forecast.risk.rain_mm_48h, 1)} mm): skip watering`}
                no={`No useful rain in 48 h (${fmt(forecast.risk.rain_mm_48h, 1)} mm): water as advised`}
                ta="மழை வருகிறது: நீர் பாய்ச்ச வேண்டாம்"
              />
              <Effect
                on={forecast.effects.delay_fertilizer}
                icon={<FlaskConical className="h-6 w-6" />}
                yes="Heavy rain: hold fertilizer so it does not wash away"
                no="Safe to apply fertilizer (no heavy rain)"
                ta="கனமழை: உரமிடுவதைத் தள்ளிப்போடவும்"
              />
              <Effect
                on={forecast.effects.irrigate_at_dawn}
                icon={<Sun className="h-6 w-6" />}
                yes={`Hot days (${fmt(forecast.risk.tmax_next3, 1)}°C): water before 7 am`}
                no={`No heat stress (max ${fmt(forecast.risk.tmax_next3, 1)}°C)`}
                ta="வெப்பம்: காலை 7 மணிக்கு முன் நீர் பாய்ச்சவும்"
              />
            </ul>
          </section>
        </>
      )}

      <section className="card overflow-hidden">
        <h2 className="px-4 pt-4 text-lg font-bold text-soil-900">
          Live rain radar <span className="tamil text-base text-leaf-700">· மழை ரேடார்</span>
        </h2>
        <p className="px-4 pb-3 text-sm text-soil-700">Map by Windy.com. Needs internet.</p>
        <iframe
          title={`Rain radar around ${place.name}`}
          src={radar}
          className="h-[420px] w-full border-0 sm:h-[480px]"
          loading="lazy"
        />
      </section>
    </div>
  );
}
