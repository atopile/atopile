/**
 * Select component tests
 * Covers keyboard navigation (arrow keys, Home/End, Enter, Escape) and
 * type-ahead for the shared accessible Select.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '../components/shared/Select';

const ITEMS = [
  { label: 'Apple', value: 'apple' },
  { label: 'Banana', value: 'banana' },
  { label: 'Cherry', value: 'cherry' },
];

function Harness({
  onValueChange,
}: {
  onValueChange?: (v: string | null) => void;
}) {
  return (
    <Select items={ITEMS} onValueChange={onValueChange}>
      <SelectTrigger>
        <SelectValue placeholder='Pick' />
      </SelectTrigger>
      <SelectContent>
        {ITEMS.map((it) => (
          <SelectItem key={it.value} value={it.value}>
            {it.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

const trigger = () => screen.getByRole('combobox');
const options = () => screen.getAllByRole('option');
const highlighted = () =>
  options().find((o) => o.getAttribute('data-highlighted') === 'true');

describe('Select keyboard navigation', () => {
  it('is closed initially', () => {
    render(<Harness />);
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    expect(trigger()).toHaveAttribute('aria-expanded', 'false');
  });

  it('opens on ArrowDown and highlights the first item', () => {
    render(<Harness />);
    fireEvent.keyDown(trigger(), { key: 'ArrowDown' });
    expect(screen.getByRole('listbox')).toBeInTheDocument();
    expect(highlighted()).toHaveTextContent('Apple');
  });

  it('moves the highlight down and wraps to the top', () => {
    render(<Harness />);
    fireEvent.keyDown(trigger(), { key: 'ArrowDown' }); // open -> Apple
    fireEvent.keyDown(trigger(), { key: 'ArrowDown' }); // Banana
    expect(highlighted()).toHaveTextContent('Banana');
    fireEvent.keyDown(trigger(), { key: 'ArrowDown' }); // Cherry
    fireEvent.keyDown(trigger(), { key: 'ArrowDown' }); // wrap -> Apple
    expect(highlighted()).toHaveTextContent('Apple');
  });

  it('wraps to the bottom with ArrowUp', () => {
    render(<Harness />);
    fireEvent.keyDown(trigger(), { key: 'ArrowDown' }); // open -> Apple
    fireEvent.keyDown(trigger(), { key: 'ArrowUp' }); // wrap -> Cherry
    expect(highlighted()).toHaveTextContent('Cherry');
  });

  it('jumps to the first/last item with Home/End', () => {
    render(<Harness />);
    fireEvent.keyDown(trigger(), { key: 'ArrowDown' });
    fireEvent.keyDown(trigger(), { key: 'End' });
    expect(highlighted()).toHaveTextContent('Cherry');
    fireEvent.keyDown(trigger(), { key: 'Home' });
    expect(highlighted()).toHaveTextContent('Apple');
  });

  it('selects the highlighted item on Enter and closes', () => {
    const onValueChange = vi.fn();
    render(<Harness onValueChange={onValueChange} />);
    fireEvent.keyDown(trigger(), { key: 'ArrowDown' }); // open -> Apple
    fireEvent.keyDown(trigger(), { key: 'ArrowDown' }); // Banana
    fireEvent.keyDown(trigger(), { key: 'Enter' });
    expect(onValueChange).toHaveBeenCalledWith('banana');
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('closes on Escape without selecting', () => {
    const onValueChange = vi.fn();
    render(<Harness onValueChange={onValueChange} />);
    fireEvent.keyDown(trigger(), { key: 'ArrowDown' });
    fireEvent.keyDown(trigger(), { key: 'Escape' });
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    expect(onValueChange).not.toHaveBeenCalled();
  });

  it('jumps to a matching item with type-ahead', () => {
    render(<Harness />);
    fireEvent.keyDown(trigger(), { key: 'ArrowDown' }); // open -> Apple
    fireEvent.keyDown(trigger(), { key: 'c' });
    expect(highlighted()).toHaveTextContent('Cherry');
  });

  it('exposes the highlighted option via aria-activedescendant', () => {
    render(<Harness />);
    fireEvent.keyDown(trigger(), { key: 'ArrowDown' });
    const active = trigger().getAttribute('aria-activedescendant');
    expect(active).toBeTruthy();
    expect(highlighted()).toHaveAttribute('id', active);
  });

  it('syncs the highlight with mouse hover', () => {
    render(<Harness />);
    fireEvent.keyDown(trigger(), { key: 'ArrowDown' }); // open -> Apple
    fireEvent.mouseEnter(screen.getByText('Cherry'));
    expect(highlighted()).toHaveTextContent('Cherry');
  });
});
