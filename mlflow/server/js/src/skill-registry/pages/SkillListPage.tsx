import { useEffect, useState } from 'react';
import { ScrollablePageWrapper } from '@mlflow/mlflow/src/common/components/ScrollablePageWrapper';
import {
  Breadcrumb,
  ChainIcon,
  Empty,
  SearchIcon,
  Spinner,
  Tag,
  Typography,
  useDesignSystemTheme,
} from '@databricks/design-system';
import { FormattedMessage } from 'react-intl';
import { Link, Outlet, useLocation } from '../../common/utils/RoutingUtils';
import { withErrorBoundary } from '../../common/utils/withErrorBoundary';
import ErrorUtils from '../../common/utils/ErrorUtils';
import { SkillRegistryApi } from '../api';
import SkillRegistryRoutes from '../routes';
import type { Skill } from '../types';

const StatusTag = ({ status }: { status: string }) => {
  switch (status) {
    case 'active':
      return (
        <Tag componentId="mlflow.skill-registry.status-tag" color="lime">
          {status}
        </Tag>
      );
    case 'deprecated':
      return (
        <Tag componentId="mlflow.skill-registry.status-tag" color="coral">
          {status}
        </Tag>
      );
    case 'deleted':
      return (
        <Tag componentId="mlflow.skill-registry.status-tag" color="brown">
          {status}
        </Tag>
      );
    default:
      return <Tag componentId="mlflow.skill-registry.status-tag">{status}</Tag>;
  }
};

const KindTag = ({ kind }: { kind: string }) => {
  return (
    <Tag componentId="mlflow.skill-registry.kind-tag" color="indigo">
      {kind}
    </Tag>
  );
};

const SkillsTable = ({ skills }: { skills: Skill[] }) => {
  const { theme } = useDesignSystemTheme();

  if (skills.length === 0) {
    return (
      <div
        css={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          minHeight: 400,
          width: '100%',
          '& > div': {
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
          },
        }}
      >
        <Empty
          description={
            <FormattedMessage
              defaultMessage="No skills registered yet. Use the CLI to register a skill."
              description="Empty state for skill registry list"
            />
          }
          image={<SearchIcon />}
        />
      </div>
    );
  }

  return (
    <table css={{ width: '100%', borderCollapse: 'collapse' }}>
      <thead>
        <tr
          css={{
            borderBottom: `1px solid ${theme.colors.borderDecorative}`,
            textAlign: 'left',
          }}
        >
          <th css={{ padding: theme.spacing.sm }}>
            <FormattedMessage defaultMessage="Name" description="Skill table column: name" />
          </th>
          <th css={{ padding: theme.spacing.sm }}>
            <FormattedMessage defaultMessage="Kind" description="Skill table column: kind" />
          </th>
          <th css={{ padding: theme.spacing.sm }}>
            <FormattedMessage defaultMessage="Description" description="Skill table column: description" />
          </th>
          <th css={{ padding: theme.spacing.sm }}>
            <FormattedMessage defaultMessage="Latest Version" description="Skill table column: latest version" />
          </th>
          <th css={{ padding: theme.spacing.sm }}>
            <FormattedMessage defaultMessage="Status" description="Skill table column: status" />
          </th>
        </tr>
      </thead>
      <tbody>
        {skills.map((skill) => (
          <tr
            key={skill.name}
            css={{
              borderBottom: `1px solid ${theme.colors.borderDecorative}`,
              '&:hover': { backgroundColor: theme.colors.backgroundSecondary },
            }}
          >
            <td css={{ padding: theme.spacing.sm }}>
              <Link
                componentId="mlflow.skill-registry.list.skill_link"
                to={SkillRegistryRoutes.getSkillDetailRoute(skill.name)}
              >
                {skill.name}
              </Link>
            </td>
            <td css={{ padding: theme.spacing.sm }}>
              <KindTag kind={skill.kind} />
            </td>
            <td css={{ padding: theme.spacing.sm, color: theme.colors.textSecondary }}>{skill.description || '-'}</td>
            <td css={{ padding: theme.spacing.sm }}>{skill.latest_version || skill.last_registered_version || '-'}</td>
            <td css={{ padding: theme.spacing.sm }}>
              <StatusTag status={skill.status} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

const SkillListPage = () => {
  const { theme } = useDesignSystemTheme();
  const location = useLocation();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const isIndexRoute = location.pathname === '/skill-registry' || location.pathname === '/skill-registry/';
  const isNestedRoute = !isIndexRoute;

  useEffect(() => {
    if (!isIndexRoute) return;
    let cancelled = false;
    const fetchSkills = () => {
      SkillRegistryApi.searchSkills()
        .then((response) => {
          if (!cancelled) {
            setSkills(response.skills);
            setIsLoading(false);
          }
        })
        .catch((err) => {
          if (!cancelled) {
            setError(err);
            setIsLoading(false);
          }
        });
    };
    setIsLoading(true);
    fetchSkills();
    const interval = setInterval(fetchSkills, 5000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [isIndexRoute]);

  if (isNestedRoute) {
    return (
      <ScrollablePageWrapper css={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div css={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <Outlet />
        </div>
      </ScrollablePageWrapper>
    );
  }

  if (isLoading) {
    return (
      <ScrollablePageWrapper css={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div
          css={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: theme.spacing.sm,
          }}
        >
          <Spinner size="small" />
          <FormattedMessage defaultMessage="Loading..." description="Loading message for skill registry" />
        </div>
      </ScrollablePageWrapper>
    );
  }

  if (error) {
    return (
      <ScrollablePageWrapper css={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div css={{ padding: theme.spacing.md, color: theme.colors.textValidationDanger }}>
          <FormattedMessage
            defaultMessage="Failed to load skills: {message}"
            description="Error message for skill registry"
            values={{ message: error.message }}
          />
        </div>
      </ScrollablePageWrapper>
    );
  }

  return (
    <ScrollablePageWrapper css={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      <div css={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div
          css={{
            display: 'flex',
            alignItems: 'center',
            padding: theme.spacing.md,
            borderBottom: `1px solid ${theme.colors.borderDecorative}`,
          }}
        >
          <div css={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.xs }}>
            <Breadcrumb includeTrailingCaret>
              <Breadcrumb.Item>
                <Link componentId="mlflow.skill-registry.breadcrumb_link" to={SkillRegistryRoutes.skillListPageRoute}>
                  <FormattedMessage defaultMessage="Skill Registry" description="Breadcrumb for skill registry" />
                </Link>
              </Breadcrumb.Item>
            </Breadcrumb>
            <div css={{ display: 'flex', gap: theme.spacing.sm, alignItems: 'center' }}>
              <div
                css={{
                  borderRadius: theme.borders.borderRadiusSm,
                  backgroundColor: theme.colors.backgroundSecondary,
                  padding: theme.spacing.sm,
                  display: 'flex',
                }}
              >
                <ChainIcon />
              </div>
              <Typography.Title withoutMargins level={2}>
                <FormattedMessage defaultMessage="Skills" description="Skills list page title" />
              </Typography.Title>
            </div>
            <div css={{ display: 'flex', gap: theme.spacing.md, marginTop: theme.spacing.xs }}>
              <Typography.Text bold>
                <FormattedMessage defaultMessage="Skills" description="Nav link to skills list (active)" />
              </Typography.Text>
              <Link componentId="mlflow.skill-registry.nav.bundles" to={SkillRegistryRoutes.bundleListPageRoute}>
                <Typography.Text>
                  <FormattedMessage defaultMessage="Bundles" description="Nav link to bundles list" />
                </Typography.Text>
              </Link>
            </div>
          </div>
        </div>
        <div css={{ flex: 1, overflow: 'auto', padding: theme.spacing.md }}>
          <SkillsTable skills={skills} />
        </div>
      </div>
    </ScrollablePageWrapper>
  );
};

export default withErrorBoundary(ErrorUtils.mlflowServices.EXPERIMENTS, SkillListPage);
