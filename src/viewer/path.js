export function returnConfigFileName(string) {
    if (string) {
        const [file, module] = string.split(":");
        return {"file": file, "module": module}
    }
    else return null;
}

// This function builds a path from the parent_path and module name
// Example 1: parent_path = 'foo', module_name = 'bar', returns 'foo:bar'
// Example 2: parent_path = null, module_name = 'bar', returns 'bar:'
// Example 3: parent_path = 'foo:bar', module_name = 'test', returns 'foo:bar.test'
export function concatenateParentPathAndModuleName(parent_path, module_name) {
    if (module_name == null) {
        throw new TypeError('Name should be defined');
    }
    if (parent_path == null) {
        return module_name + ':'
    }
    if (parent_path.slice(-1) == ':') {
        return parent_path + module_name;
    }
    if (parent_path.split(':').length != 2) {
        throw new Error('Path ' + parent_path + ' is malformed');
    }
    else {
        return parent_path + '.' + module_name;
    }
}

// This function does not support complete paths
// Only names that are separated by a .
export function computeNameDepth(path) {
    let name_list = path.split(".");
    return name_list.length;
}

export function provideFirstNameElementFromName(name) {
    // Check that there is no file
    if (name.split(':').length != 1) {
        throw new Error('Name ' + name + ' cannot contain file path');
    }
    // Split the blocks
    const blocks = name.split(".");
    const remaining_blocks = blocks.slice(1, blocks.length);
    const remaining_name = remaining_blocks.join('.');
    const first_name = blocks[0];
    return {'first_name': first_name, 'remaining': remaining_name};
}

export function provideLastPathElementFromPath(path) {
    // Check that there is no file
    if (path.split(':').length != 2) {
        throw new Error('Path ' + path + ' is not a path');
    }
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