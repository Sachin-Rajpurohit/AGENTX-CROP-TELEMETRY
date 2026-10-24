import { CropRequirementEntry, SoilReading } from '../types';

export const CROP_REQUIREMENTS_DB: Record<string, CropRequirementEntry> = {
  tomato: {
    crop: 'tomato',
    source: 'TNAU Agritech Portal & ICAR-IIHR Bangalore',
    ideal: { N: 75, P: 40, K: 50, pH: 6.5, moisture: 65 },
    stages: {
      seedling: { moisture: 70, N: 40, P: 50, K: 30 },
      vegetative: { moisture: 65, N: 75, P: 40, K: 50 },
      flowering: { moisture: 65, N: 100, P: 50, K: 60 },
      fruiting: { moisture: 60, N: 120, P: 60, K: 75 }
    }
  },
  rice: {
    crop: 'rice',
    source: 'TNAU Agritech Portal & ICAR-NRRI Cuttack',
    ideal: { N: 100, P: 50, K: 50, pH: 6.5, moisture: 80 },
    stages: {
      seedling: { moisture: 85, N: 40, P: 40, K: 30 },
      tillering: { moisture: 80, N: 80, P: 40, K: 40 },
      flowering: { moisture: 80, N: 100, P: 50, K: 50 },
      ripening: { moisture: 60, N: 60, P: 30, K: 40 }
    }
  },
  maize: {
    crop: 'maize',
    source: 'TNAU Agritech Portal & ICAR-IIMR',
    ideal: { N: 120, P: 60, K: 50, pH: 6.8, moisture: 60 },
    stages: {
      seedling: { moisture: 65, N: 40, P: 40, K: 30 },
      vegetative: { moisture: 60, N: 90, P: 50, K: 40 },
      tasseling: { moisture: 65, N: 120, P: 60, K: 50 },
      grain_filling: { moisture: 55, N: 80, P: 40, K: 40 }
    }
  },
  cotton: {
    crop: 'cotton',
    source: 'TNAU Agritech Portal & ICAR-CICR Nagpur',
    ideal: { N: 80, P: 40, K: 40, pH: 7.2, moisture: 55 },
    stages: {
      seedling: { moisture: 60, N: 30, P: 30, K: 25 },
      vegetative: { moisture: 55, N: 60, P: 40, K: 35 },
      flowering: { moisture: 60, N: 80, P: 40, K: 40 },
      boll_development: { moisture: 50, N: 60, P: 30, K: 40 }
    }
  },
  banana: {
    crop: 'banana',
    source: 'TNAU Agritech & ICAR-NRCB Tiruchirappalli',
    ideal: { N: 200, P: 60, K: 250, pH: 6.5, moisture: 70 },
    stages: {
      vegetative: { moisture: 70, N: 150, P: 50, K: 180 },
      shooting: { moisture: 75, N: 200, P: 60, K: 250 },
      bunch_development: { moisture: 70, N: 180, P: 50, K: 220 }
    }
  },
  groundnut: {
    crop: 'groundnut',
    source: 'TNAU Agritech Portal',
    ideal: { N: 25, P: 50, K: 75, pH: 6.2, moisture: 55 },
    stages: {
      vegetative: { moisture: 55, N: 20, P: 40, K: 50 },
      flowering: { moisture: 60, N: 25, P: 50, K: 75 },
      peg_formation: { moisture: 65, N: 25, P: 50, K: 75 },
      pod_filling: { moisture: 50, N: 15, P: 30, K: 50 }
    }
  }
};

// Default 8-day telemetry series matching tests and real tomato sensor stream
export const DEFAULT_TELEMETRY_DATA: SoilReading[] = [
  { timestamp: '2026-10-12 08:00', moisture: 31, N: 40, P: 20, K: 30, pH: 6.4, temperature: 29.5, humidity: 76, rainfall: 0, crop: 'tomato' },
  { timestamp: '2026-10-13 08:00', moisture: 29, N: 40, P: 20, K: 30, pH: 6.4, temperature: 30.1, humidity: 74, rainfall: 0, crop: 'tomato' },
  { timestamp: '2026-10-14 08:00', moisture: 28, N: 40, P: 20, K: 30, pH: 6.3, temperature: 30.8, humidity: 72, rainfall: 0, crop: 'tomato' },
  { timestamp: '2026-10-15 08:00', moisture: 27, N: 40, P: 20, K: 30, pH: 6.3, temperature: 31.2, humidity: 71, rainfall: 0, crop: 'tomato' },
  { timestamp: '2026-10-16 08:00', moisture: 26, N: 40, P: 20, K: 30, pH: 6.3, temperature: 31.5, humidity: 70, rainfall: 0, crop: 'tomato' },
  { timestamp: '2026-10-17 08:00', moisture: 24, N: 40, P: 20, K: 30, pH: 6.2, temperature: 31.8, humidity: 68, rainfall: 0, crop: 'tomato' },
  { timestamp: '2026-10-18 08:00', moisture: 23, N: 40, P: 20, K: 30, pH: 6.2, temperature: 32.0, humidity: 66, rainfall: 0, crop: 'tomato' },
  { timestamp: '2026-10-19 08:00', moisture: 22, N: 40, P: 20, K: 30, pH: 6.2, temperature: 32.4, humidity: 65, rainfall: 0, crop: 'tomato' }
];

export interface TelemetryScenario {
  name: string;
  description: string;
  locationName: string;
  lat: number;
  lon: number;
  data: SoilReading[];
}

export const TELEMETRY_SCENARIOS: Record<string, TelemetryScenario> = {
  tomato_stress: {
    name: 'Tomato Moisture & N Deficit (Trichy Plot #4)',
    description: 'Moisture falling rapidly from 31% to 22% over 8 days. Nitrogen at 40 kg/ha vs 100 kg/ha required in flowering stage.',
    locationName: 'Tiruchirappalli (10.79° N, 78.70° E)',
    lat: 10.79,
    lon: 78.70,
    data: DEFAULT_TELEMETRY_DATA
  },
  tomato_optimal: {
    name: 'Tomato Optimal Moisture & Soil Health (Coimbatore)',
    description: 'Moisture stable at 64% with well-balanced nutrients (N: 95, P: 48, K: 58, pH: 6.5).',
    locationName: 'Coimbatore (11.01° N, 76.95° E)',
    lat: 11.01,
    lon: 76.95,
    data: [
      { timestamp: '2026-10-12 08:00', moisture: 63, N: 92, P: 46, K: 56, pH: 6.5, temperature: 28.5, humidity: 78, rainfall: 2, crop: 'tomato' },
      { timestamp: '2026-10-13 08:00', moisture: 65, N: 93, P: 46, K: 56, pH: 6.5, temperature: 28.0, humidity: 80, rainfall: 5, crop: 'tomato' },
      { timestamp: '2026-10-14 08:00', moisture: 64, N: 93, P: 47, K: 57, pH: 6.5, temperature: 28.4, humidity: 79, rainfall: 0, crop: 'tomato' },
      { timestamp: '2026-10-15 08:00', moisture: 64, N: 94, P: 47, K: 57, pH: 6.5, temperature: 28.7, humidity: 77, rainfall: 0, crop: 'tomato' },
      { timestamp: '2026-10-16 08:00', moisture: 63, N: 95, P: 48, K: 58, pH: 6.5, temperature: 29.0, humidity: 76, rainfall: 0, crop: 'tomato' },
      { timestamp: '2026-10-17 08:00', moisture: 64, N: 95, P: 48, K: 58, pH: 6.5, temperature: 28.9, humidity: 75, rainfall: 0, crop: 'tomato' },
      { timestamp: '2026-10-18 08:00', moisture: 64, N: 95, P: 48, K: 58, pH: 6.5, temperature: 29.1, humidity: 74, rainfall: 0, crop: 'tomato' },
      { timestamp: '2026-10-19 08:00', moisture: 64, N: 95, P: 48, K: 58, pH: 6.5, temperature: 29.2, humidity: 74, rainfall: 0, crop: 'tomato' }
    ]
  },
  rice_field: {
    name: 'Paddy Rice Delta Zone (Thanjavur)',
    description: 'Rice wetland soil data with submerged moisture 82%, high humidity 84%, and moderate N=75.',
    locationName: 'Thanjavur Delta (10.78° N, 79.13° E)',
    lat: 10.78,
    lon: 79.13,
    data: [
      { timestamp: '2026-10-12 08:00', moisture: 84, N: 70, P: 38, K: 42, pH: 6.8, temperature: 27.2, humidity: 86, rainfall: 12, crop: 'rice' },
      { timestamp: '2026-10-14 08:00', moisture: 83, N: 72, P: 39, K: 43, pH: 6.7, temperature: 27.5, humidity: 85, rainfall: 4, crop: 'rice' },
      { timestamp: '2026-10-16 08:00', moisture: 82, N: 74, P: 40, K: 44, pH: 6.7, temperature: 27.8, humidity: 84, rainfall: 0, crop: 'rice' },
      { timestamp: '2026-10-18 08:00', moisture: 81, N: 75, P: 40, K: 45, pH: 6.7, temperature: 28.0, humidity: 83, rainfall: 0, crop: 'rice' }
    ]
  },
  insufficient_readings: {
    name: 'Sparse Sensor Read (Madurai Plot)',
    description: 'Simulates edge-case test with fewer than 3 readings. The agent safely refuses calculation and reports missing data.',
    locationName: 'Madurai (9.92° N, 78.11° E)',
    lat: 9.92,
    lon: 78.11,
    data: [
      { timestamp: '2026-10-18 08:00', moisture: 25, N: 45, P: 22, K: 32, pH: 6.4, temperature: 31.0, humidity: 68, rainfall: 0, crop: 'tomato' },
      { timestamp: '2026-10-19 08:00', moisture: 24, N: 45, P: 22, K: 32, pH: 6.3, temperature: 31.5, humidity: 67, rainfall: 0, crop: 'tomato' }
    ]
  }
};
