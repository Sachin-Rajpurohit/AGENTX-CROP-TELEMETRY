// Typed client for the FastAPI backend (server.py). Every number shown in the UI comes from here.

export type Urgency = 'RED' | 'YELLOW' | 'GREEN';

export interface Confidence {
  score: number;
  level: 'HIGH' | 'MEDIUM' | 'LOW';
  reasons: string[];
}

export interface IrrigationPlan {
  irrigate: boolean;
  deficit_mm: number;
  daily_mm: number;
  events_per_day: number;
  litres_per_event: number;
  litres_per_day: number;
  days_to_refill: number;
  clipped: boolean;
}

export interface FertilizerPlan {
  deficit_kg_ha: Record<'N' | 'P' | 'K', number>;
  kg_ha: { urea_gross: number; urea_net: number; dap: number; mop: number };
  kg_area: { urea_gross: number; urea_net: number; dap: number; mop: number };
  area_acres: number;
}

export interface CropMatch {
  crop: string;
  in_range: number;
  of: number;
  outside_typical_range: Record<string, { value: number; typical: [number, number] }>;
  distance_sd: number;
}

export interface CropFit {
  available: boolean;
  reason?: string;
  features_used?: string[];
  best_matches?: CropMatch[];
  selected_crop?: CropMatch | null;
  selected_crop_in_dataset?: boolean;
}

export interface WeatherRisk {
  rain_mm_48h: number;
  rain_prob_48h: number;
  tmax_next3: number;
  source: 'live' | 'cache' | 'fallback';
}

export interface Place {
  name: string;
  lat: number;
  lon: number;
}

export interface Farm {
  id: string;
  name: string;
  crop: string;
  stage: string | null;
  planted_on: string | null;
  area_acres: number;
  area_unit: 'acre' | 'cent' | 'hectare';
  irrigation: 'drip' | 'flood';
  soil: string;
  location: Place;
  has_telemetry: boolean;
  days_since_planting: number | null;
  created_at: string;
}

export type FarmInput = Omit<Farm, 'id' | 'has_telemetry' | 'created_at' | 'days_since_planting'>;

export interface Advice {
  input_source: 'upload' | 'manual' | 'sample' | 'farm';
  decision: string;
  urgency: Urgency;
  crop: string;
  stage: string;
  confidence: Confidence;
  rules_fired: string[];
  reasons: string[];
  advisory: { en: string; ta: string };
  answer: string;
  readings: { moisture: number; N: number | null; P: number | null; K: number | null };
  moisture_thresholds: { crop: string; soil: string; fc: number; pwp: number; trigger: number };
  doses: { fertilizer: FertilizerPlan | null; irrigation: IrrigationPlan; method: string } | null;
  weather: WeatherRisk;
  quality: { score: number; issues: { code: string; severity: string; detail: string }[] };
  crop_fit: CropFit;
  assumptions: string[];
}

export interface TraceStep {
  thought: string;
  tool: string;
  args: Record<string, unknown>;
  observation: string;
}

export interface ChatReply {
  answer: string;
  parsed: { urgency: Urgency | null; advice_en: string | null; advice_ta: string | null; disclaimer: string | null };
  trace: TraceStep[];
}

export interface Forecast {
  source: WeatherRisk['source'];
  risk: WeatherRisk;
  days: { date: string; rain_mm: number; rain_prob: number; tmax: number }[];
  effects: {
    skip_irrigation: boolean;
    delay_fertilizer: boolean;
    irrigate_at_dawn: boolean;
    thresholds: {
      rain_skip_threshold_mm: number;
      rain_skip_prob_pct: number;
      rain_delay_threshold_mm: number;
      heat_threshold_c: number;
    };
  };
}

export type TelemetryRow = Record<string, string | number | null>;

export interface Sample {
  rows: TelemetryRow[];
  metadata: { crop: string; soil: string; soil_types: string[]; lat: number; lon: number };
}

export type Crops = Record<
  string,
  { en: string; ta: string; stages: string[]; flooded: boolean; fao56_p: number | null; targets_source: 'tnau' | 'dataset' }
>;

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    throw new Error('Cannot reach the advisory server. Start it with: python server.py');
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((d: { loc?: string[]; msg?: string }) => `${d.loc?.slice(-1)[0] ?? 'field'}: ${d.msg}`).join('; ')
        : `Request failed (${res.status})`;
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  sample: () => request<Sample>('/api/sample'),
  crops: () => request<Crops>('/api/crops'),
  weather: (lat: number, lon: number) => request<Forecast>(`/api/weather?lat=${lat}&lon=${lon}`),
  advice: (form: FormData) => request<Advice>('/api/advice', { method: 'POST', body: form }),
  chat: (message: string, farmId?: string | null) =>
    request<ChatReply>('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, farm_id: farmId || null }),
    }),
  geocode: (q: string) => request<Place[]>(`/api/geocode?q=${encodeURIComponent(q)}`),
  farms: () => request<Farm[]>('/api/farms'),
  createFarm: (farm: FarmInput) => request<Farm>('/api/farms', jsonBody('POST', farm)),
  updateFarm: (id: string, farm: FarmInput) => request<Farm>(`/api/farms/${id}`, jsonBody('PUT', farm)),
  deleteFarm: async (id: string) => {
    const res = await fetch(`/api/farms/${id}`, { method: 'DELETE' });
    if (!res.ok && res.status !== 404) throw new Error(`Could not delete the farm (${res.status})`);
  },
  farmTelemetry: (id: string) => request<{ rows: TelemetryRow[] }>(`/api/farms/${id}/telemetry`),
  uploadFarmTelemetry: (id: string, file: File) => {
    const form = new FormData();
    form.set('csv', file);
    return request<{ rows: number; farm: Farm }>(`/api/farms/${id}/telemetry`, { method: 'POST', body: form });
  },
  useSampleData: (id: string) =>
    request<{ rows: number; farm: Farm }>(`/api/farms/${id}/sample-data`, { method: 'POST' }),
  farmAdvice: (id: string) => request<Advice & { farm: Farm }>(`/api/farms/${id}/advice`, { method: 'POST' }),
};

function jsonBody(method: string, body: unknown): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}

/** Speak text through the backend's gTTS endpoint. Resolves when playback starts. */
export async function speak(text: string, lang: 'en' | 'ta'): Promise<HTMLAudioElement> {
  const res = await fetch(`/api/voice?lang=${lang}&text=${encodeURIComponent(text.slice(0, 1000))}`);
  if (!res.ok) throw new Error('Voice is unavailable right now (needs internet).');
  const audio = new Audio(URL.createObjectURL(await res.blob()));
  await audio.play();
  return audio;
}
