import json

import click

import mlflow.genai.skills as skills_api


@click.group(
    "skills",
    help="Skill Registry: register, discover, and manage AI agent capabilities.",
)
def commands():
    pass


@commands.command(
    help="Register a skill version. Creates the parent skill if it doesn't exist."
)
@click.option("--name", required=True, help="Skill name")
@click.option("--version", required=True, help="Version string (e.g. 1.0.0)")
@click.option("--kind", default="skill", help="Capability kind: skill, agent, hook")
@click.option("--description", default=None, help="Skill description")
@click.option("--source-type", default=None, help="Source type: git, oci, zip, mlflow")
@click.option("--source", default=None, help="Source pointer (URL, image ref, etc.)")
@click.option("--subpath", default=None, help="Path within artifact")
@click.option("--content-digest", default=None, help="Content integrity digest")
def register(name, version, kind, description, source_type, source, subpath, content_digest):
    sv = skills_api.register_skill(
        name=name,
        version=version,
        kind=kind,
        description=description,
        source_type=source_type,
        source=source,
        subpath=subpath,
        content_digest=content_digest,
    )
    click.echo(f"Registered skill '{sv.name}' version '{sv.version}' (status: {sv.status})")


@commands.command(help="Get a skill by name.")
@click.option("--name", required=True, help="Skill name")
def get(name):
    skill = skills_api.get_skill(name)
    click.echo(json.dumps(_skill_to_dict(skill), indent=2))


@commands.command(help="Search for skills.")
@click.option("--filter", "filter_string", default=None, help="Filter expression")
@click.option("--max-results", default=100, help="Maximum results to return")
def search(filter_string, max_results):
    results = skills_api.search_skills(filter_string=filter_string, max_results=max_results)
    for skill in results:
        click.echo(f"  {skill.name} (kind={skill.kind}, status={skill.status})")


@commands.command("search-versions", help="Search skill versions.")
@click.option("--name", required=True, help="Skill name")
@click.option("--filter", "filter_string", default=None, help="Filter expression")
@click.option("--max-results", default=100, help="Maximum results to return")
def search_versions(name, filter_string, max_results):
    results = skills_api.search_skill_versions(
        name=name, filter_string=filter_string, max_results=max_results
    )
    for v in results:
        click.echo(f"  {v.name} v{v.version} (status={v.status}, source_type={v.source_type})")


@commands.command("update-version", help="Update a skill version (e.g. status transition).")
@click.option("--name", required=True, help="Skill name")
@click.option("--version", required=True, help="Version string")
@click.option("--status", required=True, help="New status: active, deprecated, draft, deleted")
def update_version(name, version, status):
    sv = skills_api.update_skill_version(name=name, version=version, status=status)
    click.echo(f"Updated skill '{sv.name}' v{sv.version} -> status={sv.status}")


@commands.command(help="Pull skill content from a registered source to a local directory.")
@click.option("--name", required=True, help="Skill name")
@click.option("--version", default=None, help="Version string (omit to use latest or alias)")
@click.option("--alias", default=None, help="Resolve alias to version (e.g. production)")
@click.option("--destination", default=".", help="Local directory to pull into")
def pull(name, version, alias, destination):
    dest = skills_api.pull(name=name, version=version, alias=alias, destination=destination)
    click.echo(f"Pulled skill '{name}' to {dest}")


@commands.command(help="Delete a skill and all its versions.")
@click.option("--name", required=True, help="Skill name")
def delete(name):
    skills_api.delete_skill(name)
    click.echo(f"Deleted skill '{name}'")


@commands.command("set-tag", help="Set a skill-level tag.")
@click.option("--name", required=True, help="Skill name")
@click.option("--key", required=True, help="Tag key")
@click.option("--value", required=True, help="Tag value")
def set_tag(name, key, value):
    skills_api.set_skill_tag(name, key, value)
    click.echo(f"Set tag '{key}' on skill '{name}'")


@commands.command("set-version-tag", help="Set a version-level tag.")
@click.option("--name", required=True, help="Skill name")
@click.option("--version", required=True, help="Version string")
@click.option("--key", required=True, help="Tag key")
@click.option("--value", required=True, help="Tag value")
def set_version_tag(name, version, key, value):
    skills_api.set_skill_version_tag(name, version, key, value)
    click.echo(f"Set tag '{key}' on skill '{name}' v{version}")


@commands.command("delete-tag", help="Delete a skill-level tag.")
@click.option("--name", required=True, help="Skill name")
@click.option("--key", required=True, help="Tag key")
def delete_tag(name, key):
    skills_api.delete_skill_tag(name, key)
    click.echo(f"Deleted tag '{key}' from skill '{name}'")


@commands.command("delete-version-tag", help="Delete a version-level tag.")
@click.option("--name", required=True, help="Skill name")
@click.option("--version", required=True, help="Version string")
@click.option("--key", required=True, help="Tag key")
def delete_version_tag(name, version, key):
    skills_api.delete_skill_version_tag(name, version, key)
    click.echo(f"Deleted tag '{key}' from skill '{name}' v{version}")


@commands.command("delete-alias", help="Delete a skill alias.")
@click.option("--name", required=True, help="Skill name")
@click.option("--alias", required=True, help="Alias name")
def delete_alias(name, alias):
    skills_api.delete_skill_alias(name, alias)
    click.echo(f"Deleted alias '{alias}' from skill '{name}'")


@commands.command("set-alias", help="Set an alias on a skill version.")
@click.option("--name", required=True, help="Skill name")
@click.option("--alias", required=True, help="Alias name (e.g. production)")
@click.option("--version", required=True, help="Version to point alias at")
def set_alias(name, alias, version):
    skills_api.set_skill_alias(name, alias, version)
    click.echo(f"Set alias '{alias}' -> v{version} on skill '{name}'")


@commands.command("get-alias", help="Resolve an alias to a skill version.")
@click.option("--name", required=True, help="Skill name")
@click.option("--alias", required=True, help="Alias name")
def get_alias(name, alias):
    sv = skills_api.get_skill_version_by_alias(name, alias)
    click.echo(json.dumps(_version_to_dict(sv), indent=2))


def _skill_to_dict(skill):
    return {
        "name": skill.name,
        "kind": skill.kind,
        "description": skill.description,
        "status": str(skill.status),
        "last_registered_version": skill.last_registered_version,
        "latest_version": skill.latest_version,
        "tags": skill.tags,
        "aliases": [{"alias": a.alias, "version": a.version} for a in skill.aliases],
    }


def _version_to_dict(v):
    return {
        "name": v.name,
        "version": v.version,
        "status": str(v.status),
        "source_type": v.source_type,
        "source": v.source,
        "subpath": v.subpath,
        "content_digest": v.content_digest,
        "aliases": v.aliases,
        "tags": v.tags,
    }
