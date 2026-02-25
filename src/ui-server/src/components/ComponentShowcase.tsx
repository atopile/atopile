/**
 * ComponentShowcase — interactive gallery of all shared components.
 * Import this page into a route or render it standalone to preview the design system.
 */

import { useState } from 'react'
import { Zap, Package, Star, Trash2, Mail, Calendar, Globe } from 'lucide-react'
import type { ColumnDef } from '@tanstack/react-table'

// ---- Primitives ----
import { Badge, BadgeAsLink } from './shared/Badge'
import { Button } from './shared/Button'
import { Input } from './shared/Input'
import { SearchBar, RegexSearchBar } from './shared/SearchBar'
import { Checkbox } from './shared/Checkbox'
import { Spinner } from './shared/Spinner'
import { Skeleton } from './shared/Skeleton'
import { Separator } from './shared/Separator'
import { Alert, AlertTitle, AlertDescription } from './shared/Alert'
import { Field, FieldLabel, FieldDescription, FieldError } from './shared/Field'
import {
  Select, SelectTrigger, SelectValue, SelectContent,
  SelectGroup, SelectItem, SelectLabel, SelectSeparator,
} from './shared/Select'
import {
  Tooltip, TooltipTrigger, TooltipContent, TooltipProvider,
} from './shared/Tooltip'
import {
  HoverCard, HoverCardTrigger, HoverCardContent,
} from './shared/HoverCard'
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
  TableFooter, TableCaption,
} from './shared/Table'
import { DataTable, DataTableColumnHeader } from './shared/DataTable'

// ---- Pre-existing ----
import { EmptyState } from './shared/EmptyState'
import { PanelSearchBox } from './shared/PanelSearchBox'
import { PublisherBadge } from './shared/PublisherBadge'
import { TreeRowHeader } from './shared/TreeRowHeader'

import './ComponentShowcase.css'

/* ================================================================
   Sample data
   ================================================================ */

interface Payment {
  id: string
  amount: number
  status: 'pending' | 'processing' | 'success' | 'failed'
  email: string
}

const payments: Payment[] = [
  { id: 'PAY-001', amount: 250.00, status: 'success', email: 'alice@example.com' },
  { id: 'PAY-002', amount: 150.00, status: 'processing', email: 'bob@example.com' },
  { id: 'PAY-003', amount: 350.00, status: 'success', email: 'carol@example.com' },
  { id: 'PAY-004', amount: 450.00, status: 'failed', email: 'dave@example.com' },
  { id: 'PAY-005', amount: 550.00, status: 'pending', email: 'eve@example.com' },
  { id: 'PAY-006', amount: 200.00, status: 'success', email: 'frank@example.com' },
  { id: 'PAY-007', amount: 320.00, status: 'processing', email: 'grace@example.com' },
]

const paymentColumns: ColumnDef<Payment, unknown>[] = [
  {
    accessorKey: 'id',
    header: ({ column }) => <DataTableColumnHeader column={column} title="ID" />,
  },
  {
    accessorKey: 'status',
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
  },
  {
    accessorKey: 'email',
    header: ({ column }) => <DataTableColumnHeader column={column} title="Email" />,
  },
  {
    accessorKey: 'amount',
    header: ({ column }) => <DataTableColumnHeader column={column} title="Amount" />,
    cell: ({ row }) => {
      const amount = parseFloat(row.getValue('amount'))
      return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)
    },
  },
]

const selectItems = [
  { label: 'Apple', value: 'apple' },
  { label: 'Banana', value: 'banana' },
  { label: 'Cherry', value: 'cherry' },
  { label: 'Date', value: 'date' },
]

/* ================================================================
   Showcase
   ================================================================ */

export function ComponentShowcase() {
  // State for interactive demos
  const [checkA, setCheckA] = useState(false)
  const [checkB, setCheckB] = useState(true)
  const [search, setSearch] = useState('')
  const [searchBasic, setSearchBasic] = useState('')
  const [searchRegex, setSearchRegex] = useState('')
  const [isRegex, setIsRegex] = useState(false)
  const [caseSensitive, setCaseSensitive] = useState(false)
  const [selectVal, setSelectVal] = useState<string | null>(null)
  const [treeExpanded, setTreeExpanded] = useState(false)

  return (
    <div className="showcase">
      <h1>Shared Component Library</h1>

      {/* ---- Badge ---- */}
      <section className="showcase-section">
        <h2>Badge</h2>

        <h3>Variants</h3>
        <div className="showcase-row">
          <Badge variant="default">Default</Badge>
          <Badge variant="secondary">Secondary</Badge>
          <Badge variant="outline">Outline</Badge>
          <Badge variant="destructive">Destructive</Badge>
          <Badge variant="success">Success</Badge>
          <Badge variant="warning">Warning</Badge>
          <Badge variant="info">Info</Badge>
        </div>

        <h3>With icons</h3>
        <div className="showcase-row">
          <Badge variant="success"><Zap size={12} /> Passed</Badge>
          <Badge variant="destructive"><Trash2 size={12} /> Failed</Badge>
          <Badge variant="info"><Mail size={12} /> 3 new</Badge>
        </div>

        <h3>As link</h3>
        <div className="showcase-row">
          <BadgeAsLink variant="default" href="#">Default</BadgeAsLink>
          <BadgeAsLink variant="secondary" href="#">Secondary</BadgeAsLink>
          <BadgeAsLink variant="outline" href="#">Outline</BadgeAsLink>
          <BadgeAsLink variant="info" href="#">Docs</BadgeAsLink>
        </div>
      </section>

      <hr className="showcase-divider" />

      {/* ---- Button ---- */}
      <section className="showcase-section">
        <h2>Button</h2>

        <h3>Variants</h3>
        <div className="showcase-row">
          <Button variant="default">Default</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive">Destructive</Button>
          <Button variant="link">Link</Button>
        </div>

        <h3>Sizes</h3>
        <div className="showcase-row">
          <Button size="sm">Small</Button>
          <Button size="md">Medium</Button>
          <Button size="lg">Large</Button>
          <Button size="icon" aria-label="Star"><Star size={16} /></Button>
        </div>

        <h3>With icons</h3>
        <div className="showcase-row">
          <Button><Mail size={14} /> Send Email</Button>
          <Button variant="destructive"><Trash2 size={14} /> Delete</Button>
          <Button variant="outline" disabled>Disabled</Button>
        </div>
      </section>

      <hr className="showcase-divider" />

      {/* ---- Input ---- */}
      <section className="showcase-section">
        <h2>Input</h2>

        <h3>Default</h3>
        <div className="showcase-grid">
          <Input placeholder="Email address..." type="email" />
          <Input placeholder="Search..." type="search" />
        </div>

        <h3>Disabled</h3>
        <div className="showcase-grid">
          <Input placeholder="Disabled input" disabled />
        </div>

        <h3>File</h3>
        <div className="showcase-grid">
          <Input type="file" />
        </div>

        <h3>Invalid</h3>
        <div className="showcase-grid">
          <Input defaultValue="bad-email" aria-invalid="true" />
        </div>
      </section>

      <hr className="showcase-divider" />

      {/* ---- SearchBar ---- */}
      <section className="showcase-section">
        <h2>SearchBar</h2>

        <h3>Basic</h3>
        <div className="showcase-grid">
          <SearchBar value={searchBasic} onChange={setSearchBasic} placeholder="Search components..." />
          <SearchBar value="" onChange={() => {}} placeholder="Disabled" disabled />
        </div>

        <h3>With regex toggle</h3>
        <div className="showcase-grid">
          <RegexSearchBar
            value={searchRegex}
            onChange={setSearchRegex}
            isRegex={isRegex}
            onRegexChange={setIsRegex}
            caseSensitive={caseSensitive}
            onCaseSensitiveChange={setCaseSensitive}
            placeholder="Filter by name..."
          />
        </div>
      </section>

      <hr className="showcase-divider" />

      {/* ---- Checkbox ---- */}
      <section className="showcase-section">
        <h2>Checkbox</h2>
        <div className="showcase-row">
          <Checkbox checked={checkA} onCheckedChange={setCheckA} />
          <span>{checkA ? 'Checked' : 'Unchecked'}</span>
          <Checkbox checked={checkB} onCheckedChange={setCheckB} />
          <span>{checkB ? 'Checked' : 'Unchecked'}</span>
          <Checkbox disabled aria-label="Disabled" />
        </div>
      </section>

      <hr className="showcase-divider" />

      {/* ---- Spinner ---- */}
      <section className="showcase-section">
        <h2>Spinner</h2>
        <div className="showcase-row">
          <Spinner size={14} />
          <Spinner size={20} />
          <Spinner size={28} />
          <Button disabled><Spinner size={14} /> Loading...</Button>
        </div>
      </section>

      <hr className="showcase-divider" />

      {/* ---- Skeleton ---- */}
      <section className="showcase-section">
        <h2>Skeleton</h2>
        <div className="showcase-col" style={{ maxWidth: 320 }}>
          <Skeleton style={{ height: 12, width: '80%' }} />
          <Skeleton style={{ height: 12, width: '60%' }} />
          <Skeleton style={{ height: 32, width: '100%', borderRadius: 'var(--radius-md)' }} />
        </div>
      </section>

      <hr className="showcase-divider" />

      {/* ---- Separator ---- */}
      <section className="showcase-section">
        <h2>Separator</h2>
        <div className="showcase-col" style={{ maxWidth: 320 }}>
          <span>Above</span>
          <Separator />
          <span>Below</span>
        </div>
        <h3>Vertical</h3>
        <div className="showcase-row" style={{ height: 32 }}>
          <span>Left</span>
          <Separator orientation="vertical" />
          <span>Right</span>
        </div>
      </section>

      <hr className="showcase-divider" />

      {/* ---- Tooltip ---- */}
      <section className="showcase-section">
        <h2>Tooltip</h2>
        <TooltipProvider delayDuration={200}>
          <div className="showcase-row">
            <Tooltip>
              <TooltipTrigger>
                <Button variant="outline">Hover me (top)</Button>
              </TooltipTrigger>
              <TooltipContent side="top">Tooltip on top</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger>
                <Button variant="outline">Bottom</Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">Tooltip on bottom</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger>
                <Button variant="outline">Left</Button>
              </TooltipTrigger>
              <TooltipContent side="left">Tooltip on left</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger>
                <Button variant="outline">Right</Button>
              </TooltipTrigger>
              <TooltipContent side="right">Tooltip on right</TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>
      </section>

      <hr className="showcase-divider" />

      {/* ---- HoverCard ---- */}
      <section className="showcase-section">
        <h2>HoverCard</h2>
        <div className="showcase-row">
          <HoverCard>
            <HoverCardTrigger>
              <Button variant="link">@atopile</Button>
            </HoverCardTrigger>
            <HoverCardContent side="bottom">
              <div style={{ display: 'flex', gap: 'var(--spacing-sm)', alignItems: 'flex-start' }}>
                <Zap size={20} />
                <div>
                  <p style={{ fontWeight: 600, margin: 0 }}>atopile</p>
                  <p style={{ margin: '4px 0', color: 'var(--text-secondary)' }}>
                    Design electronics with code.
                  </p>
                  <div style={{ display: 'flex', gap: 'var(--spacing-sm)', color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
                    <span><Calendar size={12} /> Joined 2023</span>
                  </div>
                </div>
              </div>
            </HoverCardContent>
          </HoverCard>
        </div>
      </section>

      <hr className="showcase-divider" />

      {/* ---- Alert ---- */}
      <section className="showcase-section">
        <h2>Alert</h2>
        <div className="showcase-col">
          <Alert variant="default">
            <AlertTitle>Default Alert</AlertTitle>
            <AlertDescription>This is a default alert with general information.</AlertDescription>
          </Alert>
          <Alert variant="info">
            <AlertTitle>Info</AlertTitle>
            <AlertDescription>Your build is running in the background.</AlertDescription>
          </Alert>
          <Alert variant="success">
            <AlertTitle>Success</AlertTitle>
            <AlertDescription>All 42 tests passed successfully.</AlertDescription>
          </Alert>
          <Alert variant="warning">
            <AlertTitle>Warning</AlertTitle>
            <AlertDescription>Some components have unresolved parameters.</AlertDescription>
          </Alert>
          <Alert variant="destructive">
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>Build failed due to unresolvable constraints.</AlertDescription>
          </Alert>
        </div>
      </section>

      <hr className="showcase-divider" />

      {/* ---- Field ---- */}
      <section className="showcase-section">
        <h2>Field</h2>
        <div className="showcase-grid">
          <Field>
            <FieldLabel>Project Name</FieldLabel>
            <FieldDescription>Choose a unique name for your project.</FieldDescription>
            <input
              type="text"
              placeholder="my-project"
              style={{
                padding: 'var(--spacing-xs) var(--spacing-sm)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                fontSize: 'var(--font-size-sm)',
              }}
            />
          </Field>
          <Field data-invalid>
            <FieldLabel>Email</FieldLabel>
            <input
              type="email"
              defaultValue="bad-email"
              style={{
                padding: 'var(--spacing-xs) var(--spacing-sm)',
                border: '1px solid var(--error)',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                fontSize: 'var(--font-size-sm)',
              }}
            />
            <FieldError>Please enter a valid email address.</FieldError>
          </Field>
          <Field data-invalid>
            <FieldLabel>Password</FieldLabel>
            <FieldError
              errors={[
                { message: 'Must be at least 8 characters' },
                { message: 'Must contain a number' },
              ]}
            />
          </Field>
        </div>
      </section>

      <hr className="showcase-divider" />

      {/* ---- Select ---- */}
      <section className="showcase-section">
        <h2>Select</h2>
        <div className="showcase-grid">
          <div className="showcase-card">
            <h3 style={{ margin: '0 0 var(--spacing-sm)' }}>Basic</h3>
            <Select items={selectItems} value={selectVal} onValueChange={setSelectVal}>
              <SelectTrigger>
                <SelectValue placeholder="Pick a fruit..." />
              </SelectTrigger>
              <SelectContent>
                {selectItems.map((i) => (
                  <SelectItem key={i.value} value={i.value}>{i.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="showcase-card">
            <h3 style={{ margin: '0 0 var(--spacing-sm)' }}>Disabled</h3>
            <Select items={selectItems} disabled defaultValue="banana">
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {selectItems.map((i) => (
                  <SelectItem key={i.value} value={i.value}>{i.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="showcase-card">
            <h3 style={{ margin: '0 0 var(--spacing-sm)' }}>With groups</h3>
            <Select
              items={[
                { label: 'React', value: 'react' },
                { label: 'Vue', value: 'vue' },
                { label: 'Svelte', value: 'svelte' },
                { label: 'Express', value: 'express' },
                { label: 'Fastify', value: 'fastify' },
              ]}
            >
              <SelectTrigger>
                <SelectValue placeholder="Pick a framework..." />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectLabel>Frontend</SelectLabel>
                  <SelectItem value="react">React</SelectItem>
                  <SelectItem value="vue">Vue</SelectItem>
                  <SelectItem value="svelte">Svelte</SelectItem>
                </SelectGroup>
                <SelectSeparator />
                <SelectGroup>
                  <SelectLabel>Backend</SelectLabel>
                  <SelectItem value="express">Express</SelectItem>
                  <SelectItem value="fastify">Fastify</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>

          <div className="showcase-card">
            <h3 style={{ margin: '0 0 var(--spacing-sm)' }}>Invalid</h3>
            <Select items={selectItems}>
              <SelectTrigger aria-invalid>
                <SelectValue placeholder="Required field..." />
              </SelectTrigger>
              <SelectContent>
                {selectItems.map((i) => (
                  <SelectItem key={i.value} value={i.value}>{i.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </section>

      <hr className="showcase-divider" />

      {/* ---- Table ---- */}
      <section className="showcase-section">
        <h2>Table</h2>
        <Table>
          <TableCaption>A list of recent components.</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>Component</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Package</TableHead>
              <TableHead style={{ textAlign: 'right' }}>Value</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell className="font-medium">R1</TableCell>
              <TableCell>Resistor</TableCell>
              <TableCell>0402</TableCell>
              <TableCell style={{ textAlign: 'right' }}>10k</TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="font-medium">C1</TableCell>
              <TableCell>Capacitor</TableCell>
              <TableCell>0402</TableCell>
              <TableCell style={{ textAlign: 'right' }}>100nF</TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="font-medium">U1</TableCell>
              <TableCell>IC</TableCell>
              <TableCell>QFN-24</TableCell>
              <TableCell style={{ textAlign: 'right' }}>RP2040</TableCell>
            </TableRow>
          </TableBody>
          <TableFooter>
            <TableRow>
              <TableCell colSpan={3}>Total components</TableCell>
              <TableCell style={{ textAlign: 'right' }}>3</TableCell>
            </TableRow>
          </TableFooter>
        </Table>
      </section>

      <hr className="showcase-divider" />

      {/* ---- DataTable ---- */}
      <section className="showcase-section">
        <h2>DataTable</h2>
        <DataTable
          columns={paymentColumns}
          data={payments}
          getRowId={(row) => row.id}
          filterColumn="email"
          filterPlaceholder="Filter emails..."
          enableRowSelection
          enableColumnVisibility
          pageSizeOptions={[5, 10, 20]}
          defaultPageSize={5}
        />
      </section>

      <hr className="showcase-divider" />

      {/* ---- Pre-existing: EmptyState ---- */}
      <section className="showcase-section">
        <h2>EmptyState</h2>
        <div className="showcase-card">
          <EmptyState
            title="No components found"
            description="Try adjusting your search or adding a new component."
          />
        </div>
      </section>

      <hr className="showcase-divider" />

      {/* ---- Pre-existing: PanelSearchBox ---- */}
      <section className="showcase-section">
        <h2>PanelSearchBox</h2>
        <div style={{ maxWidth: 320 }}>
          <PanelSearchBox
            value={search}
            onChange={setSearch}
            placeholder="Search components..."
          />
        </div>
      </section>

      <hr className="showcase-divider" />

      {/* ---- Pre-existing: PublisherBadge ---- */}
      <section className="showcase-section">
        <h2>PublisherBadge</h2>
        <div className="showcase-row">
          <PublisherBadge publisher="atopile" showPrefix />
          <PublisherBadge publisher="community" showPrefix />
        </div>
      </section>

      <hr className="showcase-divider" />

      {/* ---- Pre-existing: TreeRowHeader ---- */}
      <section className="showcase-section">
        <h2>TreeRowHeader</h2>
        <div className="showcase-col" style={{ maxWidth: 400 }}>
          <TreeRowHeader
            isExpandable
            isExpanded={treeExpanded}
            onClick={() => setTreeExpanded(!treeExpanded)}
            icon={<Package size={14} />}
            label="generics"
            secondaryLabel="Module"
            count={12}
          />
          {treeExpanded && (
            <>
              <div style={{ paddingLeft: 24 }}>
                <TreeRowHeader
                  icon={<Globe size={14} />}
                  label="Resistor"
                  secondaryLabel="Component"
                />
              </div>
              <div style={{ paddingLeft: 24 }}>
                <TreeRowHeader
                  icon={<Globe size={14} />}
                  label="Capacitor"
                  secondaryLabel="Component"
                />
              </div>
            </>
          )}
          <TreeRowHeader
            isExpandable
            isExpanded={false}
            icon={<Package size={14} />}
            label="power"
            secondaryLabel="Module"
            count={5}
          />
        </div>
      </section>
    </div>
  )
}
