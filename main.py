from fastapi import FastAPI, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, HttpUrl, SecretStr
from enum import StrEnum, auto
from pydantic_settings import BaseSettings
from uuid import UUID, uuid4
from typing import Annotated
import jwt
from fastapi_pagination import Page, add_pagination, paginate


class Settings(BaseSettings):
    jwt_search_secret: SecretStr = SecretStr("search secret")
    jwt_crawl_secret: SecretStr = SecretStr("crawl secret")


settings = Settings()


class SearchParams(BaseModel):
    q: str = Field(..., min_length=1, max_length=500, description="Search query.")


class Domain(StrEnum):
    COM = auto()
    NET = auto()
    ORG = auto()
    ...  # More domains can be added here


class CrawlStatus(StrEnum):
    COMPLETED = auto()
    IN_PROGRESS = auto()
    FAILED = auto()
    PENDING = auto()


class Region(BaseModel):
    country: str | None = Field(
        None, min_length=2, max_length=2, description="Country code."
    )
    city: str | None = Field(
        None, min_length=2, max_length=20, description="City name."
    )
    state: str | None = Field(
        None, min_length=2, max_length=20, description="State name."
    )


class CrawlParams(BaseModel):
    domains: list[Domain] | None = Field(None, description="List of domains to crawl.")
    region: Region | None = Field(None, description="Region to crawl.")


class WebPAge(BaseModel):
    snippet: str
    thumbnail: HttpUrl
    title: str
    url: HttpUrl


class User(BaseModel):
    user_id: UUID


class Message(BaseModel):
    message: str


app = FastAPI()
add_pagination(app)
security = HTTPBearer()


def get_search_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> User:
    decoded = jwt.decode(
        credentials.credentials,
        settings.jwt_search_secret.get_secret_value(),
        algorithms=["HS256"],
    )
    return User.model_validate(decoded)


def get_crawl_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> User:
    decoded = jwt.decode(
        credentials.credentials,
        settings.jwt_crawl_secret.get_secret_value(),
        algorithms=["HS256"],
    )
    return User.model_validate(decoded)


web_pages = [
    WebPAge(
        snippet="snippet 1",
        thumbnail=HttpUrl("https://picsum.photos/200/300"),
        title="title 1",
        url=HttpUrl("https://example.com/1"),
    ),
    WebPAge(
        snippet="snippet 2",
        thumbnail=HttpUrl("https://picsum.photos/200/300"),
        title="title 2",
        url=HttpUrl("https://example.com/2"),
    ),
    WebPAge(
        snippet="snippet 3",
        thumbnail=HttpUrl("https://picsum.photos/200/300"),
        title="title 3",
        url=HttpUrl("https://example.com/3"),
    ),
]


@app.get("/search", responses={status.HTTP_401_UNAUTHORIZED: {"model": Message}})
def read_root(
    user: Annotated[User, Depends(get_search_user)],
    q: Annotated[SearchParams, Depends()],
) -> Page[WebPAge]:
    """Search for web pages. Return a paginated list of results."""
    # Fetch pages with "q" query and "user"
    return paginate(web_pages)  # Pagination sample


@app.post("/crawl", responses={status.HTTP_401_UNAUTHORIZED: {"model": Message}})
def crawl(
    user: Annotated[User, Depends(get_crawl_user)],
    params: Annotated[CrawlParams, Depends()],
) -> UUID:
    """Crawl web pages. Return a unique ID for the crawl job."""
    return uuid4()


@app.get(
    "/crawl/{crawl_id}",
    responses={status.HTTP_401_UNAUTHORIZED: {"model": Message}},
)
def crawl_status(
    user: Annotated[User, Depends(get_crawl_user)],
    crawl_id: UUID,
) -> CrawlStatus:
    """Get the status of a crawl job. Return CrawlStatus."""
    return CrawlStatus.COMPLETED  # Sample status
