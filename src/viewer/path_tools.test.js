import { returnConfigFileName,
    concatenatePathAndName,
    computeNameDepth,
    popFirstNameElementFromName,
    popLastPathElementFromPath } from './path_tools';

test('compute name depth', () => {
    expect(
        computeNameDepth('this.is.a.test')
    ).toBe(
        4
    );
});