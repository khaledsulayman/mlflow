import { useEffect, useState } from 'react';
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
import { Link, useParams } from '../../common/utils/RoutingUtils';
import { withErrorBoundary } from '../../common/utils/withErrorBoundary';
import ErrorUtils from '../../common/utils/ErrorUtils';
import { SkillRegistryApi } from '../api';
import SkillRegistryRoutes from '../routes';
import type { Skill, SkillVersion } from '../types';

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

const VersionsTable = ({ versions }: { versions: SkillVersion[] }) => {
  const { theme } = useDesignSystemTheme();

  if (versions.length === 0) {
    return (
      <div
        css={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          minHeight: 300,
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
            <FormattedMessage defaultMessage="No versions found." description="Empty state for skill versions table" />
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
            <FormattedMessage defaultMessage="Version" description="Version table column: version" />
          </th>
          <th css={{ padding: theme.spacing.sm }}>
            <FormattedMessage defaultMessage="Status" description="Version table column: status" />
          </th>
          <th css={{ padding: theme.spacing.sm }}>
            <FormattedMessage defaultMessage="Source Type" description="Version table column: source type" />
          </th>
          <th css={{ padding: theme.spacing.sm }}>
            <FormattedMessage defaultMessage="Source" description="Version table column: source" />
          </th>
          <th css={{ padding: theme.spacing.sm }}>
            <FormattedMessage defaultMessage="Aliases" description="Version table column: aliases" />
          </th>
        </tr>
      </thead>
      <tbody>
        {versions.map((version) => (
          <tr
            key={version.version}
            css={{
              borderBottom: `1px solid ${theme.colors.borderDecorative}`,
              '&:hover': { backgroundColor: theme.colors.backgroundSecondary },
            }}
          >
            <td css={{ padding: theme.spacing.sm }}>{version.version}</td>
            <td css={{ padding: theme.spacing.sm }}>
              <StatusTag status={version.status} />
            </td>
            <td css={{ padding: theme.spacing.sm }}>{version.source_type || '-'}</td>
            <td
              css={{
                padding: theme.spacing.sm,
                color: theme.colors.textSecondary,
                maxWidth: 300,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {version.source || '-'}
            </td>
            <td css={{ padding: theme.spacing.sm }}>
              {version.aliases.length > 0
                ? version.aliases.map((alias) => (
                    <Tag
                      key={alias}
                      componentId="mlflow.skill-registry.alias-tag"
                      color="purple"
                      css={{ marginRight: theme.spacing.xs }}
                    >
                      {alias}
                    </Tag>
                  ))
                : '-'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

const SkillDetailPage = () => {
  const { theme } = useDesignSystemTheme();
  const { skillName } = useParams<{ skillName: string }>();
  const [skill, setSkill] = useState<Skill | null>(null);
  const [versions, setVersions] = useState<SkillVersion[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!skillName) return;
    let cancelled = false;
    setIsLoading(true);
    Promise.all([SkillRegistryApi.getSkill(skillName), SkillRegistryApi.searchSkillVersions(skillName)])
      .then(([skillData, versionsData]) => {
        if (!cancelled) {
          setSkill(skillData);
          setVersions(versionsData.skill_versions);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err);
          setIsLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [skillName]);

  if (isLoading) {
    return (
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
        <FormattedMessage defaultMessage="Loading..." description="Loading message for skill detail page" />
      </div>
    );
  }

  if (error || !skill) {
    return (
      <div css={{ padding: theme.spacing.md, color: theme.colors.textValidationDanger }}>
        <FormattedMessage
          defaultMessage="Failed to load skill: {message}"
          description="Error message for skill detail page"
          values={{ message: error?.message ?? 'Not found' }}
        />
      </div>
    );
  }

  return (
    <div css={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
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
              <Link
                componentId="mlflow.skill-registry.detail.breadcrumb_list_link"
                to={SkillRegistryRoutes.skillListPageRoute}
              >
                <FormattedMessage defaultMessage="Skill Registry" description="Breadcrumb back to skill list" />
              </Link>
            </Breadcrumb.Item>
            <Breadcrumb.Item>{skill.name}</Breadcrumb.Item>
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
              {skill.name}
            </Typography.Title>
            <StatusTag status={skill.status} />
            <Tag componentId="mlflow.skill-registry.kind-tag" color="indigo">
              {skill.kind}
            </Tag>
          </div>
        </div>
      </div>

      <div css={{ flex: 1, overflow: 'auto', padding: theme.spacing.md }}>
        {skill.description && (
          <div css={{ marginBottom: theme.spacing.lg }}>
            <Typography.Text color="secondary">{skill.description}</Typography.Text>
          </div>
        )}

        {Object.keys(skill.tags).length > 0 && (
          <div css={{ marginBottom: theme.spacing.lg }}>
            <Typography.Title level={4}>
              <FormattedMessage defaultMessage="Tags" description="Tags section header on skill detail page" />
            </Typography.Title>
            <div css={{ display: 'flex', gap: theme.spacing.xs, flexWrap: 'wrap' }}>
              {Object.entries(skill.tags).map(([key, value]) => (
                <Tag key={key} componentId="mlflow.skill-registry.tag">
                  {key}: {value}
                </Tag>
              ))}
            </div>
          </div>
        )}

        <Typography.Title level={4}>
          <FormattedMessage defaultMessage="Versions" description="Versions section header on skill detail page" />
        </Typography.Title>
        <VersionsTable versions={versions} />
      </div>
    </div>
  );
};

export default withErrorBoundary(ErrorUtils.mlflowServices.EXPERIMENTS, SkillDetailPage);
