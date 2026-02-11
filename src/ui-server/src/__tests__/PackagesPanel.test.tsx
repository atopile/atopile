import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PackagesPanel } from '../components/PackagesPanel';
import type { PackageInfo, ProjectDependency } from '../types/build';

const marketplacePackages: PackageInfo[] = [
  {
    identifier: 'atopile/imu',
    name: 'imu',
    publisher: 'atopile',
    summary: 'IMU package',
    installed: false,
    installedIn: [],
    downloads: 10,
  },
];

const projectDependencies: ProjectDependency[] = [
  {
    identifier: 'atopile/resistors',
    version: '0.1.0',
    name: 'resistors',
    publisher: 'atopile',
    summary: 'Resistor helpers',
    status: 'installed_fresh',
  },
];

describe('PackagesPanel', () => {
  it('does not let browse search hide project dependencies', () => {
    render(
      <PackagesPanel
        packages={marketplacePackages}
        installedDependencies={projectDependencies}
        selectedProjectRoot="/test/project"
        onOpenPackageDetail={vi.fn()}
      />
    );

    const searchInput = screen.getByPlaceholderText('Search packages...');
    fireEvent.change(searchInput, { target: { value: 'does-not-match' } });
    expect(screen.getByText('No packages found')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Project/i }));

    expect(screen.getByText('resistors')).toBeInTheDocument();
  });
});
