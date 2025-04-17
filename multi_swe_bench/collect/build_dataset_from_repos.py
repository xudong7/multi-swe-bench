import os
import csv
import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import math
import shutil


def load_github_tokens(token_source=None, token_arg=None):
    """
    Load GitHub tokens from multiple possible sources with priority:
    1. Direct CLI argument (--tokens)
    2. Specific env variable (--token_source)
    3. Default GITHUB_TOKENS env variable
    """
    load_dotenv()

    # Priority 1: Command line tokens
    if token_arg:
        return [t.strip() for t in token_arg.split(',') if t.strip()]

    # Priority 2: Specified environment variable
    if token_source:
        tokens_str = os.getenv(token_source)
        if tokens_str:
            return [t.strip() for t in tokens_str.split(',') if t.strip()]

    # Priority 3: Default environment variable
    tokens_str = os.getenv('GITHUB_TOKENS', '')
    if tokens_str:
        return [t.strip() for t in tokens_str.split(',') if t.strip()]

    raise ValueError("No GitHub tokens found. Provide via --tokens, --token_source, or GITHUB_TOKENS env var")


def process_repository(out_base_dir, org, repo, token):
    """Process a single repository using the get_pipeline command"""
    dir_name = f"{org}__{repo}".replace('/', '__')
    out_dir = os.path.join(out_base_dir, dir_name)

    os.makedirs(out_dir, exist_ok=True)

    cmd = [
        "python",
        "-m",
        "multi_swe_bench.collect.get_pipeline",
        "--out_dir", out_dir,
        "--org", org,
        "--repo", repo,
        "--tokens", token
    ]
    print(f"🔄 Starting: {org}/{repo}")
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        print(f"✅ Success: {org}/{repo}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {org}/{repo}\nError: {e.stderr.strip()}")
        if os.path.exists(out_dir) and not os.listdir(out_dir):
            shutil.rmtree(out_dir)
        return False


def process_repository_wrapper(args):
    """Wrapper for ThreadPoolExecutor"""
    return process_repository(*args)


def read_repositories_from_csv(csv_file):
    """Read repositories from CSV with validation"""
    repositories = []
    with open(csv_file, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if 'Name' not in row:
                raise ValueError("CSV must contain 'Name' column")
            full_name = row['Name']
            if '/' not in full_name:
                print(f"Skipping invalid repository name: {full_name}")
                continue
            org, repo = full_name.split('/', 1)
            repositories.append((org, repo))
    return repositories


def distribute_repositories(repositories, tokens, strategy='round'):
    """
    Distribute repositories among tokens using specified strategy

    Args:
        repositories: List of (org, repo) tuples
        tokens: List of GitHub tokens
        strategy: 'chunk' for equal chunks or 'round' for round-robin (default)

    Returns:
        List of dicts {'token': token, 'repos': [...]}
    """
    if strategy == 'chunk':
        return _distribute_chunk(repositories, tokens)
    return _distribute_round(repositories, tokens)


def _distribute_chunk(repositories, tokens):
    """Equal chunks distribution"""
    num_repos = len(repositories)
    num_tokens = len(tokens)
    base_chunk_size = num_repos // num_tokens
    remainder = num_repos % num_tokens

    distributed = []
    position = 0
    for i in range(num_tokens):
        chunk_size = base_chunk_size + (1 if i < remainder else 0)
        distributed.append({
            'token': tokens[i],
            'repos': repositories[position:position + chunk_size]
        })
        position += chunk_size
    return distributed


def _distribute_round(repositories, tokens):
    """Round-robin distribution"""
    num_tokens = len(tokens)
    token_repos = {token: [] for token in tokens}

    for i, repo in enumerate(repositories):
        token_index = i % num_tokens
        token_repos[tokens[token_index]].append(repo)

    return [{'token': token, 'repos': repos} for token, repos in token_repos.items()]

def process_token_group(out_dir, repos, token):
    """Process repos of a token group"""
    results = []
    for org, repo in repos:
        results.append(process_repository(out_dir, org, repo, token))
    return results

def main():
    parser = argparse.ArgumentParser(
        description='Concurrently process GitHub repositories from CSV',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--csv_file', required=True,
                        help='Path to CSV file with "Name" column')
    parser.add_argument('--out_dir', required=True,
                        help='Base output directory for repository data')
    parser.add_argument('--max_workers', type=int, default=None,
                        help='Max concurrent processes (default: token count)')
    parser.add_argument('--distribute',
                      choices=['round', 'chunk'],
                      default='round',
                      help='Distribution strategy: round-robin (default) or equal chunks')
    # Token input options (multiple sources supported)
    token_group = parser.add_mutually_exclusive_group()
    token_group.add_argument('--tokens',
                           help='Comma-separated tokens directly')
    token_group.add_argument('--token_source',
                           help='Env variable name containing tokens')
    args = parser.parse_args()

    try:
        tokens = load_github_tokens(
            token_source=args.token_source,
            token_arg=args.tokens
        )
        print(f"Loaded {len(tokens)} GitHub tokens")

        repositories = read_repositories_from_csv(args.csv_file)
        if not repositories:
            print("No valid repositories found in CSV")
            return

        print(f"Processing {len(repositories)} repositories...")
        os.makedirs(args.out_dir, exist_ok=True)

        # Distribute repos among tokens
        distribution = distribute_repositories(
            repositories,
            tokens,
            strategy=args.distribute
        )
        print(distribution)
        for i, group in enumerate(distribution, 1):
            print(f"Token {i} will process {len(group['repos'])} repositories")

        # Process with ThreadPool
        max_workers = args.max_workers or len(tokens)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            tasks = []
            for group in distribution:
                tasks.append(executor.submit(
                    process_token_group,
                    args.out_dir,
                    group['repos'],
                    group['token']
                ))

            # Wait for completion and show progress
            completed = 0
            for future in tasks:
                future.result()
                completed += 1
                print(f"Progress: {completed}/{len(tasks)} ({completed / len(tasks):.1%})")

        print("🎉 All repositories processed!")
    except Exception as e:
        print(f"💥 Error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()