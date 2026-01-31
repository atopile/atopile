/**
 * Hook for package-related state and actions.
 */

import { useCallback, useState } from 'react';
import { useStore } from '../store';
import { sendAction, sendActionWithResponse } from '../api/websocket';

export function usePackages() {
  const packages = useStore((state) => state.packages);
  const isLoadingPackages = useStore((state) => state.isLoadingPackages);
  const packagesError = useStore((state) => state.packagesError);
  const selectedPackageDetails = useStore(
    (state) => state.selectedPackageDetails
  );
  const isLoadingPackageDetails = useStore(
    (state) => state.isLoadingPackageDetails
  );

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<typeof packages>([]);
  const [isSearching, setIsSearching] = useState(false);

  const refresh = useCallback(async () => {
    sendAction('refreshPackages');
  }, []);

  const search = useCallback(async (query: string) => {
    setSearchQuery(query);
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }

    setIsSearching(true);
    try {
      const response = await sendActionWithResponse('searchPackages', { query });
      const result = response.result ?? {};
      const searchPackages = Array.isArray((result as { packages?: unknown }).packages)
        ? (result as { packages: unknown[] }).packages
        : [];
      setSearchResults(searchPackages as typeof packages);
    } catch (error) {
      console.error('Failed to search packages:', error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  const fetchDetails = useCallback(async (identifier: string, version?: string) => {
    const response = await sendActionWithResponse('getPackageDetails', {
      packageId: identifier,
      version,
    });
    const result = response.result ?? {};
    return (result as { details?: unknown }).details as unknown;
  }, []);

  const install = useCallback(
    async (identifier: string, projectRoot: string, version?: string) => {
      sendAction('installPackage', { packageId: identifier, projectRoot, version });
    },
    []
  );

  const uninstall = useCallback(
    async (identifier: string, projectRoot: string) => {
      sendAction('removePackage', { packageId: identifier, projectRoot });
    },
    []
  );

  const update = useCallback(
    async (identifier: string, projectRoot: string, version?: string) => {
      sendAction('installPackage', { packageId: identifier, projectRoot, version });
    },
    []
  );

  const clearDetails = useCallback(() => {
    useStore.getState().setPackageDetails(null);
  }, []);

  // Filter packages by installation status
  const installedPackages = packages.filter((p) => p.installed);
  const availablePackages = packages.filter((p) => !p.installed);
  const packagesWithUpdates = packages.filter((p) => p.hasUpdate);

  return {
    packages,
    installedPackages,
    availablePackages,
    packagesWithUpdates,
    isLoadingPackages,
    packagesError,
    selectedPackageDetails,
    isLoadingPackageDetails,
    searchQuery,
    searchResults,
    isSearching,
    refresh,
    search,
    setSearchQuery,
    fetchDetails,
    clearDetails,
    install,
    uninstall,
    update,
  };
}
