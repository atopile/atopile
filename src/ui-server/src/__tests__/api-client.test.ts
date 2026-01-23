/**
 * API client tests
 * Tests HTTP API calls and error handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api, APIError } from '../api/client';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('API Client', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('fetchJSON helper', () => {
    it('makes GET requests with correct headers', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ status: 'ok' })),
      });

      await api.health();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/health'),
        expect.objectContaining({
          headers: { 'Content-Type': 'application/json' },
        })
      );
    });

    it('handles empty responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(''),
      });

      const result = await api.builds.cancel('build-123');
      expect(result).toEqual({});
    });

    it('throws APIError on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: () => Promise.resolve({ detail: 'Resource not found' }),
      });

      await expect(api.projects.list()).rejects.toThrow(APIError);
    });

    it('includes detail in APIError', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: () => Promise.resolve({ detail: 'Invalid project root' }),
      });

      try {
        await api.projects.list();
        expect.fail('Should have thrown');
      } catch (error) {
        expect(error).toBeInstanceOf(APIError);
        expect((error as APIError).message).toBe('Invalid project root');
        expect((error as APIError).status).toBe(400);
      }
    });
  });

  describe('projects API', () => {
    it('lists projects', async () => {
      const mockProjects = {
        projects: [
          { root: '/test', name: 'test', targets: [] },
        ],
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify(mockProjects)),
      });

      const result = await api.projects.list();
      expect(result.projects).toHaveLength(1);
      expect(result.projects[0].name).toBe('test');
    });
  });

  describe('builds API', () => {
    it('gets build history', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ builds: [] })),
      });

      const result = await api.builds.history();
      expect(result.builds).toEqual([]);
    });

    it('gets active builds', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ builds: [] })),
      });

      const result = await api.builds.active();
      expect(result.builds).toEqual([]);
    });

    it('gets build queue', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ queue: [] })),
      });

      const result = await api.builds.queue();
      expect(result.queue).toEqual([]);
    });

    it('gets build status', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ status: 'running', stages: [] })),
      });

      const result = await api.builds.status('build-123');
      expect(result.status).toBe('running');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/build/build-123/status'),
        expect.any(Object)
      );
    });

    it('starts build with targets', async () => {
      const mockResponse = {
        success: true,
        message: 'Build started',
        build_targets: [{ target: 'default', build_id: 'build-123' }],
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify(mockResponse)),
      });

      const result = await api.builds.start('/project', ['default', 'debug']);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/build'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            project_root: '/project',
            targets: ['default', 'debug'],
          }),
        })
      );
      expect(result.success).toBe(true);
      expect(result.build_targets).toEqual([{ target: 'default', build_id: 'build-123' }]);
    });

    it('starts standalone build with entry', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ success: true, build_targets: [{ target: 'default', build_id: 'build-456' }] })),
      });

      await api.builds.start('/project', [], { entry: 'main.ato:App', standalone: true });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/build'),
        expect.objectContaining({
          body: JSON.stringify({
            project_root: '/project',
            targets: [],
            entry: 'main.ato:App',
            standalone: true,
          }),
        })
      );
    });

    it('cancels build', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ success: true, message: 'Cancelled' })),
      });

      await api.builds.cancel('build-123');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/build/build-123/cancel'),
        expect.objectContaining({ method: 'POST' })
      );
    });
  });

  describe('packages API', () => {
    it('lists packages', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ packages: [] })),
      });

      const result = await api.packages.list();
      expect(result.packages).toEqual([]);
    });

    it('gets package summary', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ packages: [], total: 0 })),
      });

      const result = await api.packages.summary();
      expect(result.total).toBe(0);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/packages/summary'),
        expect.any(Object)
      );
    });

    it('searches packages using registry endpoint', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ packages: [], total: 0, query: 'bme280' })),
      });

      await api.packages.search('bme280');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/registry/search?q=bme280'),
        expect.any(Object)
      );
    });

    it('gets package details', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ identifier: 'atopile/resistors', name: 'resistors' })),
      });

      await api.packages.details('atopile/resistors');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/packages/atopile%2Fresistors/details'),
        expect.any(Object)
      );
    });

    it('installs package', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ success: true, message: 'Installed' })),
      });

      await api.packages.install('atopile/resistors', '/project', '1.0.0');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/packages/install'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            package_identifier: 'atopile/resistors',
            project_root: '/project',
            version: '1.0.0',
          }),
        })
      );
    });

    it('removes package', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ success: true, message: 'Removed' })),
      });

      await api.packages.remove('atopile/resistors', '/project');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/packages/remove'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            package_identifier: 'atopile/resistors',
            project_root: '/project',
          }),
        })
      );
    });
  });

  describe('problems API', () => {
    it('lists problems', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ problems: [] })),
      });

      const result = await api.problems.list();
      expect(result.problems).toEqual([]);
    });

    it('lists problems with filters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ problems: [] })),
      });

      await api.problems.list({ projectRoot: '/project', buildName: 'default', level: 'error' });
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringMatching(/project_root=.*build_name=default.*level=error/),
        expect.any(Object)
      );
    });
  });

  describe('stdlib API', () => {
    it('lists stdlib items', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ items: [] })),
      });

      const result = await api.stdlib.list();
      expect(result.items).toEqual([]);
    });
  });

  describe('bom API', () => {
    it('gets BOM data', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ items: [] })),
      });

      await api.bom.get('/project', 'default');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('project_root=%2Fproject'),
        expect.any(Object)
      );
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('target=default'),
        expect.any(Object)
      );
    });

    it('gets BOM targets', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ targets: ['default', 'debug'] })),
      });

      const result = await api.bom.targets('/project');
      expect(result.targets).toEqual(['default', 'debug']);
    });
  });

  describe('variables API', () => {
    it('gets variables data', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ variables: [] })),
      });

      await api.variables.get('/project', 'default');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('project_root=%2Fproject'),
        expect.any(Object)
      );
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('target=default'),
        expect.any(Object)
      );
    });

    it('gets variables targets', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ targets: ['default'] })),
      });

      const result = await api.variables.targets('/project');
      expect(result.targets).toEqual(['default']);
    });
  });

  describe('files API', () => {
    it('lists project files', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ files: [] })),
      });

      await api.files.list('/project');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('project_root=%2Fproject'),
        expect.any(Object)
      );
    });
  });

  describe('modules API', () => {
    it('lists project modules', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ modules: [] })),
      });

      await api.modules.list('/project');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('project_root=%2Fproject'),
        expect.any(Object)
      );
    });
  });

  describe('dependencies API', () => {
    it('lists project dependencies', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ dependencies: [] })),
      });

      await api.dependencies.list('/project');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('project_root=%2Fproject'),
        expect.any(Object)
      );
    });
  });
});
