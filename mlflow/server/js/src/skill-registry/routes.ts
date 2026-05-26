import { createMLflowRoutePath, generatePath } from '../common/utils/RoutingUtils';

export enum SkillRegistryPageId {
  skillListPage = 'mlflow.skill-registry',
  skillDetailPage = 'mlflow.skill-registry.detail',
  bundleListPage = 'mlflow.skill-registry.bundles',
  bundleDetailPage = 'mlflow.skill-registry.bundles.detail',
}

// eslint-disable-next-line @typescript-eslint/no-extraneous-class -- TODO(FEINF-4274)
export class SkillRegistryRoutePaths {
  static get skillListPage() {
    return createMLflowRoutePath('/skill-registry');
  }

  static get skillDetailPage() {
    return createMLflowRoutePath('/skill-registry/:skillName');
  }

  static get bundleListPage() {
    return createMLflowRoutePath('/skill-registry/bundles');
  }

  static get bundleDetailPage() {
    return createMLflowRoutePath('/skill-registry/bundles/:bundleName');
  }
}

// eslint-disable-next-line @typescript-eslint/no-extraneous-class -- TODO(FEINF-4274)
class SkillRegistryRoutes {
  static get skillListPageRoute() {
    return SkillRegistryRoutePaths.skillListPage;
  }

  static getSkillDetailRoute(skillName: string) {
    return generatePath(SkillRegistryRoutePaths.skillDetailPage, { skillName });
  }

  static get bundleListPageRoute() {
    return SkillRegistryRoutePaths.bundleListPage;
  }

  static getBundleDetailRoute(bundleName: string) {
    return generatePath(SkillRegistryRoutePaths.bundleDetailPage, { bundleName });
  }
}

export default SkillRegistryRoutes;
