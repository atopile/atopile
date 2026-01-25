/**
 * Hook for package-related state and actions.
 */

import { useCallback, useState } from 'react';
import { useStore } from '../store';
import { api } from '../api/client';
import { sendActionWithResponse } from '../api/websocket';

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
    const store = useStore.getState();
    store.setLoadingPackages(true);
    store.setPackagesError(null);
    try {
      const result = await api.packages.summary();
      store.setPackages(result.packages);
    } catch (error) {
      store.setPackagesError(error instanceof Error ? error.message : String(error));
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
      const result = await api.packages.search(query);
      setSearchResults(result.packages as typeof packages);
    } catch (error) {
      console.error('Failed to search packages:', error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  const fetchDetails = useCallback(async (identifier: string) => {
    return api.packages.details(identifier);
  }, []);

  const install = useCallback(
    async (identifier: string, projectRoot: string, version?: string) => {
      const store = useStore.getState();
      store.addInstallingPackage(identifier);
      try {
        const response = await sendActionWithResponse('installPackage', {
          packageId: identifier,
          projectRoot,
          version,
        });
        if (!response.result?.success) {
          store.setInstallError(identifier, String(response.result?.error || 'Install failed'));
        }
      } catch (error) {
        store.setInstallError(
          identifier,
          error instanceof Error ? error.message : String(error)
        );
      }
    },
    []
  );

  const uninstall = useCallback(
    async (identifier: string, projectRoot: string) => {
      const store = useStore.getState();
      store.addInstallingPackage(identifier);
      try {
        const response = await sendActionWithResponse('removePackage', {
          packageId: identifier,
          projectRoot,
        });
        if (!response.result?.success) {
          store.setInstallError(identifier, String(response.result?.error || 'Remove failed'));
        }
      } catch (error) {
        store.setInstallError(
          identifier,
          error instanceof Error ? error.message : String(error)
        );
      }
    },
    []
  );

  const update = useCallback(
    async (identifier: string, projectRoot: string, version?: string) => {
      const store = useStore.getState();
      store.addInstallingPackage(identifier);
      try {
        const response = await sendActionWithResponse('installPackage', {
          packageId: identifier,
          projectRoot,
          version,
        });
        if (!response.result?.success) {
          store.setInstallError(identifier, String(response.result?.error || 'Update failed'));
        }
      } catch (error) {
        store.setInstallError(
          identifier,
          error instanceof Error ? error.message : String(error)
        );
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
