import { memo, useEffect, useRef } from 'react';
import hljs from 'highlight.js/lib/core';
// Import commonly used languages
import javascript from 'highlight.js/lib/languages/javascript';
import typescript from 'highlight.js/lib/languages/typescript';
import python from 'highlight.js/lib/languages/python';
import bash from 'highlight.js/lib/languages/bash';
import json from 'highlight.js/lib/languages/json';
import xml from 'highlight.js/lib/languages/xml';
import css from 'highlight.js/lib/languages/css';
import markdown from 'highlight.js/lib/languages/markdown';
import yaml from 'highlight.js/lib/languages/yaml';
import sql from 'highlight.js/lib/languages/sql';
import rust from 'highlight.js/lib/languages/rust';
import go from 'highlight.js/lib/languages/go';

// Register languages
hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('js', javascript);
hljs.registerLanguage('typescript', typescript);
hljs.registerLanguage('ts', typescript);
hljs.registerLanguage('tsx', typescript);
hljs.registerLanguage('jsx', javascript);
hljs.registerLanguage('python', python);
hljs.registerLanguage('py', python);
hljs.registerLanguage('bash', bash);
hljs.registerLanguage('sh', bash);
hljs.registerLanguage('shell', bash);
hljs.registerLanguage('zsh', bash);
hljs.registerLanguage('json', json);
hljs.registerLanguage('html', xml);
hljs.registerLanguage('xml', xml);
hljs.registerLanguage('css', css);
hljs.registerLanguage('markdown', markdown);
hljs.registerLanguage('md', markdown);
hljs.registerLanguage('yaml', yaml);
hljs.registerLanguage('yml', yaml);
hljs.registerLanguage('sql', sql);
hljs.registerLanguage('rust', rust);
hljs.registerLanguage('rs', rust);
hljs.registerLanguage('go', go);
hljs.registerLanguage('golang', go);

interface CodeBlockProps {
  code: string;
  language?: string;
  className?: string;
}

export const CodeBlock = memo(function CodeBlock({ code, language, className = '' }: CodeBlockProps) {
  const codeRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (codeRef.current) {
      // Remove previous highlighting
      codeRef.current.removeAttribute('data-highlighted');

      if (language && hljs.getLanguage(language)) {
        try {
          const result = hljs.highlight(code, { language });
          codeRef.current.innerHTML = result.value;
          codeRef.current.setAttribute('data-highlighted', 'yes');
        } catch {
          // If highlighting fails, just show plain text
          codeRef.current.textContent = code;
        }
      } else {
        // Auto-detect language
        try {
          const result = hljs.highlightAuto(code);
          codeRef.current.innerHTML = result.value;
          codeRef.current.setAttribute('data-highlighted', 'yes');
        } catch {
          codeRef.current.textContent = code;
        }
      }
    }
  }, [code, language]);

  return (
    <pre className={`bg-gray-800 border border-gray-700 rounded p-3 overflow-x-auto ${className}`}>
      <code
        ref={codeRef}
        className={`hljs text-sm ${language ? `language-${language}` : ''}`}
      >
        {code}
      </code>
    </pre>
  );
});

export default CodeBlock;
