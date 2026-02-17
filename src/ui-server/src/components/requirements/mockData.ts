import type { RequirementData } from './types';

export const BUILD_TIME = new Date(Date.now() - 42000).toISOString();

export const MOCK_REQUIREMENTS: RequirementData[] = [
  {
    id: 'req-001',
    name: 'REQ-001: Output DC bias',
    net: 'output',
    capture: 'dcop',
    measurement: 'final_value',
    minVal: 7.3,
    typical: 7.5,
    maxVal: 7.7,
    actual: 7.498,
    passed: true,
    justification: 'Resistor divider primary function is to divide voltage.',
    contextNets: [],
    unit: 'V',
    timeSeries: null,
  },
  {
    id: 'req-002',
    name: 'REQ-002: Supply current',
    net: 'i(v1)',
    capture: 'dcop',
    measurement: 'final_value',
    minVal: -500e-6,
    typical: -250e-6,
    maxVal: 0,
    actual: -250e-6,
    passed: true,
    justification: 'Power budget for shared 10V rail (SPICE sign: negative = into circuit)',
    contextNets: [],
    unit: 'A',
    timeSeries: null,
  },
  {
    id: 'req-003',
    name: 'REQ-003: Transient final value',
    net: 'output',
    capture: 'transient',
    measurement: 'final_value',
    minVal: 7.45,
    typical: 7.5,
    maxVal: 7.55,
    actual: 7.5,
    passed: true,
    justification: 'Output converges to DC steady-state before ADC sampling window.',
    contextNets: ['power_hv'],
    unit: 'V',
    timeSeries: (() => {
      const N = 500;
      const time = Array.from({ length: N }, (_, i) => i * 1.0 / (N - 1));
      const output = time.map(t => {
        const tau = 0.08;
        return 7.5 * (1 - Math.exp(-t / tau)) + (Math.random() - 0.5) * 0.01;
      });
      const power_hv = time.map(t => t < 0.001 ? 0 : 10.0 + (Math.random() - 0.5) * 0.02);
      return { time, signals: { 'v(output)': output, 'v(power_hv)': power_hv } };
    })(),
  },
  {
    id: 'req-004',
    name: 'REQ-004: Settling time',
    net: 'output',
    capture: 'transient',
    measurement: 'settling_time',
    minVal: 0.2,
    typical: 0.3,
    maxVal: 0.4,
    actual: 0.336,
    passed: true,
    justification: 'Must settle within 400ms before first ADC sample.',
    contextNets: ['power_hv'],
    unit: 's',
    settlingTolerance: 0.01,
    timeSeries: (() => {
      const N = 500;
      const time = Array.from({ length: N }, (_, i) => i * 0.5 / (N - 1));
      const output = time.map(t => {
        const tau = 0.08;
        return 7.5 * (1 - Math.exp(-t / tau)) + (Math.random() - 0.5) * 0.008;
      });
      const power_hv = time.map(t => t < 0.001 ? 0 : 10.0 + (Math.random() - 0.5) * 0.02);
      return { time, signals: { 'v(output)': output, 'v(power_hv)': power_hv } };
    })(),
  },
  {
    id: 'req-005',
    name: 'REQ-005: Output ripple',
    net: 'output',
    capture: 'transient',
    measurement: 'peak_to_peak',
    minVal: 0,
    typical: 0.05,
    maxVal: 0.2,
    actual: 0.42,
    passed: false,
    justification: 'Ripple must stay below ADC LSB (0.2V for 10-bit, 0-10V range).',
    contextNets: [],
    unit: 'V',
    timeSeries: (() => {
      const N = 500;
      const time = Array.from({ length: N }, (_, i) => i * 0.01 / (N - 1));
      const output = time.map(t => {
        return 7.5 + 0.21 * Math.sin(2 * Math.PI * 1000 * t) + (Math.random() - 0.5) * 0.005;
      });
      return { time, signals: { 'v(output)': output } };
    })(),
  },
  {
    id: 'req-006',
    name: 'REQ-006: Overshoot',
    net: 'output',
    capture: 'transient',
    measurement: 'overshoot',
    minVal: 0,
    typical: 2,
    maxVal: 5,
    actual: 8.2,
    passed: false,
    justification: 'Overshoot must be bounded to protect downstream ADC input.',
    contextNets: ['power_hv'],
    unit: '%',
    timeSeries: (() => {
      const N = 500;
      const time = Array.from({ length: N }, (_, i) => i * 0.5 / (N - 1));
      const output = time.map(t => {
        const wn = 40;
        const zeta = 0.3;
        const wd = wn * Math.sqrt(1 - zeta * zeta);
        if (t < 0.001) return 0;
        return 7.5 * (1 - Math.exp(-zeta * wn * t) * (Math.cos(wd * t) + (zeta / Math.sqrt(1 - zeta * zeta)) * Math.sin(wd * t)));
      });
      const power_hv = time.map(t => t < 0.001 ? 0 : 10.0);
      return { time, signals: { 'v(output)': output, 'v(power_hv)': power_hv } };
    })(),
  },
];
