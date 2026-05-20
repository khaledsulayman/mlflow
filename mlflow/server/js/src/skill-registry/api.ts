import { matchPredefinedError, UnknownError } from '@databricks/web-shared/errors';
import { fetchEndpoint } from '../common/utils/FetchUtils';
import type { SearchSkillsResponse, SearchSkillVersionsResponse, Skill, SkillVersion } from './types';

const defaultErrorHandler = async ({
  reject,
  response,
  err: originalError,
}: {
  reject: (cause: any) => void;
  response: Response;
  err: Error;
}) => {
  const predefinedError = matchPredefinedError(response);
  const error = predefinedError instanceof UnknownError ? originalError : predefinedError;
  if (response) {
    try {
      const messageFromResponse = (await response.json())?.message;
      if (messageFromResponse) {
        error.message = messageFromResponse;
      }
    } catch {
      // Keep original error message if extraction fails
    }
  }
  reject(error);
};

const BASE = 'ajax-api/3.0/mlflow/skills';

export const SkillRegistryApi = {
  searchSkills: () => {
    return fetchEndpoint({
      relativeUrl: `${BASE}/`,
      error: defaultErrorHandler,
    }) as Promise<SearchSkillsResponse>;
  },

  getSkill: (name: string) => {
    return fetchEndpoint({
      relativeUrl: `${BASE}/${encodeURIComponent(name)}`,
      error: defaultErrorHandler,
    }) as Promise<Skill>;
  },

  searchSkillVersions: (name: string) => {
    return fetchEndpoint({
      relativeUrl: `${BASE}/${encodeURIComponent(name)}/versions`,
      error: defaultErrorHandler,
    }) as Promise<SearchSkillVersionsResponse>;
  },

  getSkillVersion: (name: string, version: string) => {
    return fetchEndpoint({
      relativeUrl: `${BASE}/${encodeURIComponent(name)}/versions/${encodeURIComponent(version)}`,
      error: defaultErrorHandler,
    }) as Promise<SkillVersion>;
  },
};
