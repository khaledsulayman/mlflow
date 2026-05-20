export interface SkillAlias {
  name: string;
  alias: string;
  version: string;
}

export interface Skill {
  name: string;
  kind: string;
  description: string | null;
  status: string;
  tags: Record<string, string>;
  aliases: SkillAlias[];
  last_registered_version: string | null;
  latest_version: string | null;
  creation_timestamp: number | null;
  last_updated_timestamp: number | null;
}

export interface SkillVersion {
  name: string;
  version: string;
  source_type: string | null;
  source: string | null;
  subpath: string | null;
  status: string;
  content_digest: string | null;
  tags: Record<string, string>;
  aliases: string[];
  run_id: string | null;
  creation_timestamp: number | null;
  last_updated_timestamp: number | null;
}

export interface SearchSkillsResponse {
  skills: Skill[];
}

export interface SearchSkillVersionsResponse {
  skill_versions: SkillVersion[];
}
