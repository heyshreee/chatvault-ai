import { Check, Copy } from 'lucide-react'
import { Highlight, themes } from 'prism-react-renderer'
import type { Language } from 'prism-react-renderer'
import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { cn } from '../../lib/cn'

interface CodeBlockProps {
  code: string
  language: string
}

function CodeBlock({ code, language }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current)
      }
    }
  }, [])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)

      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current)
      }

      timerRef.current = window.setTimeout(() => setCopied(false), 1_500)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="my-4 overflow-hidden rounded-lg border border-line bg-[#080c12]">
      <div className="flex items-center justify-between border-b border-line/80 bg-panel/60 px-3 py-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">
          {language || 'text'}
        </span>
        <button
          type="button"
          onClick={copy}
          className="inline-flex items-center gap-1.5 rounded px-1.5 py-1 text-[10px] font-medium text-muted transition-colors hover:bg-panel-raised hover:text-ink"
          aria-label="Copy code"
        >
          {copied ? (
            <Check className="size-3 text-emerald-400" />
          ) : (
            <Copy className="size-3" />
          )}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <Highlight
        theme={themes.vsDark}
        code={code}
        language={(language || 'text') as Language}
      >
        {({ className, style, tokens, getLineProps, getTokenProps }) => (
          <pre
            className={cn(
              'overflow-x-auto px-4 py-3 font-mono text-[12.5px] leading-6',
              className,
            )}
            style={{ ...style, background: 'transparent' }}
          >
            {tokens.map((line, lineIndex) => (
              <div key={lineIndex} {...getLineProps({ line })}>
                {line.map((token, tokenIndex) => (
                  <span
                    key={tokenIndex}
                    {...getTokenProps({ token })}
                  />
                ))}
              </div>
            ))}
          </pre>
        )}
      </Highlight>
    </div>
  )
}

interface MarkdownProps {
  content: string
  className?: string
}

export function Markdown({ content, className }: MarkdownProps) {
  return (
    <div className={cn('markdown', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre({ children }) {
            return <>{children}</>
          },
          code({ className: codeClassName, children }) {
            const text = String(children).replace(/\n$/, '')
            const match = /language-([\w-]+)/.exec(codeClassName ?? '')
            const isBlock = Boolean(match) || text.includes('\n')

            if (isBlock) {
              return (
                <CodeBlock
                  code={text}
                  language={match?.[1] ?? 'text'}
                />
              )
            }

            return <code>{children}</code>
          },
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noreferrer noopener"
              >
                {children}
              </a>
            )
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
