import { returnConfigFileName,
    concatenatePathAndName,
    computeNameDepth,
    popFirstNameElementFromName,
    popLastPathElementFromPath } from './path_tools';

// Test returnConfigFileName
describe('returnConfigFileName', () => {
    test('should return path and module', () => {
        expect(returnConfigFileName('foo:bar.bar')).toEqual({file: 'foo', module: 'bar.bar'});
    });
    test('should return path and module', () => {
        expect(returnConfigFileName('foo:')).toEqual({file: 'foo', module: ''});
    });
});

// Test concatenatePathAndName
describe('concatenatePathAndName', () => {
    test('should return a properly formed path', () => {
        const testCases = [
            { path: null, name: 'foo', expected: 'foo:' },
            { path: 'foo:', name: 'bar', expected: 'foo:bar' },
            { path: 'foo:bar', name: 'bar', expected: 'foo:bar.bar' },
        ];

        testCases.forEach(({ path, name, expected }) => {
            const result = concatenatePathAndName(path, name);
            expect(result).toBe(expected);
        });
    });

    test('should throw an error if called without args', () => {
        expect(function(){ concatenatePathAndName(); } ).toThrow(TypeError('Name should be defined'));
    });

    test('should throw an error if path is malformed', () => {
        expect(function(){ concatenatePathAndName('fooo', 'bar'); } ).toThrow(Error('Path fooo is malformed'));
    });
});

// Test computeNameDepth
describe('computeNameDepth', () => {
    test('should return the correct depth for different inputs', () => {
        // Test cases and expected results
        const testCases = [
            { input: 'foo.bar', expected: 2 },
            { input: 'foo.b.ar', expected: 3 },
            { input: '', expected: 1 },
            { input: '..', expected: 3 }
        ];

        // Iterate over test cases
        testCases.forEach(({ input, expected }) => {
            const result = computeNameDepth(input);
            expect(result).toBe(expected); // Perform the assertion
        });
    });
});

// Test popFirstNameElementFromName
describe('popFirstNameElementFromName', () => {
    test('should throw an error if called with file path', () => {
        expect(function(){ popFirstNameElementFromName('foo:bar'); } ).toThrow(Error('Name foo:bar cannot contain file path'));
    });

    test('should return first element', () => {
        expect(popFirstNameElementFromName('foo.bar.bar')).toEqual({pop: 'foo', remaining: 'bar.bar'});
    });

    test('should return first element', () => {
        expect(popFirstNameElementFromName('foo')).toEqual({pop: 'foo', remaining: ''});
    });
});

// Test popLastPathElementFromPath
describe('popLastPathElementFromPath', () => {
    test('should throw an error if called without file path', () => {
        expect(function(){ popLastPathElementFromPath('foo.bar'); } ).toThrow(Error('Path foo.bar is not a path'));
    });

    test('should return the split path', () => {
        expect(popLastPathElementFromPath('foo:bar1.bar2')).toEqual({file: 'foo', path: 'foo:bar1', name: 'bar2'});
    });

    test('should return the split path', () => {
        expect(popLastPathElementFromPath('foo:bar')).toEqual({file: 'foo', path: 'foo:', name: 'bar'});
    });
});
