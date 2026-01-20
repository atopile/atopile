/**
 * Hook for package-related state and actions.
 */

import { useCallback, useState } from 'react';
import { useStore } from '../store';
import { api } from '../api/client';

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
    useStore.getState().setLoadingPackages(true);
    try {
      const response = await api.packages.list();
      useStore.getState().setPackages(response.packages);
    } catch (error) {
      console.error('Failed to refresh packages:', error);
      useStore
        .getState()
        .setPackagesError(
          error instanceof Error ? error.message : 'Failed to load packages'
        );
    }
  }, []);

  const search = useCallback(async (query: string) => {
    setSearchQuery(query);
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }

    setIsSearching(true);
    try {
      const response = await api.packages.search(query);
      setSearchResults(response.packages);
    } catch (error) {
      console.error('Failed to search packages:', error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  const fetchDetails = useCallback(async (identifier: string) => {
    useStore.getState().setLoadingPackageDetails(true);
    try {
      const details = await api.packages.details(identifier);
      useStore.getState().setPackageDetails(details);
      return details;
    } catch (error) {
      console.error('Failed to fetch package details:', error);
      useStore.getState().setPackageDetails(null);
      throw error;
    }
  }, []);

  const install = useCallback(
    async (identifier: string, projectRoot: string, version?: string) => {
      try {
        await api.packages.install(identifier, projectRoot, version);
        // Backend will broadcast state update via WebSocket
      } catch (error) {
        console.error('Failed to install package:', error);
        throw error;
      }
    },
    []
  );

  const uninstall = useCallback(
    async (identifier: string, projectRoot: string) => {
      try {
        await api.packages.uninstall(identifier, projectRoot);
        // Backend will broadcast state update via WebSocket
      } catch (error) {
        console.error('Failed to uninstall package:', error);
        throw error;
      }
    },
    []
  );

  const update = useCallback(
    async (identifier: string, projectRoot: string, version?: string) => {
      try {
        await api.packages.update(identifier, projectRoot, version);
        // Backend will broadcast state update via WebSocket
      } catch (error) {
        console.error('Failed to update package:', error);
        throw error;
      }
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
