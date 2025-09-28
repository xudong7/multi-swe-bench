from huggingface_hub import snapshot_download; 

snapshot_download(repo_id='ByteDance-Seed/Multi-SWE-bench', repo_type='dataset', local_dir='./data/patches')
