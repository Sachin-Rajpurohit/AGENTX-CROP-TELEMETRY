import { useState } from 'react';
import { AlertTriangle, CheckCircle2, ChevronDown, Clock, Loader2, Volume2 } from 'lucide-react';
import { speak, type TraceStep, type Urgency } from '../api';

export const CROP_LABEL: Record<string, { en: string; ta: string }> = {
  tomato: { en: 'Tomato', ta: 'தக்காளி' },
  rice: { en: 'Rice (paddy)', ta: 'நெல்' },
  maize: { en: 'Maize', ta: 'மக்காச்சோளம்' },
  cotton: { en: 'Cotton', ta: 'பருத்தி' },
};

export const STAGE_LABEL: Record<string, string> = {
  seedling: 'Seedling',
  vegetative: 'Vegetative growth',
  flowering: 'Flowering',
  fruiting: 'Fruiting',
  tillering: 'Tillering',
  ripening: 'Ripening',
  whole_season: 'Whole season',
};

export const SOIL_LABEL: Record<string, string> = {
  clay_loam: 'Clay loam (black / alluvial)',
  red_soil: 'Red soil',
  sandy_loam: 'Sandy loam',
};

export const DECISION_LABEL: Record<string, { en: string; ta: string }> = {
  IRRIGATE: { en: 'Water the field today', ta: 'இன்று நீர் பாய்ச்சவும்' },
  IRRIGATE_THEN_FERTILIZE: { en: 'Water first, then add fertilizer', ta: 'முதலில் நீர், பிறகு உரம்' },
  FERTILIZE: { en: 'Add fertilizer', ta: 'உரமிடவும்' },
  WAIT_FOR_RAIN: { en: 'Wait for the rain', ta: 'மழைக்காகக் காத்திருக்கவும்' },
  DELAY_FERTILIZER: { en: 'Hold the fertilizer', ta: 'உரமிடுவதைத் தள்ளிப்போடவும்' },
  DRAINAGE_WARNING: { en: 'Soil too wet: drain the field', ta: 'மண் அதிக ஈரம்: வடிகால் செய்யவும்' },
  INSPECT_SENSOR: { en: 'Check the soil sensor', ta: 'சென்சாரைச் சரிபார்க்கவும்' },
  NO_ACTION: { en: 'No action needed', ta: 'நடவடிக்கை தேவையில்லை' },
};

const URGENCY_STYLE: Record<Urgency, { box: string; chip: string; en: string; ta: string; Icon: typeof AlertTriangle }> = {
  RED: {
    box: 'bg-alert-100 border-alert-700/30 text-alert-700',
    chip: 'bg-alert-700 text-white',
    en: 'Act today',
    ta: 'இன்றே செய்யவும்',
    Icon: AlertTriangle,
  },
  YELLOW: {
    box: 'bg-warn-100 border-warn-700/30 text-warn-700',
    chip: 'bg-warn-700 text-white',
    en: 'Act in 2–3 days',
    ta: '2–3 நாட்களில் செய்யவும்',
    Icon: Clock,
  },
  GREEN: {
    box: 'bg-leaf-100 border-leaf-700/30 text-leaf-800',
    chip: 'bg-leaf-700 text-white',
    en: 'All good',
    ta: 'எல்லாம் சரி',
    Icon: CheckCircle2,
  },
};

export function UrgencyBanner({ urgency, decision }: { urgency: Urgency; decision?: string }) {
  const s = URGENCY_STYLE[urgency];
  const label = decision ? DECISION_LABEL[decision] : undefined;
  return (
    <div className={`flex items-center gap-4 rounded-2xl border p-4 sm:p-5 ${s.box}`}>
      <s.Icon className="h-10 w-10 shrink-0" aria-hidden />
      <div className="min-w-0">
        <span className={`inline-block rounded-full px-3 py-0.5 text-sm font-bold ${s.chip}`}>
          {s.en} · <span className="tamil">{s.ta}</span>
        </span>
        {label && (
          <p className="mt-1 text-xl font-bold leading-snug sm:text-2xl">
            {label.en}
            <span className="tamil block text-lg font-semibold">{label.ta}</span>
          </p>
        )}
      </div>
    </div>
  );
}

export function UrgencyChip({ urgency }: { urgency: Urgency }) {
  const s = URGENCY_STYLE[urgency];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-bold ${s.chip}`}>
      <s.Icon className="h-4 w-4" aria-hidden /> {s.en}
    </span>
  );
}

function SpeakButton({ text, lang }: { text: string; lang: 'en' | 'ta' }) {
  const [state, setState] = useState<'idle' | 'loading' | 'error'>('idle');
  const onClick = async () => {
    setState('loading');
    try {
      const audio = await speak(text, lang);
      audio.onended = () => setState('idle');
      setState('idle');
    } catch {
      setState('error');
    }
  };
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={state === 'loading'}
      className="inline-flex items-center gap-1.5 rounded-full border border-soil-300 bg-white px-3 py-1 text-sm font-semibold text-soil-700 hover:bg-soil-100 disabled:opacity-60"
      title={lang === 'ta' ? 'Listen in Tamil' : 'Listen in English'}
    >
      {state === 'loading' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Volume2 className="h-4 w-4" />}
      {state === 'error' ? 'Voice unavailable' : lang === 'ta' ? 'கேளுங்கள்' : 'Listen'}
    </button>
  );
}

/** English and Tamil advice side by side, each with a listen button. */
export function AdviceCard({ en, ta, disclaimer }: { en?: string | null; ta?: string | null; disclaimer?: string | null }) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {ta && (
        <section className="rounded-2xl border border-leaf-200 bg-leaf-50 p-4">
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3 className="tamil text-base font-bold text-leaf-800">ஆலோசனை (தமிழ்)</h3>
            <SpeakButton text={ta} lang="ta" />
          </div>
          <p className="tamil text-lg text-soil-900">{ta}</p>
        </section>
      )}
      {en && (
        <section className="rounded-2xl border border-soil-200 bg-white p-4">
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3 className="text-base font-bold text-soil-700">Advice (English)</h3>
            <SpeakButton text={en} lang="en" />
          </div>
          <p className="text-lg leading-relaxed text-soil-900">{en}</p>
        </section>
      )}
      {disclaimer && (
        <p className="text-sm text-soil-700 md:col-span-2">
          ⚠️ {disclaimer} <span className="tamil">இது மதிப்பீடு மட்டுமே.</span>
        </p>
      )}
    </div>
  );
}

/** The agent's Thought → Action → Observation steps, collapsed by default. */
export function TraceSteps({ steps }: { steps: TraceStep[] }) {
  const [open, setOpen] = useState(false);
  if (!steps.length) return null;
  return (
    <div className="rounded-xl border border-soil-200 bg-soil-50">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-2.5 text-left text-sm font-semibold text-soil-700"
        aria-expanded={open}
      >
        How I worked this out ({steps.length} steps)
        <ChevronDown className={`h-4 w-4 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <ol className="space-y-3 border-t border-soil-200 px-4 py-3">
          {steps.map((s, i) => (
            <li key={i} className="text-sm">
              <p className="font-semibold text-soil-900">
                {i + 1}. {s.thought || 'Next step'}
              </p>
              <p className="mt-0.5 font-mono text-xs text-leaf-800">
                {s.tool}({Object.entries(s.args).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(', ')})
              </p>
              <p className="mt-1 break-words font-mono text-xs text-soil-700">
                {s.observation.length > 260 ? `${s.observation.slice(0, 260)}…` : s.observation}
              </p>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export function Spinner({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 text-soil-700" role="status">
      <Loader2 className="h-5 w-5 animate-spin text-leaf-700" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-alert-700/30 bg-alert-100 px-4 py-3 text-alert-700" role="alert">
      {message}
    </div>
  );
}

export const fmt = (n: number, digits = 0) =>
  n.toLocaleString('en-IN', { maximumFractionDigits: digits, minimumFractionDigits: 0 });
