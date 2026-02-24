import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { PrismLight as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import yaml from 'react-syntax-highlighter/dist/esm/languages/prism/yaml'
import bash from 'react-syntax-highlighter/dist/esm/languages/prism/bash'
import python from 'react-syntax-highlighter/dist/esm/languages/prism/python'
import json from 'react-syntax-highlighter/dist/esm/languages/prism/json'
import { highlightAtoCode } from '../utils/codeHighlight'

SyntaxHighlighter.registerLanguage('yaml', yaml)
SyntaxHighlighter.registerLanguage('bash', bash)
SyntaxHighlighter.registerLanguage('python', python)
SyntaxHighlighter.registerLanguage('json', json)

interface MarkdownRendererProps {
  content: string
  className?: string
}

export default function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={['markdown-body', className].filter(Boolean).join(' ')}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p({ children }) {
            return <div className="markdown-paragraph">{children}</div>
          },
          code(props) {
            const { children, className, node, ...rest } = props
            const match = /language-(\w+)/.exec(className || '')
            if (!match) {
              return (
                <code {...rest} className={className}>
                  {children}
                </code>
              )
            }
            const language = match[1]
            const code = String(children).replace(/\n$/, '')
            if (language === 'ato') {
              return (
                <pre className="ato-code-block">
                  {highlightAtoCode(code)}
                </pre>
              )
            }
            return (
              <SyntaxHighlighter
                style={oneDark}
                language={language}
                PreTag="div"
              >
                {code}
              </SyntaxHighlighter>
            )
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
