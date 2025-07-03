from typing import Any, Dict

from pydantic import BaseModel

from atopile.mcp.util import mcp_decorate


class Author(BaseModel):
    name: str
    email: str


class PackageInfo(BaseModel):
    key: str
    identifier: str
    version: str
    repository: str
    authors: list[Author]
    license: str
    summary: str
    url: str
    stats: Dict[str, Any]


class PackageResponse(BaseModel):
    info: PackageInfo


class Package(BaseModel):
    identifier: str
    version: str
    summary: str
    url: str
    repository: str


class QueryPackagesResponse(BaseModel):
    packages: list[Package]


@mcp_decorate()
def get_package(identifier: str) -> PackageResponse:
    """
    Get a package

    Get information for a package, including readme if available.
    Details are sourced from the package's latest release.

    ### Responses:

    **200**: Successful Response (Success Response)
    Content-Type: application/json

    **Example Response:**
    ```json
    {
      "info": {
        "key": "Key",
        "identifier": "Package identifier",
        "version": "Version",
        "repository": "https://example.com",
        "authors": [
          {
            "name": "Name",
            "email": "Email"
          }
        ],
        "license": "License",
        "summary": "Summary",
        "url": "https://example.com",
        "stats": {}
      }
    }
    ```
    """
    # Create sample data matching the expected JSON structure
    package_info = PackageInfo(
        key=f"pkg_{identifier.replace('/', '_')}",
        identifier=identifier,
        version="1.0.0",
        repository=f"https://github.com/{identifier}",
        authors=[Author(name="Package Author", email="author@example.com")],
        license="MIT",
        summary=f"Package summary for {identifier}",
        url=f"https://example.com/packages/{identifier}",
        stats={},
    )

    return PackageResponse(info=package_info)


@mcp_decorate()
def query_packages(query: str) -> QueryPackagesResponse:
    """
    Search for packages by identifier or summary, with closest matches appearing first.

    ### Responses:

    **200**: Successful Response (Success Response)
    Content-Type: application/json

    **Example Response:**
    ```json
    {
      "packages": [
        {
          "identifier": "Package identifier",
          "version": "Version",
          "summary": "Summary",
          "url": "https://example.com",
          "repository": "https://example.com"
        }
      ]
    }
    ```
    """
    # Create sample search results matching the expected JSON structure
    packages = [
        Package(
            identifier=f"example/{query}",
            version="1.0.0",
            summary=f"Package containing {query} functionality",
            url=f"https://example.com/packages/example/{query}",
            repository=f"https://github.com/example/{query}",
        ),
        Package(
            identifier=f"community/{query}-utils",
            version="0.9.2",
            summary=f"Utility package for {query} operations",
            url=f"https://example.com/packages/community/{query}-utils",
            repository=f"https://github.com/community/{query}-utils",
        ),
    ]

    return QueryPackagesResponse(packages=packages)
