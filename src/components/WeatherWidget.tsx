import React, { useEffect, useState } from 'react';
import { WeatherForecastResult } from '../types';
import { CropTools } from '../lib/cropTools';
import { CloudRain, CloudSun, AlertTriangle, RefreshCw, MapPin } from 'lucide-react';

interface WeatherWidgetProps {
  cropTools: CropTools;
  lat?: number;
  lon?: number;
  locationName?: string;
}

export const WeatherWidget: React.FC<WeatherWidgetProps> = ({
  cropTools,
  lat = 10.79,
  lon = 78.70,
  locationName = 'Tiruchirappalli (10.79° N, 78.70° E)'
}) => {
  const [forecast, setForecast] = useState<WeatherForecastResult | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchWeather = async () => {
    setLoading(true);
    try {
      const raw = await cropTools.getWeatherForecast(lat, lon);
      const parsed = JSON.parse(raw);
      setForecast(parsed);
    } catch {
      setForecast(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWeather();
  }, [lat, lon]);

  const max48hProb = forecast?.rain_probability_pct
    ? Math.max(forecast.rain_probability_pct[0] || 0, forecast.rain_probability_pct[1] || 0)
    : 0;

  const isRainImminent = max48hProb >= 60;

  return (
    <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-5 shadow-xl space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <CloudRain className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
              Open-Meteo Weather Radar
            </h3>
            <p className="text-xs text-slate-400 flex items-center gap-1 truncate max-w-[200px]" title={locationName}>
              <MapPin className="w-3 h-3 text-emerald-400 shrink-0" />
              <span>{locationName}</span>
            </p>
          </div>
        </div>

        <button
          onClick={fetchWeather}
          disabled={loading}
          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-400 hover:text-white transition cursor-pointer"
          title="Refresh live weather forecast"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
        </button>
      </div>

      {isRainImminent && (
        <div className="bg-amber-500/15 border border-amber-500/40 rounded-xl p-3 flex items-start gap-2.5 text-xs text-amber-200">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Weather Alert:</span> High rain probability ({max48hProb}%) within 48h. AgriAgent rule automatically advises withholding irrigation and chemical fertilizer to prevent wash-off.
          </div>
        </div>
      )}

      {forecast?.error ? (
        <div className="text-xs text-slate-400 p-3 bg-slate-950/60 rounded-xl border border-slate-800">
          {forecast.error}
        </div>
      ) : forecast ? (
        <div className="grid grid-cols-3 gap-2 text-center">
          {forecast.days_ahead.map((day, idx) => {
            const prob = forecast.rain_probability_pct[idx] ?? 0;
            const mm = forecast.rain_mm[idx] ?? 0;
            const isHigh = prob >= 60;
            return (
              <div
                key={day}
                className={`p-3 rounded-xl border transition ${
                  isHigh
                    ? 'bg-cyan-950/40 border-cyan-700/60'
                    : 'bg-slate-950/50 border-slate-800/80'
                }`}
              >
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Day +{day}
                </div>
                <div className="my-2 flex justify-center">
                  {prob >= 40 ? (
                    <CloudRain className="w-6 h-6 text-cyan-400" />
                  ) : (
                    <CloudSun className="w-6 h-6 text-amber-400" />
                  )}
                </div>
                <div className={`text-base font-extrabold ${isHigh ? 'text-cyan-300' : 'text-slate-200'}`}>
                  {prob}%
                </div>
                <div className="text-[11px] font-mono text-slate-400">
                  {mm} mm rain
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-xs text-slate-500 text-center py-4">
          Loading 3-day meteorological forecast...
        </div>
      )}
    </div>
  );
};
