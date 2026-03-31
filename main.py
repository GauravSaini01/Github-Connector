from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import RedirectResponse
import os
import httpx
from dotenv import load_dotenv
from pydantic import BaseModel


app = FastAPI()

load_dotenv()

CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API = "https://api.github.com"

@app.get("/")
async def root():
    return {"message" : "success"}

@app.get("/auth/github/login")
async def github_login():
    url = f"{GITHUB_AUTH_URL}?client_id={CLIENT_ID}&scope=repo,user"
    return RedirectResponse(url)

@app.get("/auth/github/callback")
async def github_callback(code : str):
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
            },
        )

        token_data = token_res.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="Auth failed")
        
        user_res = await client.get(
            f"{GITHUB_API}/user",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        user_data = user_res.json()

    return {
        "access_token": access_token,
        "user": {
            "login": user_data["login"],
            "id": user_data["id"],
            "avatar": user_data["avatar_url"]
        }
    }


class Issue(BaseModel):
    title : str
    body : str


@app.post("/repos/{owner}/{repo}/issues")
async def create_issue(owner: str, repo: str, issue: Issue,authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")

    access_token = authorization.split(" ")[1]

    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "title": issue.title,
        "body": issue.body
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.status_code != 201:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.json()
        )

    data = response.json()

    return {
        "id": data["id"],
        "title": data["title"],
        "url": data["html_url"],
        "state": data["state"]
    }



class PRCreate(BaseModel):
    title: str
    head: str
    base: str
    body: str | None = None


@app.post("/repos/{owner}/{repo}/pulls")
async def create_pull_request(
    owner: str,
    repo: str,
    pr: PRCreate,
    authorization: str = Header(...)
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")

    token = authorization.split(" ")[1]

    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "title": pr.title,
        "head": pr.head,   # e.g. "feature-branch"
        "base": pr.base,   # e.g. "main"
        "body": pr.body
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.status_code != 201:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.json()
        )

    data = response.json()

    return {
        "id": data["id"],
        "title": data["title"],
        "url": data["html_url"],
        "state": data["state"]
    }