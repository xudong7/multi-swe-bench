# Copyright (c) 2024 Bytedance Ltd. and/or its affiliates

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at

#      http://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import argparse
import json
import random
from datetime import datetime
from pathlib import Path

from github import Auth, Github
from tqdm import tqdm

from multi_swe_bench.collect.util import get_tokens


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="A command-line tool for processing repositories."
    )
    parser.add_argument(
        "--out_dir", type=Path, required=True, help="Output directory path."
    )
    parser.add_argument(
        "--tokens",
        type=str,
        nargs="*",
        default=None,
        help="API token(s) or path to token file.",
    )
    parser.add_argument("--org", type=str, required=True, help="Organization name.")
    parser.add_argument("--repo", type=str, required=True, help="Repository name.")

    parser.add_argument(
        "--platform",
        type=str,
        choices=["github", "gitee"],
        default="github",
        help="Platform: github or gitee. Default is github.",
    )
    return parser


def get_github(token) -> Github:
    auth = Auth.Token(token)
    return Github(auth=auth, per_page=100)


def main(tokens: list[str], out_dir: Path, org: str, repo: str, platform: str):
    print("starting get all pull requests")
    print(f"Output directory: {out_dir}")
    print(f"Tokens: {tokens}")
    print(f"Org: {org}")
    print(f"Repo: {repo}")

    if platform == "gitee":
        import requests

        token = tokens[0]  # Gitee access_token
        api_url = f"https://gitee.com/api/v5/repos/{org}/{repo}/pulls"
        page = 1
        import sys

        with open(out_dir / f"{org}__{repo}_prs.jsonl", "w", encoding="utf-8") as file:
            while True:
                resp = requests.get(
                    api_url,
                    params={
                        "access_token": token,
                        "state": "all",
                        "page": page,
                        "per_page": 100,
                    },
                )
                try:
                    pulls = resp.json()
                except Exception as e:
                    print(f"Error decoding Gitee response: {e}")
                    print(f"Raw response: {resp.text}")
                    sys.exit(1)
                if not isinstance(pulls, list):
                    print(f"Unexpected Gitee API response type: {type(pulls)}")
                    print(f"Response: {pulls}")
                    sys.exit(1)
                if not pulls:
                    break
                for pull in pulls:
                    file.write(
                        json.dumps(
                            {
                                "org": org,
                                "repo": repo,
                                "number": pull.get("id"),
                                "state": pull.get("state"),
                                "title": pull.get("title"),
                                "body": pull.get("body"),
                                "url": pull.get("url"),
                                "id": pull.get("id"),
                                "html_url": pull.get("html_url"),
                                "diff_url": pull.get("diff_url"),
                                "patch_url": pull.get("patch_url"),
                                "created_at": pull.get("created_at"),
                                "updated_at": pull.get("updated_at"),
                                "closed_at": pull.get("closed_at"),
                                "merged_at": pull.get("merged_at"),
                                "labels": (
                                    [label["name"] for label in pull.get("labels", [])]
                                    if pull.get("labels")
                                    else []
                                ),
                                "commits_url": pull.get("commits_url"),
                                "comments_url": pull.get("comments_url"),
                                "base": pull.get("base", {}),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                page += 1
    else:
        g = get_github(random.choice(tokens))
        r = g.get_repo(f"{org}/{repo}")

        def datetime_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        with open(out_dir / f"{org}__{repo}_prs.jsonl", "w", encoding="utf-8") as file:
            for pull in tqdm(r.get_pulls("all"), desc="Pull Requests"):
                file.write(
                    json.dumps(
                        {
                            "org": org,
                            "repo": repo,
                            "number": pull.number,
                            "state": pull.state,
                            "title": pull.title,
                            "body": pull.body,
                            "url": pull.url,
                            "id": pull.id,
                            "node_id": pull.node_id,
                            "html_url": pull.html_url,
                            "diff_url": pull.diff_url,
                            "patch_url": pull.patch_url,
                            "issue_url": pull.issue_url,
                            "created_at": datetime_serializer(pull.created_at),
                            "updated_at": datetime_serializer(pull.updated_at),
                            "closed_at": datetime_serializer(pull.closed_at),
                            "merged_at": datetime_serializer(pull.merged_at),
                            "merge_commit_sha": pull.merge_commit_sha,
                            "labels": [label.name for label in pull.labels],
                            "draft": pull.draft,
                            "commits_url": pull.commits_url,
                            "review_comments_url": pull.review_comments_url,
                            "review_comment_url": pull.review_comment_url,
                            "comments_url": pull.comments_url,
                            "base": pull.base.raw_data,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()

    tokens = get_tokens(args.tokens)

    main(tokens, Path.cwd() / args.out_dir, args.org, args.repo, args.platform)
