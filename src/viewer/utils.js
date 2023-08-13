
const fontHeightToPxRatio = 1.6;
const fontLengthToPxRatio = 0.7;

// Definitely need to update this garbage at some point
export function measureText(text, text_size, direction) {
    var string = text + '';
    var lines = string.split("\n");
    var width = 0;
    for (let line of lines) {
        var length = line.length;
        if (length > width) {
            width = length;
        };
    };
    if (direction == 'length') {
        // divide by 3 to go from font size to pxl, will have to fix
        return width * text_size * fontLengthToPxRatio;
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