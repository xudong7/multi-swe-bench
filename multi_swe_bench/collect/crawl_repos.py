import requests
import os
from datetime import datetime
import argparse
import csv
import time
from tqdm import tqdm


class GitHubScraper:
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 10
        self.request_delay = 2

    def fetch_repositories(self, language, min_stars=0, max_results=1000000, output_format='console', token=None,
                           output_dir='.'):
        """
        Fetch GitHub repositories sorted by stars

        Args:
            language (str): Programming language to search
            min_stars (int): Minimum star count
            max_results (int): Maximum results to return
            output_format (str): 'console' or 'csv'
            token (str): GitHub personal access token
            output_dir (str): Directory to save CSV files (will be created if doesn't exist)
        """
        # Create output directory if it doesn't exist
        try:
            os.makedirs(output_dir, exist_ok=True)
            print(f"Output will be saved to: {os.path.abspath(output_dir)}")
        except OSError as e:
            print(f"Error creating output directory: {e}")
            return

        url = "https://api.github.com/search/repositories"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"

        all_repositories = []
        remaining_results = max_results
        page = 1

        print(f"Fetching repositories for {language} (max {max_results} repos)")

        with tqdm(total=max_results, desc="Fetching repos", unit="repo") as pbar:
            while remaining_results > 0:
                try:
                    response = self._make_request_with_retry(
                        url=url,
                        headers=headers,
                        params={
                            "q": f"language:{language} stars:>={min_stars}",
                            "sort": "stars",
                            "order": "desc",
                            "per_page": min(100, remaining_results),
                            "page": page
                        }
                    )

                    data = response.json()
                    repositories = data.get("items", [])

                    if not repositories:
                        break

                    all_repositories.extend(repositories)
                    fetched_count = len(repositories)
                    pbar.update(fetched_count)
                    remaining_results -= fetched_count
                    page += 1

                    time.sleep(self.request_delay)

                except (requests.exceptions.RequestException, ValueError) as e:
                    print(f"\nError occurred: {str(e)}")
                    if len(all_repositories) >= max_results:
                        break
                    continue

        if not all_repositories:
            print(f"No repositories found for {language}")
            return

        all_repositories = all_repositories[:max_results]

        if output_format == 'console':
            self._print_results(all_repositories, language)
        elif output_format == 'csv':
            self._save_to_csv(all_repositories, language, output_dir)
        else:
            self._print_results(all_repositories, language)

    def _make_request_with_retry(self, url, headers, params):
        """Make HTTP request with retry logic"""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()

                if int(response.headers.get('X-RateLimit-Remaining', 1)) <= 1:
                    reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                    sleep_time = max(reset_time - time.time(), 0) + 5
                    print(f"\nApproaching rate limit, waiting {sleep_time:.1f} seconds...")
                    time.sleep(sleep_time)
                    continue

                return response

            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    print(f"\nRetry {attempt + 1}/{self.max_retries} in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)

        raise last_error if last_error else Exception("Request failed after retries")

    def _print_results(self, repositories, language):
        """Print results to console"""
        print(f"\n{'=' * 50}")
        print(f"Top {len(repositories)} {language} repositories (sorted by stars):")
        print(f"{'=' * 50}\n")

        for i, repo in enumerate(repositories, 1):
            print(f"{i}. {repo['full_name']}")
            print(f"   ⭐ Stars: {repo['stargazers_count']:,}")
            print(f"   🍴 Forks: {repo['forks_count']:,}")
            print(f"   📝 Description: {repo['description'] or 'No description'}")
            print(f"   🔗 URL: {repo['html_url']}")
            print(f"   🕒 Last updated: {repo['updated_at']}")
            print("-" * 60)

    def _save_to_csv(self, repositories, language, output_dir):
        """Save results to CSV in specified directory"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"github_{language}_repos_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)

        try:
            with open(filepath, mode='w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                writer.writerow(['Rank', 'Name', 'Stars', 'Forks', 'Description', 'URL', 'Last Updated'])

                for i, repo in enumerate(repositories, 1):
                    description = repo['description'] or 'No description'
                    if description:
                        description = description.encode('utf-8', 'ignore').decode('utf-8')

                    writer.writerow([
                        i,
                        repo['full_name'],
                        repo['stargazers_count'],
                        repo['forks_count'],
                        description,
                        repo['html_url'],
                        repo['updated_at']
                    ])

            print(f"\nData successfully saved to: {os.path.abspath(filepath)}")
            print(f"Total repositories saved: {len(repositories)}")

        except IOError as e:
            print(f"\nFailed to save CSV file: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description='Fetch GitHub repositories sorted by stars')
    parser.add_argument('--language', required=True,
                        type=str, help='Programming language to search')
    parser.add_argument('--min-stars', type=int, default=0, help='Minimum star count (default: 0)')
    parser.add_argument('--max-results', type=int, default=100,
                        help='Maximum results to return (default: 100)')
    parser.add_argument('--output', type=str, choices=['console', 'csv'], default='csv',
                        help='Output format: console (default) or csv')
    parser.add_argument('--token', type=str, default=None,
                        help='GitHub personal access token for higher rate limits')
    parser.add_argument('--output-dir', type=str, default='.',
                        help='Directory to save CSV files (will be created if doesn\'t exist)')

    args = parser.parse_args()

    scraper = GitHubScraper()
    scraper.fetch_repositories(
        language=args.language,
        min_stars=args.min_stars,
        max_results=args.max_results,
        output_format=args.output,
        token=args.token,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()