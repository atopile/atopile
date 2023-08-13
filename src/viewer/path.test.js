import { returnConfigFileName,
    concatenateParentPathAndModuleName,
    computeNameDepth,
    provideFirstNameElementFromName,
    provideLastPathElementFromPath } from './path';

// Test returnConfigFileName
describe('returnConfigFileName', () => {
    test('should return path and module', () => {
        expect(returnConfigFileName('foo:bar.bar')).toEqual({file: 'foo', module: 'bar.bar'});
    });
    test('should return path and module', () => {
        expect(returnConfigFileName('foo:')).toEqual({file: 'foo', module: ''});
    });
});

// Test concatenateParentPathAndModuleName
describe('concatenateParentPathAndModuleName', () => {
    test('should return a properly formed path', () => {
        const testCases = [
            { parent_path: null, module_name: 'foo', expected: 'foo:' },
            { parent_path: 'foo:', module_name: 'bar', expected: 'foo:bar' },
            { parent_path: 'foo:bar', module_name: 'bar', expected: 'foo:bar.bar' },
        ];

        testCases.forEach(({ parent_path, module_name, expected }) => {
            const result = concatenateParentPathAndModuleName(parent_path, module_name);
            expect(result).toBe(expected);
        });
    });

    test('should throw an error if called without args', () => {
        expect(function(){ concatenateParentPathAndModuleName(); } ).toThrow(TypeError('Name should be defined'));
    });

    test('should throw an error if path is malformed', () => {
        expect(function(){ concatenateParentPathAndModuleName('fooo', 'bar'); } ).toThrow(Error('Path fooo is malformed'));
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

// Test provideFirstNameElementFromName
describe('provideFirstNameElementFromName', () => {
    test('should throw an error if called with file path', () => {
        expect(function(){ provideFirstNameElementFromName('foo:bar'); } ).toThrow(Error('Name foo:bar cannot contain file path'));
    });

    test('should return first element', () => {
        expect(provideFirstNameElementFromName('foo.bar.bar')).toEqual({first_name: 'foo', remaining: 'bar.bar'});
    });

    test('should return first element', () => {
        expect(provideFirstNameElementFromName('foo')).toEqual({first_name: 'foo', remaining: ''});
    });
});

// Test provideLastPathElementFromPath
describe('provideLastPathElementFromPath', () => {
    test('should throw an error if called without file path', () => {
        expect(function(){ provideLastPathElementFromPath('foo.bar'); } ).toThrow(Error('Path foo.bar is not a path'));
    });

    test('should return the split path', () => {
        expect(provideLastPathElementFromPath('foo:bar1.bar2')).toEqual({file: 'foo', path: 'foo:bar1', name: 'bar2'});
    });

    test('should return the split path', () => {
        expect(provideLastPathElementFromPath('foo:bar')).toEqual({file: 'foo', path: 'foo:', name: 'bar'});
    });
});
