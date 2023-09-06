const fontHeightToPxRatio = 1.1;
const fontLengthToPxRatio = 0.6;

// Definitely need to update this garbage at some point
export function measureText(text, text_size, direction) {
    var string = text + '';
    var lines = string.split("\n");
    var length = 0;
    for (let line of lines) {
        var current_length = line.length;
        console.log('new line')
        console.log(line);
        // Save the longest line
        if (current_length > length) {
            length = current_length;
        };
        console.log(length);
    };
    if (direction == 'length') {
        // will have to fix the magic number
        return length * text_size * fontLengthToPxRatio;
    }
    else if (direction == 'height') {
        return lines.length * text_size * fontHeightToPxRatio;
    }
    else {
        return 0;
    }
};

export function normalizeDimensionToGrid(dimension, grid_size) {
    if (dimension < 0) {
        throw new Error('Dimension cannot be negative');
    }
    let remainder = dimension % grid_size;

    return dimension + (grid_size - remainder);
}