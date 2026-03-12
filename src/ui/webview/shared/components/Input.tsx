import { forwardRef, type InputHTMLAttributes } from 'react'
import './Input.css'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', type, ...props }, ref) => {
    const cls = `input ${className}`.trim()
    return <input ref={ref} type={type} className={cls} {...props} />
  }
)
Input.displayName = 'Input'
