import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { CopyableCodeBlock } from './shared/CopyableCodeBlock'

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
          code({ className: codeClassName, children, node, ...rest }) {
            const match = /language-(\w+)/.exec(codeClassName || '')
            const language = match?.[1] || ''
            const code = String(children).replace(/\n$/, '')

            // In react-markdown v9, inline is determined by checking if parent is not 'pre'
            // The node's parent tagName tells us if this is a code block (wrapped in pre) or inline
            const isInline = !node?.position || !codeClassName

            if (isInline) {
              return <code className={codeClassName} {...rest}>{children}</code>
            }

            return (
              <CopyableCodeBlock
                label={language ? `${language}` : 'code'}
                code={code}
                highlightAto={language === 'ato'}
              />
            )
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
