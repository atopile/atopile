

export function returnConfigFileName(string) {
    if (string) {
        const [file, module] = string.split(":");
        return {"file": file, "module": module}
    }
    else return null;
}

export function concatenatePathAndName(path, name) {
    if (path == null) {
        return name + ':'
    }
    else if (path.slice(-1) == ':') {
        return path + name;
    }
    else {
        return path + '.' + name;
    }
}

// This function does not support complete paths
// Only names that are separated by a .
export function computeNameDepth(path) {
    let name_list = path.split(".");
    return name_list.length;
}

export function popFirstNameElementFromName(name) {
    // Split the blocks
    const blocks = name.split(".");
    const remaining_blocks = blocks.slice(1, blocks.length);
    const remaining_name = remaining_blocks.join('.');
    const pop = blocks[0];
    return {'pop': pop, 'remaining': remaining_name};
}

export function popLastPathElementFromPath(path) {
    // Split the file name and the blocks
    const file_block = path.split(":");
    const file = file_block[0];
    // Split the blocks
    const blocks = file_block[1].split(".");
    const path_blocks = blocks.slice(0, blocks.length - 1);
    const remaining_path = file + ':' + path_blocks.join('.');
    const name = blocks[blocks.length - 1];
    return {'file': file, 'path': remaining_path, 'name': name};
}