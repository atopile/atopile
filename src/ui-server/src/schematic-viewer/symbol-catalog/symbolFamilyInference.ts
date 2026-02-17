import type {
  SchematicComponent,
  SchematicSymbolFamily,
} from '../types/schematic';

function getDesignatorPrefix(designator: string): string {
  return designator.replace(/[^A-Za-z]/g, '').toUpperCase();
}

export function inferSymbolFamily(
  component: SchematicComponent,
): SchematicSymbolFamily | null {
  // Connectors stay on the generic box renderer for now.
  if (component.symbolFamily === 'connector') return null;
  if (component.symbolFamily) return component.symbolFamily;

  const designatorPrefix = getDesignatorPrefix(component.designator);
  const haystack = [
    component.name,
    designatorPrefix,
    component.reference,
    component.symbolVariant,
    component.packageCode,
  ].join(' ').toLowerCase();

  if (haystack.includes('led')) return 'led';
  if (haystack.includes('testpoint') || designatorPrefix.startsWith('TP')) return 'testpoint';

  if (
    haystack.includes('pmos')
    || haystack.includes('p-mos')
    || haystack.includes('pfet')
    || haystack.includes('p-fet')
    || haystack.includes('pchannel')
    || haystack.includes('p-channel')
  ) {
    return 'mosfet_p';
  }
  if (
    haystack.includes('nmos')
    || haystack.includes('n-mos')
    || haystack.includes('nfet')
    || haystack.includes('n-fet')
    || haystack.includes('nchannel')
    || haystack.includes('n-channel')
  ) {
    return 'mosfet_n';
  }
  if (
    haystack.includes('mosfet')
    || /(^|[^a-z0-9])fet([^a-z0-9]|$)/.test(haystack)
  ) {
    return 'mosfet_n';
  }

  if (haystack.includes('pnp')) return 'transistor_pnp';
  if (haystack.includes('npn')) return 'transistor_npn';
  if (
    designatorPrefix.startsWith('Q')
    || haystack.includes('bjt')
    || haystack.includes('transistor')
  ) {
    return 'transistor_npn';
  }

  if (
    haystack.includes('capacitorpolarized')
    || haystack.includes('capacitor_polarized')
    || haystack.includes('polarized')
    || haystack.includes('electrolytic')
  ) {
    return 'capacitor_polarized';
  }
  if (haystack.includes('capacitor') || designatorPrefix.startsWith('C')) return 'capacitor';
  if (haystack.includes('resistor') || designatorPrefix.startsWith('R')) return 'resistor';
  if (haystack.includes('inductor') || designatorPrefix.startsWith('L')) return 'inductor';
  if (haystack.includes('diode') || designatorPrefix.startsWith('D')) return 'diode';

  return null;
}
