// The supported crops (names in English and Tamil, stages, water rule) fetched once from /api/crops.
import { useEffect, useState } from 'react';
import { api, type Crops } from './api';

let cache: Crops | null = null;
let pending: Promise<Crops> | null = null;

export function useCrops(): Crops | null {
  const [crops, setCrops] = useState<Crops | null>(cache);
  useEffect(() => {
    if (cache) return;
    pending ??= api.crops();
    pending
      .then((c) => {
        cache = c;
        setCrops(c);
      })
      .catch(() => {
        pending = null;
      });
  }, []);
  return crops;
}

export const cropName = (crops: Crops | null, key: string) => crops?.[key]?.en ?? key;
export const cropTamil = (crops: Crops | null, key: string) => crops?.[key]?.ta ?? '';
