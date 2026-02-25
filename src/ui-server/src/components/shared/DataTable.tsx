import { useState, useEffect, useRef } from 'react'
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type ColumnFiltersState,
  type SortingState,
  type VisibilityState,
} from '@tanstack/react-table'
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Settings2,
  X,
} from 'lucide-react'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from './Table'
import { Checkbox } from './Checkbox'
import { Button } from './Button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './Select'
import { Separator } from './Separator'
import './DataTable.css'

// Re-export ColumnDef for consumer convenience
export type { ColumnDef }

/* ============================
   DataTableColumnHeader
   Sortable header cell helper
   ============================ */

export interface DataTableColumnHeaderProps<TData, TValue> {
  column: import('@tanstack/react-table').Column<TData, TValue>
  title: string
  className?: string
}

export function DataTableColumnHeader<TData, TValue>({
  column,
  title,
}: DataTableColumnHeaderProps<TData, TValue>) {
  if (!column.getCanSort()) {
    return <span>{title}</span>
  }

  const sorted = column.getIsSorted()

  return (
    <button
      className="data-table-sort-btn"
      onClick={() => column.toggleSorting()}
    >
      {title}
      {sorted === 'asc' ? (
        <ArrowUp size={12} className="sort-icon active" />
      ) : sorted === 'desc' ? (
        <ArrowDown size={12} className="sort-icon active" />
      ) : (
        <ArrowUpDown size={12} className="sort-icon" />
      )}
    </button>
  )
}

/* ============================
   DataTable
   ============================ */

export interface DataTableProps<TData, TValue> {
  /** TanStack column definitions */
  columns: ColumnDef<TData, TValue>[]
  /** Row data */
  data: TData[]
  /** Unique key per row (defaults to index) */
  getRowId?: (row: TData, index: number) => string
  /** Filter placeholder */
  filterPlaceholder?: string
  /** Column id to filter on (omit to disable filter input) */
  filterColumn?: string
  /** Enable row selection checkboxes */
  enableRowSelection?: boolean
  /** Enable column visibility controls */
  enableColumnVisibility?: boolean
  /** Page size options (omit or empty to disable pagination) */
  pageSizeOptions?: number[]
  /** Default page size */
  defaultPageSize?: number
  /** Empty state message */
  emptyMessage?: string
}

export function DataTable<TData, TValue>({
  columns,
  data,
  getRowId,
  filterPlaceholder = 'Filter...',
  filterColumn,
  enableRowSelection = false,
  enableColumnVisibility = false,
  pageSizeOptions,
  defaultPageSize = 10,
  emptyMessage = 'No results.',
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = useState({})

  const paginated = pageSizeOptions && pageSizeOptions.length > 0

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
    },
    initialState: {
      pagination: {
        pageSize: defaultPageSize,
      },
    },
    getRowId,
    enableRowSelection,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    ...(paginated ? { getPaginationRowModel: getPaginationRowModel() } : {}),
  })

  const isFiltered = columnFilters.length > 0

  /* ---- View options dropdown ---- */
  const [viewMenuOpen, setViewMenuOpen] = useState(false)
  const viewMenuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!viewMenuOpen) return
    function handleClick(e: MouseEvent) {
      if (viewMenuRef.current && !viewMenuRef.current.contains(e.target as Node)) {
        setViewMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [viewMenuOpen])

  /* ---- Filter value (for the single-column text filter) ---- */
  const filterValueStr = filterColumn
    ? (table.getColumn(filterColumn)?.getFilterValue() as string) ?? ''
    : ''

  return (
    <div className="data-table">
      {/* Toolbar */}
      {(filterColumn || enableColumnVisibility) && (
        <div className="data-table-toolbar">
          <div className="data-table-toolbar-left">
            {filterColumn && (
              <div className="data-table-filter">
                <input
                  placeholder={filterPlaceholder}
                  value={filterValueStr}
                  onChange={(e) =>
                    table.getColumn(filterColumn)?.setFilterValue(e.target.value)
                  }
                />
              </div>
            )}
            {isFiltered && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => table.resetColumnFilters()}
              >
                Reset
                <X size={14} />
              </Button>
            )}
          </div>
          {enableColumnVisibility && (
            <div className="data-table-view-options" ref={viewMenuRef}>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setViewMenuOpen(!viewMenuOpen)}
              >
                <Settings2 size={14} />
                View
              </Button>
              {viewMenuOpen && (
                <div className="data-table-view-menu">
                  <div className="data-table-view-title">Toggle columns</div>
                  <Separator />
                  {table
                    .getAllColumns()
                    .filter(
                      (col) =>
                        typeof col.accessorFn !== 'undefined' &&
                        col.getCanHide()
                    )
                    .map((col) => (
                      <button
                        key={col.id}
                        className="data-table-view-item"
                        onClick={() => col.toggleVisibility(!col.getIsVisible())}
                      >
                        <Checkbox
                          checked={col.getIsVisible()}
                          onCheckedChange={() => {}} // handled by button click
                        />
                        {col.id}
                      </button>
                    ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Table */}
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id} colSpan={header.colSpan}>
                  {header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext())}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows?.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow
                key={row.id}
                data-state={row.getIsSelected() ? 'selected' : undefined}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell
                colSpan={columns.length}
                className="data-table-empty"
              >
                {emptyMessage}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {/* Footer */}
      {(enableRowSelection || paginated) && (
        <div className="data-table-footer">
          {enableRowSelection ? (
            <div className="data-table-selection-info">
              {table.getFilteredSelectedRowModel().rows.length} of{' '}
              {table.getFilteredRowModel().rows.length} row(s) selected
            </div>
          ) : (
            <div />
          )}

          {paginated && (
            <>
              <div className="data-table-page-size">
                <span>Rows per page</span>
                <Select
                  items={pageSizeOptions!.map((s) => ({
                    label: String(s),
                    value: String(s),
                  }))}
                  value={String(table.getState().pagination.pageSize)}
                  onValueChange={(v) => {
                    if (v) table.setPageSize(Number(v))
                  }}
                >
                  <SelectTrigger className="data-table-page-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {pageSizeOptions!.map((size) => (
                      <SelectItem key={size} value={String(size)}>
                        {size}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="data-table-page-info">
                Page {table.getState().pagination.pageIndex + 1} of{' '}
                {table.getPageCount()}
              </div>
              <div className="data-table-page-controls">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!table.getCanPreviousPage()}
                  onClick={() => table.setPageIndex(0)}
                  aria-label="First page"
                >
                  <ChevronsLeft size={14} />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!table.getCanPreviousPage()}
                  onClick={() => table.previousPage()}
                  aria-label="Previous page"
                >
                  <ChevronLeft size={14} />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!table.getCanNextPage()}
                  onClick={() => table.nextPage()}
                  aria-label="Next page"
                >
                  <ChevronRight size={14} />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!table.getCanNextPage()}
                  onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                  aria-label="Last page"
                >
                  <ChevronsRight size={14} />
                </Button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
