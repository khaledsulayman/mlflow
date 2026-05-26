import { useEffect, useState } from 'react';
import {
  Breadcrumb,
  ChainIcon,
  Empty,
  SearchIcon,
  Spinner,
  Typography,
  useDesignSystemTheme,
} from '@databricks/design-system';
import { FormattedMessage } from 'react-intl';
import { Link, useParams } from '../../common/utils/RoutingUtils';
import { withErrorBoundary } from '../../common/utils/withErrorBoundary';
import ErrorUtils from '../../common/utils/ErrorUtils';
import { SkillRegistryApi } from '../api';
import SkillRegistryRoutes from '../routes';
import type { SkillBundle, SkillBundleItem } from '../types';

const BundleItemsTable = ({ items }: { items: SkillBundleItem[] }) => {
  const { theme } = useDesignSystemTheme();

  if (items.length === 0) {
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
            <FormattedMessage
              defaultMessage="No skills in this bundle. Use the CLI to add skills."
              description="Empty state for bundle items"
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
            <FormattedMessage defaultMessage="Skill" description="Bundle items column: skill name" />
          </th>
          <th css={{ padding: theme.spacing.sm }}>
            <FormattedMessage defaultMessage="Version" description="Bundle items column: version" />
          </th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr
            key={item.skill_name}
            css={{
              borderBottom: `1px solid ${theme.colors.borderDecorative}`,
              '&:hover': { backgroundColor: theme.colors.backgroundSecondary },
            }}
          >
            <td css={{ padding: theme.spacing.sm }}>
              <Link
                componentId="mlflow.skill-registry.bundles.skill_link"
                to={SkillRegistryRoutes.getSkillDetailRoute(item.skill_name)}
              >
                {item.skill_name}
              </Link>
            </td>
            <td css={{ padding: theme.spacing.sm }}>{item.version}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

const BundleDetailPage = () => {
  const { theme } = useDesignSystemTheme();
  const { bundleName } = useParams<{ bundleName: string }>();
  const [bundle, setBundle] = useState<SkillBundle | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!bundleName) return;
    let cancelled = false;
    setIsLoading(true);
    SkillRegistryApi.getSkillBundle(bundleName)
      .then((data) => {
        if (!cancelled) {
          setBundle(data);
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
  }, [bundleName]);

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
        <FormattedMessage defaultMessage="Loading..." description="Loading message for bundle detail" />
      </div>
    );
  }

  if (error || !bundle) {
    return (
      <div css={{ padding: theme.spacing.md, color: theme.colors.textValidationDanger }}>
        <FormattedMessage
          defaultMessage="Failed to load bundle: {message}"
          description="Error message for bundle detail"
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
                componentId="mlflow.skill-registry.bundles.breadcrumb_registry_link"
                to={SkillRegistryRoutes.skillListPageRoute}
              >
                <FormattedMessage defaultMessage="Skill Registry" description="Breadcrumb back to skill list" />
              </Link>
            </Breadcrumb.Item>
            <Breadcrumb.Item>
              <Link
                componentId="mlflow.skill-registry.bundles.breadcrumb_bundles_link"
                to={SkillRegistryRoutes.bundleListPageRoute}
              >
                <FormattedMessage defaultMessage="Bundles" description="Breadcrumb back to bundles" />
              </Link>
            </Breadcrumb.Item>
            <Breadcrumb.Item>{bundle.name}</Breadcrumb.Item>
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
              {bundle.name}
            </Typography.Title>
          </div>
        </div>
      </div>

      <div css={{ flex: 1, overflow: 'auto', padding: theme.spacing.md }}>
        {bundle.description && (
          <div css={{ marginBottom: theme.spacing.lg }}>
            <Typography.Text color="secondary">{bundle.description}</Typography.Text>
          </div>
        )}

        <Typography.Title level={4}>
          <FormattedMessage defaultMessage="Skills in Bundle" description="Items section header on bundle detail" />
        </Typography.Title>
        <BundleItemsTable items={bundle.items} />
      </div>
    </div>
  );
};

export default withErrorBoundary(ErrorUtils.mlflowServices.EXPERIMENTS, BundleDetailPage);
