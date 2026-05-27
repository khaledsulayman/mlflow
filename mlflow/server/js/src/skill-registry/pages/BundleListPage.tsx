import { useEffect, useState } from 'react';
import { ScrollablePageWrapper } from '@mlflow/mlflow/src/common/components/ScrollablePageWrapper';
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
import { Link, Outlet, useLocation } from '../../common/utils/RoutingUtils';
import { withErrorBoundary } from '../../common/utils/withErrorBoundary';
import ErrorUtils from '../../common/utils/ErrorUtils';
import { SkillRegistryApi } from '../api';
import SkillRegistryRoutes from '../routes';
import type { SkillBundle } from '../types';

const BundlesTable = ({ bundles }: { bundles: SkillBundle[] }) => {
  const { theme } = useDesignSystemTheme();

  if (bundles.length === 0) {
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
              defaultMessage="No bundles created yet. Use the CLI to create a bundle."
              description="Empty state for skill bundle list"
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
            <FormattedMessage defaultMessage="Name" description="Bundle table column: name" />
          </th>
          <th css={{ padding: theme.spacing.sm }}>
            <FormattedMessage defaultMessage="Description" description="Bundle table column: description" />
          </th>
          <th css={{ padding: theme.spacing.sm }}>
            <FormattedMessage defaultMessage="Items" description="Bundle table column: item count" />
          </th>
        </tr>
      </thead>
      <tbody>
        {bundles.map((bundle) => (
          <tr
            key={bundle.name}
            css={{
              borderBottom: `1px solid ${theme.colors.borderDecorative}`,
              '&:hover': { backgroundColor: theme.colors.backgroundSecondary },
            }}
          >
            <td css={{ padding: theme.spacing.sm }}>
              <Link
                componentId="mlflow.skill-registry.bundles.bundle_link"
                to={SkillRegistryRoutes.getBundleDetailRoute(bundle.name)}
              >
                {bundle.name}
              </Link>
            </td>
            <td css={{ padding: theme.spacing.sm, color: theme.colors.textSecondary }}>{bundle.description || '-'}</td>
            <td css={{ padding: theme.spacing.sm }}>{bundle.items.length}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

const BundleListPage = () => {
  const { theme } = useDesignSystemTheme();
  const location = useLocation();
  const [bundles, setBundles] = useState<SkillBundle[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const isIndexRoute =
    location.pathname === '/skill-registry/bundles' || location.pathname === '/skill-registry/bundles/';
  const isNestedRoute = !isIndexRoute;

  useEffect(() => {
    if (!isIndexRoute) return;
    let cancelled = false;
    const fetchBundles = () => {
      SkillRegistryApi.searchSkillBundles()
        .then((response) => {
          if (!cancelled) {
            setBundles(response.skill_bundles);
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
    fetchBundles();
    const interval = setInterval(fetchBundles, 5000);
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
          <FormattedMessage defaultMessage="Loading..." description="Loading message for bundles" />
        </div>
      </ScrollablePageWrapper>
    );
  }

  if (error) {
    return (
      <ScrollablePageWrapper css={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div css={{ padding: theme.spacing.md, color: theme.colors.textValidationDanger }}>
          <FormattedMessage
            defaultMessage="Failed to load bundles: {message}"
            description="Error message for bundle list"
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
              <Breadcrumb.Item>
                <FormattedMessage defaultMessage="Bundles" description="Breadcrumb for bundles" />
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
                <FormattedMessage defaultMessage="Bundles" description="Bundles list page title" />
              </Typography.Title>
            </div>
            <div css={{ display: 'flex', gap: theme.spacing.md, marginTop: theme.spacing.xs }}>
              <Link componentId="mlflow.skill-registry.nav.skills" to={SkillRegistryRoutes.skillListPageRoute}>
                <Typography.Text>
                  <FormattedMessage defaultMessage="Skills" description="Nav link to skills list" />
                </Typography.Text>
              </Link>
              <Typography.Text bold>
                <FormattedMessage defaultMessage="Bundles" description="Nav link to bundles list (active)" />
              </Typography.Text>
            </div>
          </div>
        </div>
        <div css={{ flex: 1, overflow: 'auto', padding: theme.spacing.md }}>
          <BundlesTable bundles={bundles} />
        </div>
      </div>
    </ScrollablePageWrapper>
  );
};

export default withErrorBoundary(ErrorUtils.mlflowServices.EXPERIMENTS, BundleListPage);
