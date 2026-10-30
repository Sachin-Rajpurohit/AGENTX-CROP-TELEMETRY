// Farm size: a number plus Acres / Cents / Hectares buttons. Changing the unit converts the number,
// so the land stays the same (2 acres -> 200 cents). The API always receives acres (toAcres).
export type Unit = 'acre' | 'cent' | 'hectare';

export const UNITS: { id: Unit; en: string; ta: string; perAcre: number }[] = [
  { id: 'acre', en: 'Acres', ta: 'ஏக்கர்', perAcre: 1 },
  { id: 'cent', en: 'Cents', ta: 'சென்ட்', perAcre: 100 },
  { id: 'hectare', en: 'Hectares', ta: 'ஹெக்டேர்', perAcre: 0.404686 },
];

const perAcre = (unit: Unit) => UNITS.find((u) => u.id === unit)!.perAcre;
export const toAcres = (value: number, unit: Unit) => value / perAcre(unit);
export const fromAcres = (acres: number, unit: Unit) => acres * perAcre(unit);

export default function AreaInput({
  value,
  unit,
  onChange,
  id,
}: {
  value: string;
  unit: Unit;
  onChange: (value: string, unit: Unit) => void;
  id?: string;
}) {
  const switchUnit = (next: Unit) => {
    const n = Number(value);
    onChange(n > 0 ? String(+fromAcres(toAcres(n, unit), next).toFixed(2)) : value, next);
  };

  return (
    <div className="space-y-2">
      <input
        id={id}
        className="w-full rounded-xl border border-soil-300 bg-white px-3 py-2.5 text-lg focus:border-leaf-700 focus:outline-none focus:ring-2 focus:ring-leaf-200"
        type="number"
        inputMode="decimal"
        min="0.01"
        step="any"
        value={value}
        onChange={(e) => onChange(e.target.value, unit)}
        placeholder="e.g. 2"
        required
      />
      <div className="grid grid-cols-3 gap-1.5" role="radiogroup" aria-label="Unit">
        {UNITS.map((u) => (
          <button
            key={u.id}
            type="button"
            role="radio"
            aria-checked={unit === u.id}
            onClick={() => switchUnit(u.id)}
            className={`rounded-lg border px-2 py-1.5 text-center leading-tight ${
              unit === u.id
                ? 'border-leaf-700 bg-leaf-700 font-bold text-white'
                : 'border-soil-300 bg-white font-semibold text-soil-700 hover:bg-soil-100'
            }`}
          >
            <span className="block text-sm">{u.en}</span>
            <span className="tamil block text-xs">{u.ta}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
