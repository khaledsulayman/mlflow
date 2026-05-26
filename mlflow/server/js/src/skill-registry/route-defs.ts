import type { DocumentTitleHandle } from '../common/utils/RoutingUtils';
import { createLazyRouteElement } from '../common/utils/RoutingUtils';
import { SkillRegistryPageId, SkillRegistryRoutePaths } from './routes';

export const getSkillRegistryRouteDefs = () => {
  return [
    {
      path: SkillRegistryRoutePaths.skillListPage,
      element: createLazyRouteElement(() => import('./pages/SkillListPage')),
      pageId: SkillRegistryPageId.skillListPage,
      handle: { getPageTitle: () => 'Skill Registry' } satisfies DocumentTitleHandle,
      children: [
        {
          path: 'bundles',
          element: createLazyRouteElement(() => import('./pages/BundleListPage')),
          pageId: SkillRegistryPageId.bundleListPage,
          handle: { getPageTitle: () => 'Skill Bundles' } satisfies DocumentTitleHandle,
          children: [
            {
              path: ':bundleName',
              element: createLazyRouteElement(() => import('./pages/BundleDetailPage')),
              pageId: SkillRegistryPageId.bundleDetailPage,
              handle: {
                getPageTitle: (params) => `Bundle ${params['bundleName']}`,
              } satisfies DocumentTitleHandle,
            },
          ],
        },
        {
          path: ':skillName',
          element: createLazyRouteElement(() => import('./pages/SkillDetailPage')),
          pageId: SkillRegistryPageId.skillDetailPage,
          handle: { getPageTitle: (params) => `Skill ${params['skillName']}` } satisfies DocumentTitleHandle,
        },
      ],
    },
  ];
};
