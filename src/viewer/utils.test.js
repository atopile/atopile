import * as utils from './utils';

// Test normalizeDimensionToGrid
describe('normalizeDimensionToGrid', () => {
    let grid_size = 5;
    test('should return normalized value', () => {
        expect(utils.normalizeDimensionToGrid(104, grid_size)).toEqual(105);
    });

    test('0 should return grid', () => {
        expect(utils.normalizeDimensionToGrid(0, grid_size)).toEqual(grid_size);
    });

    test('nagative dimesion shoudl throw an error', () => {
        expect(function(){ utils.normalizeDimensionToGrid(-grid_size, grid_size); } ).toThrow(Error('Dimension cannot be negative'));
    });
});