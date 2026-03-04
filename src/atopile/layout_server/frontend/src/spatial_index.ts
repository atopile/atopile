import { BBox, Vec2 } from "./math";

export interface SpatialObject {
    bbox: BBox;
    index: number;
}

export class SpatialIndex {
    private grid: Map<string, number[]> = new Map();
    private cellSize: number = 10;

    constructor(cellSize: number = 10) {
        this.cellSize = cellSize;
    }

    private getKeys(bbox: BBox): string[] {
        const x1 = Math.floor(bbox.x / this.cellSize);
        const y1 = Math.floor(bbox.y / this.cellSize);
        const x2 = Math.floor(bbox.x2 / this.cellSize);
        const y2 = Math.floor(bbox.y2 / this.cellSize);

        const keys: string[] = [];
        for (let x = x1; x <= x2; x++) {
            for (let y = y1; y <= y2; y++) {
                keys.push(`${x},${y}`);
            }
        }
        return keys;
    }

    insert(obj: SpatialObject) {
        const keys = this.getKeys(obj.bbox);
        for (const key of keys) {
            let list = this.grid.get(key);
            if (!list) {
                list = [];
                this.grid.set(key, list);
            }
            list.push(obj.index);
        }
    }

    query(bbox: BBox): number[] {
        const keys = this.getKeys(bbox);
        const resultSet = new Set<number>();
        for (const key of keys) {
            const list = this.grid.get(key);
            if (list) {
                for (const idx of list) {
                    resultSet.add(idx);
                }
            }
        }
        return Array.from(resultSet);
    }

    queryPoint(p: Vec2): number[] {
        const x = Math.floor(p.x / this.cellSize);
        const y = Math.floor(p.y / this.cellSize);
        return this.grid.get(`${x},${y}`) || [];
    }

    clear() {
        this.grid.clear();
    }
}
