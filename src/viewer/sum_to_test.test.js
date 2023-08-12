import { sum } from './sum_to_test';

test('sum 2 + 3 == 5', () => {
    expect(
        sum(2, 3)
    ).toBe(
        5
    );
});

