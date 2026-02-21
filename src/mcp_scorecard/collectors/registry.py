"""MCP Registry API collector.

Paginates the official MCP registry and returns normalized ServerEntry dicts
filtered to isLatest == True only.
"""

from __future__ import annotations

from typing import Any, TypedDict

import httpx

from mcp_scorecard import config


class EnvVar(TypedDict):
    name: str
    is_required: bool
    is_secret: bool


class ServerEntry(TypedDict):
    name: str
    title: str | None
    description: str
    version: str
    repo_url: str | None
    repo_source: str | None
    has_packages: bool
    package_types: list[str]
    package_identifiers: list[str]
    has_remotes: bool
    transport_types: list[str]
    env_vars: list[EnvVar]
    has_website: bool
    has_icon: bool
    published_at: str
    updated_at: str
    namespace: str
    server_id: str


def _normalize(entry: dict[str, Any]) -> ServerEntry:
    """Flatten a raw registry entry into a ServerEntry dict."""
    server = entry["server"]
    meta_block = entry.get("_meta", {})
    official = meta_block.get("io.modelcontextprotocol.registry/official", {})

    name: str = server.get("name", "")
    parts = name.split("/", 1)
    namespace = parts[0] if len(parts) == 2 else ""
    server_id = parts[1] if len(parts) == 2 else name

    repo = server.get("repository") or {}
    repo_url = repo.get("url") or None
    repo_source = repo.get("source") or None

    packages: list[dict[str, Any]] = server.get("packages") or []
    remotes: list[dict[str, Any]] = server.get("remotes") or []

    package_types: list[str] = []
    package_identifiers: list[str] = []
    transport_types: list[str] = []
    env_vars: list[EnvVar] = []

    for pkg in packages:
        reg_type = pkg.get("registryType")
        if reg_type:
            package_types.append(reg_type)
        identifier = pkg.get("identifier")
        if identifier:
            package_identifiers.append(identifier)
        transport = pkg.get("transport") or {}
        t_type = transport.get("type")
        if t_type and t_type not in transport_types:
            transport_types.append(t_type)
        for ev in pkg.get("environmentVariables") or []:
            env_vars.append(
                EnvVar(
                    name=ev.get("name", ""),
                    is_required=bool(ev.get("isRequired", False)),
                    is_secret=bool(ev.get("isSecret", False)),
                )
            )

    for remote in remotes:
        r_type = remote.get("type")
        if r_type and r_type not in transport_types:
            transport_types.append(r_type)

    return ServerEntry(
        name=name,
        title=server.get("title") or None,
        description=server.get("description", ""),
        version=server.get("version", ""),
        repo_url=repo_url,
        repo_source=repo_source,
        has_packages=len(packages) > 0,
        package_types=package_types,
        package_identifiers=package_identifiers,
        has_remotes=len(remotes) > 0,
        transport_types=transport_types,
        env_vars=env_vars,
        has_website=bool(server.get("websiteUrl")),
        has_icon=bool(server.get("icons")),
        published_at=official.get("publishedAt", ""),
        updated_at=official.get("updatedAt", ""),
        namespace=namespace,
        server_id=server_id,
    )


def _is_latest(entry: dict[str, Any]) -> bool:
    """Return True if the entry's _meta marks it as isLatest."""
    meta_block = entry.get("_meta", {})
    official = meta_block.get("io.modelcontextprotocol.registry/official", {})
    return bool(official.get("isLatest", False))


async def collect() -> list[ServerEntry]:
    """Paginate the MCP registry and return normalized ServerEntry list.

    Only entries with isLatest == True are included.
    """
    base_url = config.REGISTRY_BASE_URL
    limit = config.REGISTRY_LIMIT
    url = f"{base_url}/v0/servers"

    entries: list[ServerEntry] = []
    cursor: str | None = None
    page = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            page += 1
            params: dict[str, str | int] = {"limit": limit}
            if cursor:
                params["cursor"] = cursor

            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            servers_raw: list[dict[str, Any]] = data.get("servers", [])
            batch = [_normalize(e) for e in servers_raw if _is_latest(e)]
            entries.extend(batch)

            print(
                f"Collected page {page}... "
                f"{len(servers_raw)} raw, {len(batch)} latest, "
                f"{len(entries)} total"
            )

            metadata = data.get("metadata", {})
            cursor = metadata.get("nextCursor")
            if not cursor or not servers_raw:
                break

    print(f"Registry collection complete: {len(entries)} servers")
    return entries
