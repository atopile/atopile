import { forwardRef, useMemo, type HTMLAttributes, type ReactNode } from 'react'
import './Field.css'

/* ---- Field (root) ---- */

export const Field = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className = '', ...props }, ref) => (
    <div ref={ref} className={`field ${className}`.trim()} {...props} />
  )
)
Field.displayName = 'Field'

/* ---- FieldLabel ---- */

export const FieldLabel = forwardRef<HTMLLabelElement, HTMLAttributes<HTMLLabelElement>>(
  ({ className = '', ...props }, ref) => (
    <label ref={ref} className={`field-label ${className}`.trim()} {...props} />
  )
)
FieldLabel.displayName = 'FieldLabel'

/* ---- FieldDescription ---- */

export const FieldDescription = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  ({ className = '', ...props }, ref) => (
    <p ref={ref} className={`field-description ${className}`.trim()} {...props} />
  )
)
FieldDescription.displayName = 'FieldDescription'

/* ---- FieldError ---- */

export interface FieldErrorProps extends HTMLAttributes<HTMLDivElement> {
  /** Array of error objects (renders as list if multiple) */
  errors?: Array<{ message?: string } | undefined>
}

export const FieldError = forwardRef<HTMLDivElement, FieldErrorProps>(
  ({ className = '', children, errors, ...props }, ref) => {
    const content = useMemo((): ReactNode => {
      if (children) return children

      if (!errors?.length) return null

      const unique = [
        ...new Map(errors.map((e) => [e?.message, e])).values(),
      ]

      if (unique.length === 1) return unique[0]?.message ?? null

      return (
        <ul className="field-error-list">
          {unique.map(
            (e, i) => e?.message && <li key={i}>{e.message}</li>
          )}
        </ul>
      )
    }, [children, errors])

    if (!content) return null

    return (
      <div ref={ref} role="alert" className={`field-error ${className}`.trim()} {...props}>
        {content}
      </div>
    )
  }
)
FieldError.displayName = 'FieldError'
