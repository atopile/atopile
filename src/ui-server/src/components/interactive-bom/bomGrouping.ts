import type { RenderModel } from '@layout-viewer/types';
import type { BomGroup } from './types';

function extractPackage(footprintName: string): string {
  const parts = footprintName.split(':');
  const name = parts.length > 1 ? parts[parts.length - 1]! : footprintName;
  return name;
}

function naturalSort(a: string, b: string): number {
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
}

export function buildBomGroups(model: RenderModel): {
  bomGroups: BomGroup[];
  fpIndexToGroupId: Map<number, string>;
} {
  const groupMap = new Map<string, {
    footprintName: string;
    value: string | null;
    designators: string[];
    footprintIndices: number[];
  }>();

  for (let i = 0; i < model.footprints.length; i++) {
    const fp = model.footprints[i]!;
    const key = `${fp.name}\0${fp.value ?? ''}`;

    let group = groupMap.get(key);
    if (!group) {
      group = {
        footprintName: fp.name,
        value: fp.value,
        designators: [],
        footprintIndices: [],
      };
      groupMap.set(key, group);
    }

    if (fp.reference) {
      group.designators.push(fp.reference);
    }
    group.footprintIndices.push(i);
  }

  const bomGroups: BomGroup[] = [];
  const fpIndexToGroupId = new Map<number, string>();

  for (const [key, group] of groupMap) {
    group.designators.sort(naturalSort);
    const id = key;
    const bomGroup: BomGroup = {
      id,
      footprintName: group.footprintName,
      value: group.value,
      package: extractPackage(group.footprintName),
      designators: group.designators,
      quantity: group.footprintIndices.length,
      footprintIndices: group.footprintIndices,
    };
    bomGroups.push(bomGroup);
    for (const fpIdx of group.footprintIndices) {
      fpIndexToGroupId.set(fpIdx, id);
    }
  }

  bomGroups.sort((a, b) => {
    if (a.designators.length > 0 && b.designators.length > 0) {
      return naturalSort(a.designators[0]!, b.designators[0]!);
    }
    if (a.designators.length > 0) return -1;
    if (b.designators.length > 0) return 1;
    return naturalSort(a.footprintName, b.footprintName);
  });

  return { bomGroups, fpIndexToGroupId };
}
