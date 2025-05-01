// scripts/convert-to-mdx.js
const fs = require('fs');
const path = require('path');

// Configuration
const sourceDir = 'examples';
const outputDir = 'converted-examples';

// Create output directory if it doesn't exist
if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
}

// Get all example files
const files = getAllFiles(sourceDir);

// Process each file
files.forEach(file => {
    const content = fs.readFileSync(file, 'utf8');

    // Convert content to MDX (customize this part for your specific needs)
    const mdxContent = convertToMDX(content);

    // Calculate the output path
    const relativePath = path.relative(sourceDir, file);
    const outputPath = path.join(outputDir, relativePath).replace(/\.\w+$/, '.mdx');

    // Ensure the output directory exists
    const outputFileDir = path.dirname(outputPath);
    if (!fs.existsSync(outputFileDir)) {
        fs.mkdirSync(outputFileDir, { recursive: true });
    }

    // Write the MDX file
    fs.writeFileSync(outputPath, mdxContent);
    console.log(`Converted ${file} to ${outputPath}`);
});

// Function to get all files in a directory recursively
function getAllFiles(dir) {
    let results = [];
    const list = fs.readdirSync(dir);

    list.forEach(file => {
        const filePath = path.join(dir, file);
        const stat = fs.statSync(filePath);

        if (stat && stat.isDirectory()) {
            // Recursively get files from subdirectories
            results = results.concat(getAllFiles(filePath));
        } else {
            // Only process files with extensions you want to convert
            if (/\.(py|ato)$/.test(filePath)) {
                results.push(filePath);
            }
        }
    });

    return results;
}

// Function to convert content to MDX
function convertToMDX(content) {
    // This is where you'll implement your conversion logic
    // For example, adding frontmatter, transforming code examples, etc.

    const mdxContent = `
\`\`\`python
${content}
\`\`\`
`;
    return mdxContent;
}
