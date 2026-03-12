import { forwardRef, type HTMLAttributes, type TdHTMLAttributes, type ThHTMLAttributes } from 'react'
import './Table.css'

/* ---- Table ---- */

export const Table = forwardRef<
  HTMLTableElement,
  HTMLAttributes<HTMLTableElement>
>(({ className = '', ...props }, ref) => (
  <div className="table-wrapper">
    <table ref={ref} className={`table ${className}`.trim()} {...props} />
  </div>
))
Table.displayName = 'Table'

/* ---- TableHeader ---- */

export const TableHeader = forwardRef<
  HTMLTableSectionElement,
  HTMLAttributes<HTMLTableSectionElement>
>(({ className = '', ...props }, ref) => (
  <thead ref={ref} className={`table-header ${className}`.trim()} {...props} />
))
TableHeader.displayName = 'TableHeader'

/* ---- TableBody ---- */

export const TableBody = forwardRef<
  HTMLTableSectionElement,
  HTMLAttributes<HTMLTableSectionElement>
>(({ className = '', ...props }, ref) => (
  <tbody ref={ref} className={`table-body ${className}`.trim()} {...props} />
))
TableBody.displayName = 'TableBody'

/* ---- TableRow ---- */

export const TableRow = forwardRef<
  HTMLTableRowElement,
  HTMLAttributes<HTMLTableRowElement>
>(({ className = '', ...props }, ref) => (
  <tr ref={ref} className={`table-row ${className}`.trim()} {...props} />
))
TableRow.displayName = 'TableRow'

/* ---- TableHead ---- */

export const TableHead = forwardRef<
  HTMLTableCellElement,
  ThHTMLAttributes<HTMLTableCellElement>
>(({ className = '', ...props }, ref) => (
  <th ref={ref} className={`table-head ${className}`.trim()} {...props} />
))
TableHead.displayName = 'TableHead'

/* ---- TableFooter ---- */

export const TableFooter = forwardRef<
  HTMLTableSectionElement,
  HTMLAttributes<HTMLTableSectionElement>
>(({ className = '', ...props }, ref) => (
  <tfoot ref={ref} className={`table-footer ${className}`.trim()} {...props} />
))
TableFooter.displayName = 'TableFooter'

/* ---- TableCell ---- */

export const TableCell = forwardRef<
  HTMLTableCellElement,
  TdHTMLAttributes<HTMLTableCellElement>
>(({ className = '', ...props }, ref) => (
  <td ref={ref} className={`table-cell ${className}`.trim()} {...props} />
))
TableCell.displayName = 'TableCell'

/* ---- TableCaption ---- */

export const TableCaption = forwardRef<
  HTMLTableCaptionElement,
  HTMLAttributes<HTMLTableCaptionElement>
>(({ className = '', ...props }, ref) => (
  <caption ref={ref} className={`table-caption ${className}`.trim()} {...props} />
))
TableCaption.displayName = 'TableCaption'
