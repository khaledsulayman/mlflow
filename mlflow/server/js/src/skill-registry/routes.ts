import { createMLflowRoutePath, generatePath } from '../common/utils/RoutingUtils';

export enum SkillRegistryPageId {
  skillListPage = 'mlflow.skill-registry',
  skillDetailPage = 'mlflow.skill-registry.detail',
}

// eslint-disable-next-line @typescript-eslint/no-extraneous-class -- TODO(FEINF-4274)
export class SkillRegistryRoutePaths {
  static get skillListPage() {
    return createMLflowRoutePath('/skill-registry');
  }

  static get skillDetailPage() {
    return createMLflowRoutePath('/skill-registry/:skillName');
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
}

export default SkillRegistryRoutes;
