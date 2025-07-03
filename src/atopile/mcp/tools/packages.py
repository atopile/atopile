from pydantic import BaseModel

from atopile.mcp.util import MCPTools
from faebryk.libs.backend.packages.api import PackagesAPIClient, _Endpoints

packages_tools = MCPTools()


class PackageInfoVeryBrief(BaseModel):
    identifier: str
    version: str
    summary: str


@packages_tools.register()
def inspect_package(
    identifier: str, version: str | None = None
) -> _Endpoints.PackageRelease.Response:
    """
    Get information for a published atopile community package,
    including readme if available.
    Details are sourced from the package's latest release.
    """
    client = PackagesAPIClient()
    package = client.get_package(identifier, version=version)

    return package


@packages_tools.register()
def find_packages(query: str) -> list[PackageInfoVeryBrief]:
    """
    Search for atopile community packages by identifier or summary,
    with closest matches appearing first.
    """
    client = PackagesAPIClient()
    packages = client.query_packages(query)

    return [
        PackageInfoVeryBrief(
            identifier=p.identifier, version=p.version, summary=p.summary
        )
        for p in packages.packages
    ]
