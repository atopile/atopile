/**
 * Hook to handle package_modified events and show toast notifications.
 *
 * Installed packages cannot be modified directly - if users need to customize
 * a package, they should copy it into their local project instead.
 */

import { useEffect } from 'react';
import { toast } from 'sonner';
import { sendAction } from '../api/websocket';

interface PackageModifiedDetail {
  identifier: string;
  modifiedFiles: string[];
  packagePath: string | null;
  projectRoot: string;
  message: string;
}

export function usePackageModifiedHandler() {
  useEffect(() => {
    function handlePackageModified(event: CustomEvent<PackageModifiedDetail>) {
      const { identifier, projectRoot } = event.detail;

      toast.error(`Package '${identifier}' was modified`, {
        description:
          'Installed packages cannot be modified. Click to reinstall the package.',
        duration: Infinity, // Keep it visible until user takes action
        action: {
          label: 'Reinstall Package',
          onClick: () => {
            // Trigger force sync to reinstall the package fresh
            sendAction('syncPackages', { projectRoot, force: true, identifier });
            toast.info(`Reinstalling ${identifier}...`, { duration: 3000 });
          },
        },
      });
    }

    window.addEventListener(
      'atopile:package_modified',
      handlePackageModified as EventListener
    );

    return () => {
      window.removeEventListener(
        'atopile:package_modified',
        handlePackageModified as EventListener
      );
    };
  }, []);
}
